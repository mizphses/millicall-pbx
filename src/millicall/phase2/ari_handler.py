"""Asterisk ARI handler for AI voice agent calls.

Flow:
1. Call arrives at AI agent extension → routed to Stasis(millicall-ai)
2. ARI answers the call
3. Play greeting via TTS
4. Loop: Record caller → STT → LLM → TTS → Play response
5. Hangup detection
"""

import asyncio
import contextlib
import json
import logging
import os

import httpx
import websockets

from millicall.config import settings
from millicall.phase2 import llm_chat, stt, tts_coefont, tts_google

logger = logging.getLogger(__name__)

ARI_URL = "http://localhost:8088"
ARI_USER = settings.ari_user
ARI_PASSWORD = settings.ari_password
STASIS_APP_AI = "millicall-ai"
STASIS_APP_WORKFLOW = "millicall-workflow"
STASIS_APP_MCP = "millicall-mcp"

# Tracks MCP-originated channels (channel_id -> True when connected)
mcp_channels: dict[str, bool] = {}

# Per-call conversation contexts
_conversations: dict[str, llm_chat.ConversationContext] = {}

# Playback completion events: playback_id -> asyncio.Event
_playback_events: dict[str, asyncio.Event] = {}


async def _play_and_wait(
    channel_id: str,
    media: str,
    fallback_duration: float = 5.0,
) -> None:
    """Play media on channel and wait for PlaybackFinished event."""
    import uuid

    playback_id = str(uuid.uuid4())
    event = asyncio.Event()
    _playback_events[playback_id] = event

    try:
        await _ari_request(
            "POST",
            f"/channels/{channel_id}/play/{playback_id}",
            params={"media": media},
        )
        # Wait for PlaybackFinished event, with fallback timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=fallback_duration + 2.0)
        except asyncio.TimeoutError:
            logger.debug("Playback timeout, continuing (id=%s)", playback_id)
    finally:
        _playback_events.pop(playback_id, None)


async def _get_google_auth():
    """Get GoogleAuth instance from DB settings."""
    from millicall.infrastructure.database import async_session
    from millicall.infrastructure.google_auth import get_google_auth

    async with async_session() as session:
        return await get_google_auth(session)


def _generate_ringback_wav(ring_count: int) -> bytes:
    """Generate Japanese ringback tone WAV: 400+15Hz, 1s ON / 2s OFF."""
    import io
    import math
    import struct
    import wave

    sample_rate = 8000
    samples = []

    for _ in range(ring_count):
        # 1 second of 400+15Hz tone
        for i in range(sample_rate):
            t = i / sample_rate
            val = math.sin(2 * math.pi * 400 * t) + math.sin(2 * math.pi * 415 * t)
            samples.append(int(val * 8000))  # scale to 16-bit range

        # 2 seconds of silence
        samples.extend([0] * (sample_rate * 2))

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    return output.getvalue()


async def _record_with_vad(
    channel_id: str, recording_name: str, max_duration: int = 15
) -> bytes | None:
    """Record audio with VAD-based end-of-speech detection."""
    from millicall.phase2.vad import detect_end_of_speech

    try:
        await _ari_request(
            "POST",
            f"/channels/{channel_id}/record",
            params={
                "name": recording_name,
                "format": "wav",
                "maxDurationSeconds": max_duration,
                "maxSilenceSeconds": 0,
                "beep": "false",
                "terminateOn": "#",
                "ifExists": "overwrite",
            },
        )
    except Exception as e:
        logger.info("Recording failed: %s", e)
        return None

    audio_data = None
    pending_end = False
    grace_polls = 0
    GRACE_LIMIT = 5  # up to 1.5s grace to catch continuation speech
    for poll in range(max_duration * 4 + 8):
        await asyncio.sleep(0.3)

        try:
            result = await _ari_request(
                "GET", f"/recordings/stored/{recording_name}/file"
            )
        except Exception:
            continue

        if not result or not isinstance(result, bytes) or len(result) < 1000:
            continue

        vad_result = detect_end_of_speech(result)

        if vad_result["speech_ended"]:
            if not pending_end:
                pending_end = True
                grace_polls = 0
            else:
                grace_polls += 1
                if grace_polls >= GRACE_LIMIT:
                    logger.info(
                        "VAD: speech ended after %dms (silence %dms)",
                        vad_result["speech_ms"],
                        vad_result["trailing_silence_ms"],
                    )
                    audio_data = result
                    break
        elif pending_end and vad_result["has_speech"] and not vad_result["speech_ended"]:
            logger.info("VAD: continuation speech detected, resetting")
            pending_end = False
            grace_polls = 0

        if not vad_result["has_speech"] and poll >= 17:
            logger.info("VAD: no speech after %ds", poll * 0.3)
            break

    with contextlib.suppress(Exception):
        await _ari_request("POST", f"/recordings/live/{recording_name}/stop")

    if not audio_data:
        await asyncio.sleep(0.3)
        try:
            result = await _ari_request(
                "GET", f"/recordings/stored/{recording_name}/file"
            )
            if result and isinstance(result, bytes) and len(result) > 1000:
                vad_result = detect_end_of_speech(result)
                if vad_result["has_speech"]:
                    audio_data = result
        except Exception:
            pass

    return audio_data


async def _synthesize_one(text: str, agent) -> bytes:
    """Synthesize a single text segment."""
    if agent.tts_provider == "google":
        api_key = await _get_api_key("google")
        auth = await _get_google_auth()
        return await tts_google.synthesize(
            text, api_key, voice_name=agent.google_tts_voice, google_auth=auth
        )
    else:
        return await tts_coefont.synthesize_for_asterisk(text, agent.coefont_voice_id)


async def _play_tts_pipelined(text: str, agent, channel_id: str) -> None:
    """Split into 2 chunks: first sentence (low latency) + rest (background)."""
    import re

    sentences = re.split(r"(?<=[。！？\n])", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return

    safe_id = _sanitize_id(channel_id)
    first = sentences[0]
    rest = "".join(sentences[1:]).strip() if len(sentences) > 1 else ""

    # Synthesize first sentence immediately
    audio_first = await _synthesize_one(first, agent)

    # Start synthesizing rest in background
    rest_task: asyncio.Task | None = None
    if rest:
        rest_task = asyncio.create_task(_synthesize_one(rest, agent))

    # Play first chunk
    sound_name = await _save_wav_to_asterisk(audio_first, f"tts_{safe_id}_0.wav")
    duration = len(audio_first) / 16000
    await _play_and_wait(channel_id, f"sound:{sound_name}", duration)

    # Play rest
    if rest_task:
        audio_rest = await rest_task
        sound_name = await _save_wav_to_asterisk(audio_rest, f"tts_{safe_id}_1.wav")
        duration = len(audio_rest) / 16000
        await _play_and_wait(channel_id, f"sound:{sound_name}", duration)


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
    """Sanitize channel IDs for safe filenames — allow only alphanumeric, underscore, hyphen."""
    import re

    return re.sub(r"[^a-zA-Z0-9_\-]", "_", channel_id)


async def _save_wav_to_asterisk(audio_wav: bytes, filename: str) -> str:
    """Save WAV audio to a file Asterisk can play and return the ARI media URI."""
    sounds_dir = "/usr/share/asterisk/sounds/en/millicall"
    os.makedirs(sounds_dir, exist_ok=True)
    filepath = f"{sounds_dir}/{filename}"
    with open(filepath, "wb") as f:
        f.write(audio_wav)
    logger.debug("Saved WAV: %s (%d bytes)", filepath, len(audio_wav))

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
            assert agent.id is not None
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
        greeting_audio = await _synthesize_one(agent.greeting_text, agent)
        sound_name = await _save_wav_to_asterisk(greeting_audio, f"greeting_{safe_id}.wav")
        greeting_duration = len(greeting_audio) / 16000
        await _play_and_wait(channel_id, f"sound:{sound_name}", greeting_duration)

        # Conversation loop
        for turn in range(50):  # Max 50 turns
            # Record with VAD-based end-of-speech detection
            recording_name = f"ai_{safe_id}_{turn}"
            audio_data = await _record_with_vad(channel_id, recording_name)
            if not audio_data:
                logger.info("No speech detected, continuing...")
                continue

            try:
                user_text = await stt.smart_transcribe(audio_data)
            except Exception as e:
                logger.error("STT failed: %s", e)
                continue

            user_text = user_text.strip()
            if not user_text:
                continue

            with contextlib.suppress(Exception):
                await _ari_request("DELETE", f"/recordings/stored/{recording_name}")

            logger.info("User said: '%s'", user_text)

            # LLM - append hangup instruction to system prompt
            hangup_prompt = (
                agent.system_prompt
                + "\n\n[重要ルール]"
                "\n- これは電話会話です。応答は最大2文、40文字以内で簡潔に。"
                "\n- 最初の一文は必ず短く（15文字以内の相槌や返事）。例:「ああ、そうだね！」「ふむ、なるほど。」"
                "\n\n[終話ルール — 必ず守ること]"
                "\n相手が会話を終わらせようとしている場合、あなたの応答の最後に必ず [END_CALL] を付けてください。"
                "\n終話のサイン例:"
                "\n- 「ありがとう」「ありがとうね」「サンキュー」"
                "\n- 「じゃあね」「バイバイ」「またね」「また今度」"
                "\n- 「大丈夫」「もういいよ」「切るね」「おやすみ」"
                "\n- 「一旦大丈夫」「とりあえずいいや」"
                "\nこれらが含まれていたら、短い別れの挨拶 + [END_CALL] で応答してください。"
                "\n例: 「うん、またね！ [END_CALL]」「こちらこそ、ありがとう！ [END_CALL]」"
                "\n通常の会話中は絶対に [END_CALL] を付けないでください。"
            )
            try:
                llm_key = await _get_api_key(agent.llm_provider)
                auth = await _get_google_auth() if agent.llm_provider == "google" else None
                response_text = await llm_chat.generate_response(
                    user_text=user_text,
                    context=context,
                    system_prompt=hangup_prompt,
                    provider=agent.llm_provider,
                    api_key=llm_key,
                    model=agent.llm_model,
                    google_auth=auth,
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

            # TTS (pipelined: synthesize next sentence while playing current)
            try:
                await _play_tts_pipelined(response_text, agent, channel_id)
            except Exception as e:
                logger.error("TTS/playback failed: %s", e)
                break

            # Hang up if LLM decided the call should end
            if should_hangup:
                logger.info("AI ending call (natural conclusion)")
                await asyncio.sleep(0.5)
                with contextlib.suppress(Exception):
                    await _ari_request(
                        "DELETE", f"/channels/{channel_id}", params={"reason_code": "16"}
                    )
                break

            # Clean up recording
            with contextlib.suppress(Exception):
                await _ari_request("DELETE", f"/recordings/stored/{recording_name}")

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
            with contextlib.suppress(OSError):
                os.remove(f)
        logger.info("AI call ended: channel=%s", channel_id)


async def _handle_workflow_call(channel_id: str, extension: str) -> None:
    """Handle an incoming workflow call."""
    from millicall.infrastructure.database import async_session
    from millicall.infrastructure.repositories.workflow_repo import WorkflowRepository
    from millicall.phase2.workflow_executor import WorkflowExecutor

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
        # Wait for N rings before answering (1 ring ≈ 5 seconds)
        ring_count = 0
        if workflow.definition:
            for node in workflow.definition.get("nodes", []):
                if node.get("type") == "start":
                    ring_count = int(node.get("config", {}).get("ring_count", 0))
                    break

        if ring_count > 0:
            # Answer early, then play Japanese ringback tone to simulate ringing
            await _ari_request("POST", f"/channels/{channel_id}/answer")
            await asyncio.sleep(0.3)

            # Generate Japanese ringback WAV and play it
            # 400+15Hz, 1s ON / 2s OFF, repeated ring_count times
            ringback_wav = _generate_ringback_wav(ring_count)
            sound_name = await _save_wav_to_asterisk(ringback_wav, f"ringback_{_sanitize_id(channel_id)}.wav")
            duration = ring_count * 3.0
            await _play_and_wait(channel_id, f"sound:{sound_name}", duration)
            await asyncio.sleep(0.3)
        else:
            # Answer the call immediately
            await _ari_request("POST", f"/channels/{channel_id}/answer")
            await asyncio.sleep(0.5)

        # Execute the workflow
        executor = WorkflowExecutor(channel_id, workflow)
        await executor.execute()
    except Exception as exc:
        logger.error("Workflow call error on channel %s: %s", channel_id, exc, exc_info=True)
        with contextlib.suppress(Exception):
            await _ari_request("DELETE", f"/channels/{channel_id}", params={"reason_code": "16"})
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
                        cause = event.get("cause", 0)
                        logger.info("Hangup request: channel=%s cause=%s", channel_id, cause)
                        # Don't mark channel_gone here — StasisEnd is the reliable signal.
                        # ChannelHangupRequest fires multiple times and before Answer,
                        # causing premature termination of workflows.

                    elif event_type == "PlaybackFinished":
                        playback_id = event.get("playback", {}).get("id", "")
                        ev = _playback_events.get(playback_id)
                        if ev:
                            ev.set()

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
