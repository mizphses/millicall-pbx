"""CoeFont Text-to-Speech API client."""

import hashlib
import hmac
import logging
import time

import httpx

from millicall.config import settings

logger = logging.getLogger(__name__)

COEFONT_API_URL = "https://api.coefont.cloud/v2/text2speech"


async def synthesize(text: str, coefont_id: str | None = None) -> bytes:
    """Convert text to speech using CoeFont API.

    Returns WAV audio bytes.
    """
    voice_id = coefont_id or settings.coefont_voice_id

    # Try DB settings first, then fall back to config/env
    from millicall.application.settings_service import SettingsService
    from millicall.infrastructure.database import async_session

    async with async_session() as session:
        svc = SettingsService(session)
        access_key = await svc.get("coefont_access_key") or settings.coefont_access_key
        access_secret = await svc.get("coefont_access_secret") or settings.coefont_access_secret

    if not access_key or not access_secret:
        raise RuntimeError("CoeFont API credentials not configured")

    # Build request body
    import json as _json
    payload = {
        "coefont": voice_id,
        "text": text,
    }
    data = _json.dumps(payload)

    # HMAC-SHA256 authentication: sign(date + json_body)
    timestamp = str(int(time.time()))
    signature = hmac.new(
        access_secret.encode("utf-8"),
        (timestamp + data).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": access_key,
        "X-Coefont-Date": timestamp,
        "X-Coefont-Content": signature,
    }

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        response = await client.post(COEFONT_API_URL, content=data, headers=headers)
        response.raise_for_status()
        logger.info("CoeFont TTS: %d bytes for '%s...'", len(response.content), text[:30])
        return response.content


async def synthesize_for_asterisk(text: str, coefont_id: str | None = None) -> bytes:
    """Synthesize and convert to format Asterisk can play (16-bit PCM, 8kHz mono).

    Returns raw signed linear 16-bit audio (slin) suitable for Asterisk playback.
    """
    import io
    import wave
    import audioop

    wav_data = await synthesize(text, coefont_id)

    # Read source WAV
    with wave.open(io.BytesIO(wav_data), "rb") as src:
        channels = src.getnchannels()
        sampwidth = src.getsampwidth()
        framerate = src.getframerate()
        frames = src.readframes(src.getnframes())

    # Convert to mono if stereo
    if channels == 2:
        frames = audioop.tomono(frames, sampwidth, 1, 1)

    # Resample to 8kHz if needed
    if framerate != 8000:
        frames, _ = audioop.ratecv(frames, sampwidth, 1, framerate, 8000, None)

    # Convert to 16-bit if needed
    if sampwidth != 2:
        frames = audioop.lin2lin(frames, sampwidth, 2)

    # Write as WAV for Asterisk
    output = io.BytesIO()
    with wave.open(output, "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(8000)
        dst.writeframes(frames)

    return output.getvalue()
