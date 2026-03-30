"""Speech-to-Text service — supports OpenAI Whisper and Google Cloud STT."""

import audioop
import io
import logging
import wave

import httpx

logger = logging.getLogger(__name__)

# STT provider: "openai" or "google" — set via smart_transcribe()
_stt_provider: str | None = None

OPENAI_API_URL = "https://api.openai.com/v1/audio/transcriptions"

# Known Whisper hallucination phrases on silence
HALLUCINATION_PHRASES = {
    "ご視聴ありがとうございました",
    "チャンネル登録お願いします",
    "ご視聴ありがとうございます",
    "チャンネル登録よろしくお願いします",
    "おやすみなさい",
    "ありがとうございました",
    "thank you for watching",
    "thanks for watching",
    "subscribe",
}


def is_silence(audio_wav: bytes, threshold: int = 500) -> bool:
    """Check if WAV audio is essentially silence."""
    try:
        with wave.open(io.BytesIO(audio_wav), "rb") as w:
            frames = w.readframes(w.getnframes())
            sampwidth = w.getsampwidth()
        rms = audioop.rms(frames, sampwidth)
        logger.debug("Audio RMS: %d (threshold: %d)", rms, threshold)
        return rms < threshold
    except Exception:
        return False


async def transcribe(audio_wav: bytes, api_key: str, language: str = "ja") -> str:
    """Transcribe audio using OpenAI Whisper API.

    Returns empty string if audio is silence or result is a known hallucination.
    """
    # Skip silence
    if is_silence(audio_wav):
        logger.info("STT skipped: audio is silence")
        return ""

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    files = {
        "file": ("audio.wav", io.BytesIO(audio_wav), "audio/wav"),
        "model": (None, "whisper-1"),
        "language": (None, language),
        "response_format": (None, "text"),
        "prompt": (None, "電話での会話です。"),
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(OPENAI_API_URL, headers=headers, files=files)
        response.raise_for_status()
        text = response.text.strip()

    # Filter hallucinations
    clean = text.replace("。", "").replace("、", "").replace(" ", "").strip()
    if clean in HALLUCINATION_PHRASES or any(clean == h for h in HALLUCINATION_PHRASES):
        logger.info("STT filtered hallucination: '%s'", text)
        return ""

    logger.info("STT result: '%s'", text[:100])
    return text


async def transcribe_google(
    audio_wav: bytes,
    api_key: str,
    language: str = "ja-JP",
    google_auth: object | None = None,
) -> str:
    """Transcribe using Google Cloud Speech-to-Text v2 (Chirp2) REST API.

    Supports both API Key and Vertex AI (service account) authentication.
    Falls back to v1 API if v2 is unavailable.
    """
    import base64

    from millicall.infrastructure.google_auth import GoogleAuth

    if is_silence(audio_wav):
        logger.info("Google STT skipped: audio is silence")
        return ""

    audio_b64 = base64.b64encode(audio_wav).decode("utf-8")

    # Use v2 API with Chirp2 model
    if isinstance(google_auth, GoogleAuth) and google_auth.mode == "vertex_ai":
        # Vertex AI endpoint
        project = google_auth.vertex_project
        location = google_auth.vertex_location
        url = (
            f"https://{location}-speech.googleapis.com/v2"
            f"/projects/{project}/locations/{location}"
            f"/recognizers/_:recognize"
        )
        _, headers = google_auth.gemini_url()  # reuse token
        payload = {
            "config": {
                "languageCodes": [language],
                "model": "chirp_2",
                "features": {
                    "enableAutomaticPunctuation": True,
                },
                "autoDecodingConfig": {},
            },
            "content": audio_b64,
        }
    else:
        # API Key — use v1 API (v2 requires project-level access)
        url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
        headers = {}
        payload = {
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": 8000,
                "languageCode": language,
                "model": "telephony",
                "useEnhanced": True,
                "enableAutomaticPunctuation": True,
            },
            "audio": {
                "content": audio_b64,
            },
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    # Parse results (v1 and v2 have slightly different formats)
    results = data.get("results", [])
    if not results:
        return ""

    text = results[0].get("alternatives", [{}])[0].get("transcript", "")
    if not text:
        return ""

    # Filter hallucinations (less common with Google STT but still check)
    clean = text.replace("。", "").replace("、", "").replace(" ", "").strip()
    if clean in HALLUCINATION_PHRASES:
        logger.info("Google STT filtered hallucination: '%s'", text)
        return ""

    logger.info("Google STT result: '%s'", text[:100])
    return text


async def smart_transcribe(audio_wav: bytes) -> str:
    """Transcribe using the configured STT provider (from DB settings).

    Automatically selects provider and handles authentication.
    """
    from millicall.application.settings_service import SettingsService
    from millicall.infrastructure.database import async_session
    from millicall.infrastructure.google_auth import get_google_auth

    global _stt_provider  # noqa: PLW0603

    async with async_session() as session:
        svc = SettingsService(session)

        # Determine provider (cache after first call)
        if _stt_provider is None:
            _stt_provider = await svc.get("stt_provider") or "openai"

        if _stt_provider == "google":
            api_key = await svc.get_api_key("google")
            stt_auth_mode = await svc.get("google_stt_auth_mode")
            if stt_auth_mode == "api_key" and api_key:
                # Force API key mode for STT even when Vertex AI is configured for LLM
                return await transcribe_google(audio_wav, api_key, google_auth=None)
            auth = await get_google_auth(session)
            return await transcribe_google(audio_wav, api_key, google_auth=auth)

        # Default: OpenAI Whisper
        api_key = await svc.get_api_key("openai")
        return await transcribe(audio_wav, api_key)
