"""Google Cloud Text-to-Speech with Chirp3 voice support."""

import io
import logging
import wave

import httpx

logger = logging.getLogger(__name__)

GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


async def synthesize(
    text: str,
    api_key: str,
    voice_name: str = "ja-JP-Chirp3-HD-Aoede",
    language_code: str = "ja-JP",
    google_auth: object | None = None,
) -> bytes:
    """Synthesize speech using Google Cloud TTS (Chirp3 HD voices).

    Returns WAV audio bytes. Supports both API Key and Vertex AI auth.

    Available Chirp3 HD Japanese voices:
    - ja-JP-Chirp3-HD-Aoede
    - ja-JP-Chirp3-HD-Charon
    - ja-JP-Chirp3-HD-Fenrir
    - ja-JP-Chirp3-HD-Kore
    - ja-JP-Chirp3-HD-Leda
    - ja-JP-Chirp3-HD-Orus
    - ja-JP-Chirp3-HD-Puck
    - ja-JP-Chirp3-HD-Zephyr
    """
    from millicall.infrastructure.google_auth import GoogleAuth

    if isinstance(google_auth, GoogleAuth):
        url, headers = google_auth.tts_url()
    else:
        url = f"{GOOGLE_TTS_URL}?key={api_key}"
        headers = {}

    payload = {
        "input": {"text": text},
        "voice": {
            "languageCode": language_code,
            "name": voice_name,
        },
        "audioConfig": {
            "audioEncoding": "LINEAR16",
            "sampleRateHertz": 8000,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    import base64

    audio_content = base64.b64decode(data["audioContent"])

    # Wrap raw PCM in WAV header
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(audio_content)

    logger.info("Google TTS (Chirp3): %d bytes for '%s...'", len(output.getvalue()), text[:30])
    return output.getvalue()


async def synthesize_streaming(
    text: str,
    api_key: str,
    voice_name: str = "ja-JP-Chirp3-HD-Aoede",
    language_code: str = "ja-JP",
) -> bytes:
    """Same as synthesize but for longer text, splits by sentence for lower latency."""
    import re

    # Split by Japanese punctuation for incremental TTS
    sentences = re.split(r"(?<=[。！？\n])", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return b""

    # If only one sentence, just synthesize directly
    if len(sentences) == 1:
        return await synthesize(sentences[0], api_key, voice_name, language_code)

    # Concatenate audio from all sentences
    all_frames = b""
    for sentence in sentences:
        wav_data = await synthesize(sentence, api_key, voice_name, language_code)
        with wave.open(io.BytesIO(wav_data), "rb") as src:
            all_frames += src.readframes(src.getnframes())

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(all_frames)

    return output.getvalue()
