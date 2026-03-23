"""Asterisk ARI handler for AI voice agent calls.

Flow:
1. Call arrives at AI agent extension → routed to Stasis(millicall-ai)
2. ARI answers the call
3. Play greeting via TTS
4. Loop: Record caller → STT → LLM → TTS → Play response
5. Hangup detection
"""

import asyncio
import json
import logging
import os

import httpx
import websockets

from millicall.phase2 import llm_chat, stt, tts_coefont, tts_google

logger = logging.getLogger(__name__)

ARI_URL = "http://localhost:8088"
ARI_USER = "millicall"
ARI_PASSWORD = "millicall"
STASIS_APP_AI = "millicall-ai"
STASIS_APP_WORKFLOW = "millicall-workflow"
STASIS_APP_MCP = "millicall-mcp"

# Tracks MCP-originated channels (channel_id -> True when connected)
mcp_channels: dict[str, bool] = {}

# Per-call conversation contexts
_conversations: dict[str, llm_chat.ConversationContext] = {}


async def _synthesize_tts(text: str, agent) -> bytes:
    """Route TTS to the configured provider."""
    if agent.tts_provider == "google":
        api_key = await _get_api_key("google")
        return await tts_google.synthesize(text, api_key, voice_name=agent.google_tts_voice)
    else:
        return await tts_coefont.synthesize_for_asterisk(text, agent.coefont_voice_id)


async def _get_api_key(provider: str) -> str:
    """Get API key for the LLM/STT provider from DB (with env fallback)."""
    from millicall.application.settings_service import SettingsService
    from millicall.infrastructure.database import async_session

    async with async_session() as session:
        svc = SettingsService(session)
        key = await svc.get_api_key(provider)
    if not key:
        raise RuntimeError(f"API key not configured for: {provider}")
    return key


async def _ari_request(method: str, path: str, **kwargs) -> dict | bytes | None:
    """Make an ARI REST API request."""
    url = f"{ARI_URL}/ari{path}"
    params = kwargs.pop("params", {})
    params["api_key"] = f"{ARI_USER}:{ARI_PASSWORD}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, params=params, **kwargs)
        if response.status_code == 204:
            return None
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
        return response.content


def _sanitize_id(channel_id: str) -> str:
    """Remove dots from channel IDs for safe filenames."""
    return channel_id.replace(".", "_")


async def _save_wav_to_asterisk(audio_wav: bytes, filename: str) -> str:
    """Save WAV audio to a file Asterisk can play and return the ARI media URI."""
    # Asterisk has language prefix enabled, so sounds are searched under en/
    # Place files under the language-prefixed path
    sounds_path = f"/usr/share/asterisk/sounds/en/millicall/{filename}"
    os.makedirs(os.path.dirname(sounds_path), exist_ok=True)
    with open(sounds_path, "wb") as f:
        f.write(audio_wav)

    # Return sound name without extension
    return f"millicall/{filename.rsplit('.', 1)[0]}"


async def _save_call_message(log_id: int, role: str, content: str, turn: int) -> None:
    """Persist a single call message to the database."""
    from datetime import datetime

    from millicall.domain.models import CallMessage
    from millicall.infrastructure.database import async_session
    from millicall.infrastructure.repositories.call_log_repo import CallLogRepository

    async with async_session() as session:
        repo = CallLogRepository(session)
        await repo.add_message(
            CallMessage(
                call_log_id=log_id,
                role=role,
                content=content,
                turn=turn,
                created_at=datetime.now(),
            )
        )


async def _handle_call(channel_id: str, extension: str) -> None:
    """Handle an incoming AI agent call."""
    from datetime import datetime

    from millicall.domain.models import CallLog
    from millicall.infrastructure.database import async_session
    from millicall.infrastructure.repositories.ai_agent_repo import AIAgentRepository
    from millicall.infrastructure.repositories.call_log_repo import CallLogRepository

    # Look up the AI agent for this extension
    async with async_session() as session:
        repo = AIAgentRepository(session)
        agent = await repo.get_by_extension(extension)

    if not agent or not agent.enabled:
        logger.warning("No active AI agent for extension %s", extension)
        await _ari_request("DELETE", f"/channels/{channel_id}", params={"reason_code": "404"})
        return

    safe_id = _sanitize_id(channel_id)
    logger.info("AI call started: ext=%s agent=%s channel=%s", extension, agent.name, channel_id)

    # Ensure recording directory exists
    os.makedirs("/var/spool/asterisk/recording", exist_ok=True)

    # Initialize conversation context
    context = llm_chat.ConversationContext(max_history=agent.max_history)
    _conversations[channel_id] = context

    # Create call log
    call_log_id = None
    turn_counter = 0
    try:
        async with async_session() as session:
            log_repo = CallLogRepository(session)
            call_log_id = await log_repo.create_log(
                CallLog(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    extension_number=extension,
                    caller_channel=channel_id,
                    started_at=datetime.now(),
                )
            )
    except Exception as e:
        logger.error("Failed to create call log: %s", e)

    try:
        # Answer the call
        await _ari_request("POST", f"/channels/{channel_id}/answer")
        await asyncio.sleep(0.5)

        # Play greeting
        greeting_audio = await _synthesize_tts(agent.greeting_text, agent)
        sound_name = await _save_wav_to_asterisk(greeting_audio, f"greeting_{safe_id}.wav")
        await _ari_request(
            "POST", f"/channels/{channel_id}/play", params={"media": f"sound:{sound_name}"}
        )
        # Wait for greeting to finish
        await asyncio.sleep(len(greeting_audio) / (8000 * 2) + 0.5)

        # Conversation loop
        for turn in range(50):  # Max 50 turns
            # Record caller audio (max 15 seconds, stop on silence)
            recording_name = f"ai_{safe_id}_{turn}"
            try:
                await _ari_request(
                    "POST",
                    f"/channels/{channel_id}/record",
                    params={
                        "name": recording_name,
                        "format": "wav",
                        "maxDurationSeconds": 15,
                        "maxSilenceSeconds": 2,
                        "beep": "false",
                        "terminateOn": "none",
                    },
                )
            except Exception as e:
                logger.info("Recording failed: %s", e)
                break

            # Wait for recording to complete (poll until file exists)
            audio_data = None
            for poll in range(18):  # Wait up to 18 seconds
                await asyncio.sleep(1)
                try:
                    result = await _ari_request(
                        "GET",
                        f"/recordings/stored/{recording_name}/file",
                    )
                    if result and isinstance(result, bytes) and len(result) > 100:
                        audio_data = result
                        break
                except Exception:
                    continue

            if not audio_data:
                logger.info("No audio recorded, continuing...")
                continue

            # STT
            try:
                stt_key = await _get_api_key("openai")
                user_text = await stt.transcribe(audio_data, stt_key)
            except Exception as e:
                logger.error("STT failed: %s", e)
                continue

            if not user_text.strip():
                continue

            logger.info("User said: '%s'", user_text)

            # LLM - append hangup instruction to system prompt
            hangup_prompt = (
                agent.system_prompt
                + "\n\n[重要ルール] 会話が自然に終わる場面（お礼・別れの挨拶・「もういい」「切るね」"
                "「ありがとう、じゃあね」等）では、最後の応答の末尾に [END_CALL] と付けてください。"
                "このタグはユーザーには見えません。通常の会話中は絶対に付けないでください。"
            )
            try:
                llm_key = await _get_api_key(agent.llm_provider)
                response_text = await llm_chat.generate_response(
                    user_text=user_text,
                    context=context,
                    system_prompt=hangup_prompt,
                    provider=agent.llm_provider,
                    api_key=llm_key,
                    model=agent.llm_model,
                )
            except Exception as e:
                logger.error("LLM failed: %s", e)
                response_text = "申し訳ございません、少々お待ちください。"

            # Detect end-of-call marker
            should_hangup = "[END_CALL]" in response_text
            response_text = response_text.replace("[END_CALL]", "").strip()

            # Update conversation context
            context.add_message("user", user_text)
            context.add_message("assistant", response_text)
            turn_counter += 1

            # Persist to database
            if call_log_id:
                try:
                    await _save_call_message(call_log_id, "user", user_text, turn_counter)
                    await _save_call_message(call_log_id, "assistant", response_text, turn_counter)
                except Exception as e:
                    logger.error("Failed to save call message: %s", e)

            # TTS
            try:
                response_audio = await _synthesize_tts(response_text, agent)
                sound_name = await _save_wav_to_asterisk(
                    response_audio, f"response_{safe_id}_{turn}.wav"
                )
                await _ari_request(
                    "POST",
                    f"/channels/{channel_id}/play",
                    params={"media": f"sound:{sound_name}"},
                )
                # Wait for playback to finish
                duration = len(response_audio) / (8000 * 2)
                await asyncio.sleep(duration + 0.3)
            except Exception as e:
                logger.error("TTS/playback failed: %s", e)
                break

            # Hang up if LLM decided the call should end
            if should_hangup:
                logger.info("AI ending call (natural conclusion)")
                await asyncio.sleep(0.5)
                try:
                    await _ari_request(
                        "DELETE", f"/channels/{channel_id}", params={"reason_code": "16"}
                    )
                except Exception:
                    pass
                break

            # Clean up recording
            try:
                await _ari_request("DELETE", f"/recordings/stored/{recording_name}")
            except Exception:
                pass

    except Exception as e:
        logger.error("AI call error: %s", e)
    finally:
        _conversations.pop(channel_id, None)
        # Finalize call log
        if call_log_id:
            try:
                async with async_session() as session:
                    log_repo = CallLogRepository(session)
                    await log_repo.finish_log(call_log_id, turn_counter)
            except Exception as e:
                logger.error("Failed to finalize call log: %s", e)
        # Clean up temp audio files
        import glob

        for f in glob.glob(f"/usr/share/asterisk/sounds/en/millicall/*{safe_id}*"):
            try:
                os.remove(f)
            except OSError:
                pass
        logger.info("AI call ended: channel=%s", channel_id)


async def _handle_workflow_call(channel_id: str, extension: str) -> None:
    """Handle an incoming workflow call."""
    from millicall.infrastructure.database import async_session
    from millicall.infrastructure.repositories.workflow_repo import WorkflowRepository
    from millicall.phase2.workflow_executor import WorkflowExecutor, channel_gone

    # Look up the workflow for this extension number
    async with async_session() as session:
        repo = WorkflowRepository(session)
        workflow = await repo.get_by_number(extension)

    if not workflow:
        logger.warning("No enabled workflow for extension %s", extension)
        await _ari_request("DELETE", f"/channels/{channel_id}", params={"reason_code": "404"})
        return

    logger.info(
        "Workflow call started: ext=%s workflow=%s (type=%s) channel=%s",
        extension,
        workflow.name,
        workflow.workflow_type,
        channel_id,
    )

    try:
        # Answer the call
        await _ari_request("POST", f"/channels/{channel_id}/answer")
        await asyncio.sleep(0.5)

        # Execute the workflow
        executor = WorkflowExecutor(channel_id, workflow)
        await executor.execute()
    except Exception as exc:
        logger.error("Workflow call error on channel %s: %s", channel_id, exc, exc_info=True)
        try:
            await _ari_request("DELETE", f"/channels/{channel_id}", params={"reason_code": "16"})
        except Exception:
            pass
    finally:
        logger.info("Workflow call ended: channel=%s", channel_id)


async def run_ari_listener() -> None:
    """Connect to ARI WebSocket and handle Stasis events for both AI and workflow apps."""
    from millicall.phase2.workflow_executor import channel_gone, dtmf_queues

    ws_url = (
        f"ws://localhost:8088/ari/events"
        f"?api_key={ARI_USER}:{ARI_PASSWORD}"
        f"&app={STASIS_APP_AI},{STASIS_APP_WORKFLOW},{STASIS_APP_MCP}"
        f"&subscribeAll=true"
    )

    while True:
        try:
            logger.info("Connecting to ARI WebSocket...")
            async with websockets.connect(ws_url) as ws:
                logger.info(
                    "ARI WebSocket connected (apps: %s, %s, %s)",
                    STASIS_APP_AI,
                    STASIS_APP_WORKFLOW,
                    STASIS_APP_MCP,
                )
                async for message in ws:
                    event = json.loads(message)
                    event_type = event.get("type")

                    if event_type == "StasisStart":
                        channel = event["channel"]
                        channel_id = channel["id"]
                        app_name = event.get("application", "")
                        exten = channel.get("dialplan", {}).get("exten", "")
                        logger.info(
                            "StasisStart: channel=%s exten=%s app=%s",
                            channel_id,
                            exten,
                            app_name,
                        )

                        if app_name == STASIS_APP_MCP:
                            # MCP-originated call: just track it, MCP tools control it
                            logger.info("MCP call connected: channel=%s", channel_id)
                            mcp_channels[channel_id] = True
                        elif app_name == STASIS_APP_WORKFLOW:
                            asyncio.create_task(_handle_workflow_call(channel_id, exten))
                        else:
                            # Default to AI handler (millicall-ai)
                            asyncio.create_task(_handle_call(channel_id, exten))

                    elif event_type == "StasisEnd":
                        channel_id = event["channel"]["id"]
                        logger.info("StasisEnd: channel=%s", channel_id)
                        # Signal workflow executors that the channel is gone
                        channel_gone[channel_id] = True
                        # Clean up MCP channel tracking
                        mcp_channels.pop(channel_id, None)

                    elif event_type == "ChannelHangupRequest":
                        channel_id = event["channel"]["id"]
                        logger.info("Hangup request: channel=%s", channel_id)
                        channel_gone[channel_id] = True
                        try:
                            await _ari_request("DELETE", f"/channels/{channel_id}")
                        except Exception:
                            pass

                    elif event_type == "ChannelDtmfReceived":
                        channel_id = event["channel"]["id"]
                        digit = event.get("digit", "")
                        logger.info("DTMF received: channel=%s digit=%s", channel_id, digit)
                        queue = dtmf_queues.get(channel_id)
                        if queue is not None:
                            await queue.put(digit)

        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            logger.warning("ARI WebSocket disconnected: %s, reconnecting in 5s...", e)
            await asyncio.sleep(5)
        except Exception as e:
            logger.error("ARI listener error: %s", e)
            await asyncio.sleep(5)
