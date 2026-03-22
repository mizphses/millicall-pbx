"""Speech-to-Text service using OpenAI Whisper API."""

import audioop
import io
import logging
import wave

import httpx

logger = logging.getLogger(__name__)

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


async def transcribe_google(audio_wav: bytes, api_key: str, language: str = "ja") -> str:
    """Transcribe using Google Cloud Speech-to-Text v1 REST API."""
    import base64

    url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"

    audio_b64 = base64.b64encode(audio_wav).decode("utf-8")

    payload = {
        "config": {
            "encoding": "LINEAR16",
            "sampleRateHertz": 8000,
            "languageCode": language,
        },
        "audio": {
            "content": audio_b64,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])
    if not results:
        return ""

    text = results[0]["alternatives"][0]["transcript"]
    logger.info("Google STT result: '%s'", text[:100])
    return text
