"""Workflow execution engine for Millicall PBX.

Walks a workflow graph (nodes + edges) during an active Asterisk call,
executing each node type via ARI and routing based on DTMF input,
conditions, or simple sequential edges.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from millicall.phase2 import llm_chat, stt
from millicall.phase2.ari_handler import (
    _ari_request,
    _get_api_key,
    _get_google_auth,
    _play_and_wait,
    _sanitize_id,
    _save_wav_to_asterisk,
)

if TYPE_CHECKING:
    from millicall.domain.models import Workflow

logger = logging.getLogger(__name__)

# Global registry: channel_id -> asyncio.Queue of DTMF digits.
dtmf_queues: dict[str, asyncio.Queue[str]] = {}

# Global registry: channel_id -> bool.  Set to True on StasisEnd / hangup.
channel_gone: dict[str, bool] = {}


class ChannelHungUpError(Exception):
    """Raised when the channel has been hung up mid-execution."""


class _GotoExecutedError(Exception):
    """Internal sentinel: goto already dispatched to the target node."""


class WorkflowExecutor:
    """Executes a workflow definition during an active Asterisk call."""

    def __init__(self, channel_id: str, workflow: Workflow) -> None:
        self.channel_id = channel_id
        self.workflow = workflow
        self.definition: dict = workflow.definition or {}
        self.variables: dict[str, Any] = {}
        self.current_node_id: str | None = None
        self.safe_id = _sanitize_id(channel_id)

        if channel_id not in dtmf_queues:
            dtmf_queues[channel_id] = asyncio.Queue()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def execute(self) -> None:
        try:
            start_node = self._find_start_node()
            if not start_node:
                logger.error("Workflow %s has no start node", self.workflow.name)
                await self._hangup()
                return
            await self._execute_node(start_node)
        except ChannelHungUpError:
            logger.info("Channel %s hung up during workflow", self.channel_id)
        except Exception as exc:
            logger.error("Workflow error on %s: %s", self.channel_id, exc, exc_info=True)
            await self._hangup()
        finally:
            self._cleanup()

    # ------------------------------------------------------------------
    # Graph traversal
    # ------------------------------------------------------------------

    def _find_start_node(self) -> dict | None:
        for node in self.definition.get("nodes", []):
            if node.get("type") == "start":
                return node
        return None

    def _get_outgoing_edges(self, node_id: str) -> list[dict]:
        return [e for e in self.definition.get("edges", []) if e.get("source") == node_id]

    def _find_node_by_id(self, node_id: str) -> dict | None:
        for node in self.definition.get("nodes", []):
            if node.get("id") == node_id:
                return node
        return None

    def _get_next_node(self, current_node: dict, result: str | None = None) -> dict | None:
        edges = self._get_outgoing_edges(current_node["id"])
        if not edges:
            return None
        if result is not None:
            for edge in edges:
                label = (edge.get("label") or "").strip()
                if label and label == str(result):
                    return self._find_node_by_id(edge["target"])
                handle = (edge.get("sourceHandle") or "").strip()
                if handle and handle == str(result):
                    return self._find_node_by_id(edge["target"])
        return self._find_node_by_id(edges[0]["target"])

    async def _execute_node(self, node: dict) -> None:
        self._check_channel()
        self.current_node_id = node["id"]
        node_type = node.get("type", "")
        config = node.get("config", {})
        logger.info("Exec node %s (type=%s) ch=%s", node["id"], node_type, self.channel_id)

        handler = getattr(self, f"_exec_{node_type}", None)
        if handler is None:
            logger.warning("No handler for '%s', skipping", node_type)
            result = None
        else:
            try:
                result = await handler(node, config)
            except (ChannelHungUpError, _GotoExecutedError):
                raise
            except Exception as exc:
                logger.error("Node %s error: %s", node["id"], exc, exc_info=True)
                result = None

        next_node = self._get_next_node(node, result)
        if next_node:
            await self._execute_node(next_node)

    # ------------------------------------------------------------------
    # Channel utilities
    # ------------------------------------------------------------------

    def _check_channel(self) -> None:
        if channel_gone.get(self.channel_id):
            raise ChannelHungUpError(self.channel_id)

    async def _hangup(self) -> None:
        with contextlib.suppress(Exception):
            await _ari_request(
                "DELETE", f"/channels/{self.channel_id}", params={"reason_code": "16"}
            )

    def _cleanup(self) -> None:
        dtmf_queues.pop(self.channel_id, None)
        channel_gone.pop(self.channel_id, None)
        import glob as _glob

        for f in _glob.glob(f"/usr/share/asterisk/sounds/en/millicall/*{self.safe_id}*"):
            with contextlib.suppress(OSError):
                os.remove(f)

    async def _synthesize_one(
        self,
        text: str,
        tts_provider: str,
        google_tts_voice: str,
        coefont_voice_id: str,
    ) -> bytes:
        """Synthesize a single text segment."""
        if tts_provider == "coefont" and coefont_voice_id:
            from millicall.phase2 import tts_coefont

            return await tts_coefont.synthesize_for_asterisk(text, coefont_voice_id)
        else:
            api_key = await _get_api_key("google")
            from millicall.phase2 import tts_google
            from millicall.phase2.ari_handler import _get_google_auth

            auth = await _get_google_auth()
            return await tts_google.synthesize(
                text, api_key, voice_name=google_tts_voice, google_auth=auth
            )

    async def _play_tts(
        self,
        text: str,
        tts_provider: str = "google",
        google_tts_voice: str = "ja-JP-Chirp3-HD-Aoede",
        coefont_voice_id: str = "",
    ) -> None:
        """Synthesize text via TTS and play on the channel.

        Splits into 2 chunks: first sentence (for low latency) and the rest.
        Pipelines: synthesize chunk 2 while playing chunk 1.
        """
        self._check_channel()

        # Split: first sentence plays ASAP, rest synthesizes in background
        sentences = re.split(r"(?<=[。！？\n])", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return

        # Chunk into: first sentence, everything else
        first = sentences[0]
        rest = "".join(sentences[1:]).strip() if len(sentences) > 1 else ""

        # Synthesize first sentence immediately
        audio_first = await self._synthesize_one(
            first, tts_provider, google_tts_voice, coefont_voice_id
        )

        # Start synthesizing the rest in background
        rest_task: asyncio.Task | None = None
        if rest:
            rest_task = asyncio.create_task(
                self._synthesize_one(rest, tts_provider, google_tts_voice, coefont_voice_id)
            )

        # Play first chunk
        filename = f"wf_{self.safe_id}_{id(text) & 0xFFFFFF:06x}_0.wav"
        sound_name = await _save_wav_to_asterisk(audio_first, filename)
        duration = len(audio_first) / 16000
        await _play_and_wait(self.channel_id, f"sound:{sound_name}", duration)

        # Play rest if any
        if rest_task:
            self._check_channel()
            audio_rest = await rest_task
            filename = f"wf_{self.safe_id}_{id(text) & 0xFFFFFF:06x}_1.wav"
            sound_name = await _save_wav_to_asterisk(audio_rest, filename)
            duration = len(audio_rest) / 16000
            await _play_and_wait(self.channel_id, f"sound:{sound_name}", duration)

    def _get_tts_params(self, config: dict) -> dict:
        """Extract TTS params from node config, falling back to workflow defaults."""
        defaults = self.workflow.default_tts_config or {}
        return {
            "tts_provider": config.get("tts_provider") or defaults.get("tts_provider", "google"),
            "google_tts_voice": config.get("google_tts_voice")
            or defaults.get("google_tts_voice", "ja-JP-Chirp3-HD-Aoede"),
            "coefont_voice_id": config.get("coefont_voice_id")
            or defaults.get("coefont_voice_id", ""),
        }

    async def _play_sound_file(self, file_path: str) -> None:
        self._check_channel()
        await _ari_request(
            "POST", f"/channels/{self.channel_id}/play", params={"media": f"sound:{file_path}"}
        )
        await asyncio.sleep(3)

    async def _wait_dtmf(self, max_digits: int = 1, timeout: float = 5.0) -> str:
        self._check_channel()
        queue = dtmf_queues.get(self.channel_id)
        if queue is None:
            return ""
        collected = ""
        deadline = asyncio.get_event_loop().time() + timeout
        while len(collected) < max_digits:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                digit = await asyncio.wait_for(queue.get(), timeout=remaining)
                collected += digit
                if digit == "#":
                    break
            except TimeoutError:
                break
        return collected

    def _drain_dtmf(self) -> None:
        queue = dtmf_queues.get(self.channel_id)
        if queue:
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    # Only allow safe variable names: alphanumeric + underscore
    _SAFE_VAR_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

    def _render_template(self, text: str) -> str:
        def replacer(match: re.Match) -> str:
            var_name = match.group(1).strip()
            if not self._SAFE_VAR_RE.match(var_name):
                logger.warning("Blocked unsafe template variable: %r", var_name)
                return ""
            value = self.variables.get(var_name)
            if value is None:
                return match.group(0)
            return str(value)

        return re.sub(r"\{\{(.+?)\}\}", replacer, text)

    # ------------------------------------------------------------------
    # Node handlers
    # ------------------------------------------------------------------

    async def _exec_start(self, node: dict, config: dict) -> str | None:
        return None

    async def _exec_end(self, node: dict, config: dict) -> str | None:
        await self._hangup()
        return None

    async def _exec_hangup(self, node: dict, config: dict) -> str | None:
        await self._hangup()
        return None

    async def _exec_play_audio(self, node: dict, config: dict) -> str | None:
        tts_text = config.get("tts_text", "").strip()
        file_path = config.get("file_path", "").strip()
        if tts_text:
            rendered = self._render_template(tts_text)
            await self._play_tts(rendered, **self._get_tts_params(config))
        elif file_path:
            await self._play_sound_file(file_path)
        else:
            logger.warning("play_audio %s: no tts_text or file_path", node["id"])
        return None

    async def _exec_transfer(self, node: dict, config: dict) -> str | None:
        destination = config.get("destination", "").strip()
        if not destination:
            logger.error("transfer %s: no destination", node["id"])
            return None
        logger.info("Transfer %s → %s", self.channel_id, destination)
        try:
            await _ari_request(
                "POST",
                f"/channels/{self.channel_id}/continue",
                params={"context": "internal", "extension": destination, "priority": "1"},
            )
        except Exception as exc:
            logger.error("Transfer failed: %s", exc)
        return None

    async def _play_prompt(self, config: dict) -> None:
        """Play prompt based on prompt_mode: tts, beep, or none."""
        mode = config.get("prompt_mode", "tts")
        if mode == "beep":
            await _ari_request(
                "POST", f"/channels/{self.channel_id}/play", params={"media": "tone:beep"}
            )
            await asyncio.sleep(0.5)
        elif mode == "tts":
            text = config.get("prompt_text", "").strip()
            if text:
                await self._play_tts(self._render_template(text), **self._get_tts_params(config))

    async def _exec_dtmf_input(self, node: dict, config: dict) -> str | None:
        max_digits = int(config.get("max_digits", 1))
        timeout = float(config.get("timeout", 5))
        variable = config.get("variable", "dtmf_result")

        self._drain_dtmf()
        await self._play_prompt(config)

        # Check if DTMF was pressed during TTS playback (don't drain again)
        queue = dtmf_queues.get(self.channel_id)
        if queue and not queue.empty():
            # Already have buffered input from during playback
            digits = ""
            while not queue.empty() and len(digits) < max_digits:
                try:
                    digits += queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        else:
            digits = await self._wait_dtmf(max_digits=max_digits, timeout=timeout)

        self.variables[variable] = digits
        logger.info("DTMF: %s = '%s'", variable, digits)
        return digits

    async def _exec_menu(self, node: dict, config: dict) -> str | None:
        timeout = float(config.get("timeout", 5))
        max_retries = int(config.get("max_retries", 3))
        invalid_text = config.get("invalid_text", "入力が正しくありません。").strip()
        tts_params = self._get_tts_params(config)

        for attempt in range(max_retries):
            self._check_channel()
            self._drain_dtmf()
            await self._play_prompt(config)

            # Check buffered DTMF from during playback first
            queue = dtmf_queues.get(self.channel_id)
            if queue and not queue.empty():
                try:
                    digit = queue.get_nowait()
                except asyncio.QueueEmpty:
                    digit = ""
            else:
                digit = await self._wait_dtmf(max_digits=1, timeout=timeout)

            if digit:
                logger.info("Menu: '%s' on %s", digit, self.channel_id)
                return digit

            if invalid_text and attempt < max_retries - 1:
                await self._play_tts(invalid_text, **tts_params)

        logger.info("Menu timeout on %s", self.channel_id)
        return "timeout"

    async def _exec_condition(self, node: dict, config: dict) -> str | None:
        variable = config.get("variable", "")
        operator = config.get("operator", "eq")
        value = config.get("value", "")
        actual = str(self.variables.get(variable, ""))
        expected = str(value)

        ops = {
            "eq": actual == expected,
            "neq": actual != expected,
            "gt": _safe_float(actual) > _safe_float(expected),
            "lt": _safe_float(actual) < _safe_float(expected),
            "gte": _safe_float(actual) >= _safe_float(expected),
            "lte": _safe_float(actual) <= _safe_float(expected),
            "contains": expected in actual,
        }
        match = ops.get(operator, False)
        result = "true" if match else "false"
        logger.info("Condition: %s %s %s => %s", variable, operator, expected, result)
        return result

    async def _exec_set_variable(self, node: dict, config: dict) -> str | None:
        variable = config.get("variable", "")
        value = config.get("value", "")
        self.variables[variable] = self._render_template(value)
        return None

    async def _exec_goto(self, node: dict, config: dict) -> str | None:
        target_id = config.get("target_node_id", "")
        target_node = self._find_node_by_id(target_id)
        if target_node:
            await self._execute_node(target_node)
            raise _GotoExecutedError()
        logger.error("goto target '%s' not found", target_id)
        return None

    async def _exec_time_condition(self, node: dict, config: dict) -> str | None:
        now = datetime.now()
        start_str = config.get("start_time", "09:00")
        end_str = config.get("end_time", "18:00")
        days = config.get("days_of_week", ["mon", "tue", "wed", "thu", "fri"])

        try:
            sh, sm = (int(x) for x in start_str.split(":"))
            eh, em = (int(x) for x in end_str.split(":"))
        except (ValueError, AttributeError):
            return "no_match"

        day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
        if isinstance(days, str):
            days = [d.strip() for d in days.split(",")]
        allowed = {day_map.get(d.lower(), -1) for d in days}

        if now.weekday() not in allowed:
            return "no_match"

        cur = now.hour * 60 + now.minute
        if sh * 60 + sm <= cur < eh * 60 + em:
            return "match"
        return "no_match"

    async def _exec_voicemail(self, node: dict, config: dict) -> str | None:
        mailbox = config.get("mailbox", "").strip()
        greeting_text = config.get("greeting_text", "").strip()
        if not mailbox:
            logger.error("voicemail %s: no mailbox", node["id"])
            return None
        if greeting_text:
            await self._play_tts(
                self._render_template(greeting_text), **self._get_tts_params(config)
            )
        try:
            await _ari_request(
                "POST",
                f"/channels/{self.channel_id}/continue",
                params={"context": "voicemail", "extension": mailbox, "priority": "1"},
            )
        except Exception as exc:
            logger.error("Voicemail redirect failed: %s", exc)
        return None

    async def _record_with_vad(self, recording_name: str, max_duration: int = 15) -> bytes | None:
        """Record audio with VAD-based end-of-speech detection.

        Starts recording without silence detection, polls the recording
        periodically, and uses VAD to detect when the user stops speaking.
        """
        from millicall.phase2.vad import detect_end_of_speech

        self._check_channel()
        try:
            await _ari_request(
                "POST",
                f"/channels/{self.channel_id}/record",
                params={
                    "name": recording_name,
                    "format": "wav",
                    "maxDurationSeconds": str(max_duration),
                    "maxSilenceSeconds": "0",
                    "beep": "false",
                    "terminateOn": "#",
                    "ifExists": "overwrite",
                },
            )
        except Exception:
            return None

        # Poll recording and check VAD every 0.3s
        audio_data = None
        grace_polls = 0  # grace period polls after first speech_ended
        GRACE_LIMIT = 5  # up to 1.5s grace to catch continuation speech
        pending_end = False
        for poll in range(max_duration * 4 + 8):
            await asyncio.sleep(0.3)
            self._check_channel()

            try:
                result = await _ari_request(
                    "GET", f"/recordings/stored/{recording_name}/file"
                )
            except Exception:
                try:
                    live = await _ari_request("GET", f"/recordings/live/{recording_name}")
                    if isinstance(live, dict) and live.get("duration", 0) >= max_duration:
                        continue
                except Exception:
                    pass
                continue

            if not result or not isinstance(result, bytes) or len(result) < 1000:
                continue

            vad_result = detect_end_of_speech(result)
            logger.debug(
                "VAD: speech=%s ended=%s speech_ms=%d silence_ms=%d",
                vad_result["has_speech"],
                vad_result["speech_ended"],
                vad_result["speech_ms"],
                vad_result["trailing_silence_ms"],
            )

            if vad_result["speech_ended"]:
                if not pending_end:
                    # First speech_ended — start grace period to catch continuation
                    pending_end = True
                    grace_polls = 0
                    logger.debug("VAD: speech ended, starting grace period")
                else:
                    grace_polls += 1
                    if grace_polls >= GRACE_LIMIT:
                        # Grace period elapsed with no new speech — done
                        logger.info(
                            "VAD: speech ended after %dms (silence %dms)",
                            vad_result["speech_ms"],
                            vad_result["trailing_silence_ms"],
                        )
                        audio_data = result
                        break
            elif pending_end and vad_result["has_speech"] and not vad_result["speech_ended"]:
                # New speech detected during grace period — user is still talking
                logger.info("VAD: continuation speech detected, resetting")
                pending_end = False
                grace_polls = 0

            if not vad_result["has_speech"] and poll >= 17:
                # 5+ seconds with no speech at all — give up
                logger.info("VAD: no speech detected after %ds", poll * 0.3)
                break

        # If recording is still live, stop it
        with contextlib.suppress(Exception):
            await _ari_request("POST", f"/recordings/live/{recording_name}/stop")

        # Final fetch if we don't have data yet
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

    async def _exec_ai_conversation(self, node: dict, config: dict) -> str | None:
        system_prompt = config.get("system_prompt", "あなたは電話応対AIアシスタントです。")
        provider = config.get("llm_provider", "google")
        llm_model = config.get("llm_model", "gemini-2.5-flash")
        max_turns = int(config.get("max_turns", 10))
        greeting_text = config.get("greeting_text", "").strip()
        extraction_mode = config.get("extraction_mode", "auto")
        tts_params = self._get_tts_params(config)

        os.makedirs("/var/spool/asterisk/recording", exist_ok=True)
        context = llm_chat.ConversationContext(max_history=max_turns * 2)

        # Detect variables to extract from system prompt
        var_names = re.findall(r"`(\w+)`", system_prompt)
        exclude = {"true", "false", "null", "none", "int", "str", "float", "bool"}
        var_names = [v for v in var_names if v.lower() not in exclude and len(v) > 1]

        # Build extraction instructions based on mode
        extraction_instructions = ""
        if var_names:
            if extraction_mode == "direct":
                extraction_instructions = (
                    "\n\n[最重要タスク] あなたの最優先の目的は、以下の情報を聞き出すことです。"
                    "最初のターンから本題に入り、必要な情報を聞き出してください。"
                    "情報が得られたら [END_CALL] を付けて会話を終了してください。"
                    f"\n聞き出す情報: {', '.join(var_names)}"
                )
            else:
                # auto: 自然に聞き出す。会話が長引いたら切り上げる
                extraction_instructions = (
                    "\n\n[重要タスク] 会話の中で、以下の情報を自然に聞き出してください。"
                    "雑談が続いた場合は、2〜3ターン以内に本題に移ってください。"
                    "情報が得られたら [END_CALL] を付けて会話を終了してください。"
                    f"\n聞き出す情報: {', '.join(var_names)}"
                )

        full_prompt = (
            system_prompt
            + extraction_instructions
            + "\n\n[重要ルール]"
            "\n- これは電話会話です。応答は最大2文、40文字以内で簡潔に。"
            "\n- 最初の一文は必ず短く（15文字以内の相槌や返事）。例:「ああ、そうだね！」「ふむ、なるほど。」"
            "\n- 会話が自然に終わる場面では、最後の応答の末尾に [END_CALL] と付けてください。"
            "このタグはユーザーには見えません。通常の会話中は絶対に付けないでください。"
        )

        # Create call log
        call_log_id = None
        turn_counter = 0
        try:
            from millicall.domain.models import CallLog
            from millicall.infrastructure.database import async_session
            from millicall.infrastructure.repositories.call_log_repo import CallLogRepository

            async with async_session() as session:
                repo = CallLogRepository(session)
                call_log_id = await repo.create_log(
                    CallLog(
                        agent_id=0,
                        agent_name=self.workflow.name,
                        extension_number=self.workflow.number,
                        caller_channel=self.channel_id,
                        started_at=datetime.now(),
                    )
                )
        except Exception as e:
            logger.error("Failed to create call log: %s", e)

        if greeting_text:
            await self._play_tts(self._render_template(greeting_text), **tts_params)

        for turn in range(max_turns):
            self._check_channel()

            # Record with VAD-based end-of-speech detection
            recording_name = f"wf_{self.safe_id}_{turn}"
            audio_data = await self._record_with_vad(recording_name)
            if not audio_data:
                continue

            import time as _time

            _t_stt_start = _time.monotonic()
            try:
                user_text = await stt.smart_transcribe(audio_data)
            except Exception as exc:
                logger.error("STT failed: %s", exc)
                continue
            _t_stt_end = _time.monotonic()
            logger.info("LATENCY stt=%.1fms", (_t_stt_end - _t_stt_start) * 1000)

            user_text = user_text.strip()
            if not user_text:
                continue

            with contextlib.suppress(Exception):
                await _ari_request("DELETE", f"/recordings/stored/{recording_name}")

            try:
                _t_llm_start = _time.monotonic()
                llm_key = await _get_api_key(provider)
                auth = await _get_google_auth() if provider == "google" else None

                # Use streaming for Google to get first sentence ASAP
                if provider == "google":
                    first_sentence_future: asyncio.Future[str] = asyncio.get_event_loop().create_future()
                    llm_task = asyncio.create_task(
                        llm_chat.chat_google_streaming(
                            user_text=user_text,
                            context=context,
                            system_prompt=full_prompt,
                            api_key=llm_key,
                            model=llm_model,
                            google_auth=auth,
                            on_first_sentence=first_sentence_future,
                        )
                    )

                    # Wait for first sentence, start TTS immediately
                    first_sentence = await first_sentence_future
                    _t_first_sentence = _time.monotonic()
                    logger.info("LATENCY llm_first_sentence=%.1fms", (_t_first_sentence - _t_llm_start) * 1000)
                    first_sentence_clean = first_sentence.replace("[END_CALL]", "").strip()
                    if first_sentence_clean:
                        tts_task = asyncio.create_task(
                            self._synthesize_one(
                                first_sentence_clean, **tts_params_for_synth
                            )
                        ) if (tts_params_for_synth := {
                            "tts_provider": tts_params.get("tts_provider", "google"),
                            "google_tts_voice": tts_params.get("google_tts_voice", ""),
                            "coefont_voice_id": tts_params.get("coefont_voice_id", ""),
                        }) else None

                    # Wait for full response
                    response_text = await llm_task
                    _t_llm_end = _time.monotonic()
                    logger.info("LATENCY llm_full=%.1fms", (_t_llm_end - _t_llm_start) * 1000)

                    # Play first sentence while rest synthesizes
                    if first_sentence_clean and tts_task:
                        _t_tts_start = _time.monotonic()
                        audio_first = await tts_task
                        logger.info("LATENCY tts_first=%.1fms", (_time.monotonic() - _t_tts_start) * 1000)
                        filename = f"wf_{self.safe_id}_{turn}_first.wav"
                        sound_name = await _save_wav_to_asterisk(audio_first, filename)
                        duration = len(audio_first) / 16000
                        await _play_and_wait(self.channel_id, f"sound:{sound_name}", duration)

                        # Play the rest
                        rest_text = response_text.replace("[END_CALL]", "").strip()
                        # Remove first sentence from rest
                        rest_text = rest_text[len(first_sentence_clean):].strip()
                        if rest_text:
                            await self._play_tts(rest_text, **tts_params)

                        should_hangup = "[END_CALL]" in response_text
                        response_text = response_text.replace("[END_CALL]", "").strip()
                    else:
                        should_hangup = "[END_CALL]" in response_text
                        response_text = response_text.replace("[END_CALL]", "").strip()
                        if response_text:
                            await self._play_tts(response_text, **tts_params)
                else:
                    response_text = await llm_chat.generate_response(
                        user_text=user_text,
                        context=context,
                        system_prompt=full_prompt,
                        provider=provider,
                        api_key=llm_key,
                        model=llm_model,
                        google_auth=auth,
                    )
                    logger.info("LATENCY llm_full=%.1fms", (_time.monotonic() - _t_llm_start) * 1000)
                    should_hangup = "[END_CALL]" in response_text
                    response_text = response_text.replace("[END_CALL]", "").strip()
                    if response_text:
                        await self._play_tts(response_text, **tts_params)

            except Exception as exc:
                logger.error("LLM failed: %s", exc)
                response_text = "申し訳ございません、少々お待ちください。"
                should_hangup = False
                await self._play_tts(response_text, **tts_params)

            response_text = response_text.replace("[END_CALL]", "").strip()
            context.add_message("user", user_text)
            context.add_message("assistant", response_text)
            turn_counter += 1
            self.variables["last_user_text"] = user_text
            self.variables["last_ai_response"] = response_text

            # Save messages to call log
            if call_log_id:
                try:
                    from millicall.domain.models import CallMessage
                    from millicall.infrastructure.database import async_session
                    from millicall.infrastructure.repositories.call_log_repo import (
                        CallLogRepository,
                    )

                    async with async_session() as session:
                        repo = CallLogRepository(session)
                        await repo.add_message(
                            CallMessage(
                                call_log_id=call_log_id,
                                role="user",
                                content=user_text,
                                turn=turn_counter,
                                created_at=datetime.now(),
                            )
                        )
                        await repo.add_message(
                            CallMessage(
                                call_log_id=call_log_id,
                                role="assistant",
                                content=response_text,
                                turn=turn_counter,
                                created_at=datetime.now(),
                            )
                        )
                except Exception as e:
                    logger.error("Failed to save call message: %s", e)

            if should_hangup:
                break

            with contextlib.suppress(Exception):
                await _ari_request("DELETE", f"/recordings/stored/{recording_name}")

        # Extract variables from conversation if system prompt mentions them
        await self._extract_variables_from_conversation(system_prompt, context, provider, llm_model)

        # Finalize call log
        if call_log_id:
            try:
                from millicall.infrastructure.database import async_session
                from millicall.infrastructure.repositories.call_log_repo import CallLogRepository

                async with async_session() as session:
                    repo = CallLogRepository(session)
                    await repo.finish_log(call_log_id, turn_counter)
            except Exception as e:
                logger.error("Failed to finalize call log: %s", e)

        return None

    async def _extract_variables_from_conversation(
        self,
        system_prompt: str,
        context: llm_chat.ConversationContext,
        provider: str,
        llm_model: str,
    ) -> None:
        """After AI conversation, extract variable values from the conversation history.

        Scans the system prompt for backtick-quoted variable names (e.g. `var_name`)
        and asks the LLM to extract their values from the conversation.
        """
        # Find variable names mentioned in backticks in the system prompt
        var_names = re.findall(r"`(\w+)`", system_prompt)
        # Filter to plausible variable names (exclude common code terms)
        exclude = {"true", "false", "null", "none", "int", "str", "float", "bool"}
        var_names = [v for v in var_names if v.lower() not in exclude and len(v) > 1]

        if not var_names:
            return

        # Build conversation transcript
        transcript = "\n".join(
            f"{'ユーザー' if m.role == 'user' else 'AI'}: {m.content}" for m in context.messages
        )
        if not transcript.strip():
            return

        extraction_prompt = (
            "以下の会話から、指定された変数の値を抽出してください。\n"
            "JSON形式で回答してください。値が会話から読み取れない場合は空文字にしてください。\n\n"
            f"抽出する変数: {', '.join(var_names)}\n\n"
            f"会話:\n{transcript}\n\n"
            "回答（JSONのみ）:"
        )

        try:
            llm_key = await _get_api_key(provider)
            auth = await _get_google_auth() if provider == "google" else None
            extract_ctx = llm_chat.ConversationContext(max_history=2)
            result = await llm_chat.generate_response(
                user_text=extraction_prompt,
                context=extract_ctx,
                system_prompt="あなたはデータ抽出AIです。会話から指定された情報を抽出し、JSON形式で返してください。",
                provider=provider,
                api_key=llm_key,
                model=llm_model,
                google_auth=auth,
            )

            # Parse JSON from response
            result = result.strip()
            # Strip markdown code blocks if present
            if result.startswith("```"):
                result = re.sub(r"^```(?:json)?\s*\n?", "", result)
                result = re.sub(r"\n?```$", "", result)
                result = result.strip()

            extracted = json.loads(result)
            if isinstance(extracted, dict):
                for var_name in var_names:
                    value = extracted.get(var_name, "")
                    if value:
                        self.variables[var_name] = str(value)
                        logger.info("Extracted variable %s = '%s'", var_name, str(value)[:100])
        except Exception as exc:
            logger.error("Variable extraction failed: %s", exc)

    async def _exec_intent_detection(self, node: dict, config: dict) -> str | None:
        """Use LLM to classify the caller's last utterance into an intent."""
        intents = config.get("intents", [])
        provider = config.get("llm_provider", "google")
        llm_model = config.get("llm_model", "gemini-2.5-flash")
        fallback = config.get("fallback_intent", "other")

        user_text = self.variables.get("last_user_text", "")
        if not user_text:
            return fallback

        if isinstance(intents, list):
            intent_desc = "\n".join(
                f"- {i['key']}: {i['value']}" for i in intents if isinstance(i, dict)
            )
            intent_keys = [i["key"] for i in intents if isinstance(i, dict)]
        else:
            return fallback

        prompt = (
            f"以下のユーザー発話を分類してください。\n\n"
            f"発話: 「{user_text}」\n\n"
            f"分類先:\n{intent_desc}\n\n"
            f"回答はキー名のみを1つ返してください（{', '.join(intent_keys)}）。"
        )

        try:
            llm_key = await _get_api_key(provider)
            auth = await _get_google_auth() if provider == "google" else None
            ctx = llm_chat.ConversationContext(max_history=2)
            result = await llm_chat.generate_response(
                user_text=prompt,
                context=ctx,
                system_prompt="あなたは意図分類AIです。キー名のみ回答してください。",
                provider=provider,
                api_key=llm_key,
                model=llm_model,
                google_auth=auth,
            )
            detected = result.strip().lower()
            if detected in [k.lower() for k in intent_keys]:
                self.variables["detected_intent"] = detected
                return detected
        except Exception as exc:
            logger.error("Intent detection failed: %s", exc)

        self.variables["detected_intent"] = fallback
        return fallback

    async def _exec_collect_info(self, node: dict, config: dict) -> str | None:
        """Conversationally collect information fields from the caller."""
        fields = config.get("fields", [])
        config.get("llm_provider", "google")
        config.get("llm_model", "gemini-2.5-flash")
        tts_params = self._get_tts_params(config)

        if not isinstance(fields, list):
            return None

        os.makedirs("/var/spool/asterisk/recording", exist_ok=True)

        for field in fields:
            if not isinstance(field, dict):
                continue
            var_name = field.get("key", "")
            question = field.get("value", "")
            if not var_name or not question:
                continue

            self._check_channel()
            await self._play_tts(self._render_template(question), **tts_params)

            # Record answer
            rec_name = f"wf_{self.safe_id}_collect_{var_name}"
            try:
                await _ari_request(
                    "POST",
                    f"/channels/{self.channel_id}/record",
                    params={
                        "name": rec_name,
                        "format": "wav",
                        "maxDurationSeconds": "30",
                        "maxSilenceSeconds": "4",
                        "beep": "false",
                        "terminateOn": "none",
                    },
                )
            except Exception:
                continue

            audio_data = None
            for _ in range(18):
                await asyncio.sleep(1)
                self._check_channel()
                try:
                    result = await _ari_request("GET", f"/recordings/stored/{rec_name}/file")
                    if result and isinstance(result, bytes) and len(result) > 100:
                        audio_data = result
                        break
                except Exception:
                    continue

            if not audio_data:
                continue

            try:
                answer = await stt.smart_transcribe(audio_data)
                self.variables[var_name] = answer.strip()
                logger.info("Collected %s = '%s'", var_name, answer.strip())
            except Exception as exc:
                logger.error("STT failed for collect_info: %s", exc)

            with contextlib.suppress(Exception):
                await _ari_request("DELETE", f"/recordings/stored/{rec_name}")

        return None

    async def _exec_api_call(self, node: dict, config: dict) -> str | None:
        """Call an external HTTP API. Supports JSON and form-urlencoded."""
        import urllib.parse

        import httpx

        url = self._render_template(config.get("url", ""))
        method = config.get("method", "POST").upper()
        headers = config.get("headers", {})
        body_template = config.get("body_template", "").strip()
        content_type = config.get("content_type", "json")
        result_var = config.get("result_variable", "api_result")

        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except Exception:
                headers = {}

        body = None
        form_data = None
        if body_template:
            rendered = self._render_template(body_template)
            if content_type == "form":
                # Parse as key=value pairs or JSON -> form data
                try:
                    form_data = json.loads(rendered)
                except Exception:
                    # Parse key=value&key=value format
                    form_data = dict(urllib.parse.parse_qsl(rendered))
            else:
                try:
                    body = json.loads(rendered)
                except Exception:
                    body = rendered

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                if form_data is not None:
                    resp = await client.request(
                        method,
                        url,
                        headers=headers,
                        data=form_data,
                    )
                else:
                    resp = await client.request(
                        method,
                        url,
                        headers=headers,
                        json=body if isinstance(body, dict) else None,
                        content=body if isinstance(body, str) else None,
                    )
                self.variables[result_var] = resp.text
                self.variables[f"{result_var}_status"] = str(resp.status_code)
                logger.info("API call %s %s => %d", method, url, resp.status_code)
                return "success" if resp.is_success else "error"
        except Exception as exc:
            logger.error("API call failed: %s", exc)
            self.variables[result_var] = str(exc)
            self.variables[f"{result_var}_status"] = "0"
            return "error"

    async def _exec_email_notify(self, node: dict, config: dict) -> str | None:
        """Send email notification (logs for now, actual SMTP can be added later)."""
        to = config.get("to", "")
        subject = self._render_template(config.get("subject_template", ""))
        body = self._render_template(config.get("body_template", ""))
        # TODO: implement actual SMTP sending
        logger.info("EMAIL NOTIFY: to=%s subject=%s body=%s", to, subject, body[:200])
        self.variables["email_sent"] = "true"
        return None

    async def _exec_human_escalation(self, node: dict, config: dict) -> str | None:
        destination = config.get("destination", "").strip()
        announcement_text = config.get("announcement_text", "").strip()
        if not destination:
            logger.error("human_escalation %s: no destination", node["id"])
            return None
        if announcement_text:
            await self._play_tts(
                self._render_template(announcement_text), **self._get_tts_params(config)
            )
        logger.info("Escalating %s → %s", self.channel_id, destination)
        try:
            await _ari_request(
                "POST",
                f"/channels/{self.channel_id}/continue",
                params={"context": "internal", "extension": destination, "priority": "1"},
            )
        except Exception as exc:
            logger.error("Escalation failed: %s", exc)
        return None

    async def _exec_call_workflow(self, node: dict, config: dict) -> str | None:
        workflow_id = config.get("workflow_id")
        if not workflow_id:
            logger.error("call_workflow %s: no workflow_id", node["id"])
            return None
        try:
            from millicall.infrastructure.database import async_session
            from millicall.infrastructure.repositories.workflow_repo import WorkflowRepository

            async with async_session() as session:
                repo = WorkflowRepository(session)
                sub_wf = await repo.get_by_id(int(workflow_id))
            if not sub_wf or not sub_wf.enabled:
                logger.warning("Sub-workflow %s not found/disabled", workflow_id)
                return None
            sub = WorkflowExecutor(self.channel_id, sub_wf)
            sub.variables = self.variables
            await sub.execute()
            self.variables.update(sub.variables)
        except ChannelHungUpError:
            raise
        except Exception as exc:
            logger.error("Sub-workflow failed: %s", exc, exc_info=True)
        return None


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
