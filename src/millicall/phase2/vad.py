"""Voice Activity Detection using webrtcvad.

Provides real-time end-of-speech detection for recorded audio.
"""

import io
import logging
import wave

import webrtcvad

logger = logging.getLogger(__name__)

# VAD aggressiveness: 0-3 (higher = more aggressive at filtering non-speech)
VAD_MODE = 2

# End-of-speech parameters
SPEECH_START_FRAMES = 3       # Need 3 speech frames to confirm speech started
SILENCE_END_MS = 1000         # 1.0s of silence after speech = end of utterance
MIN_SPEECH_MS = 200           # Minimum speech duration to be considered valid
FRAME_MS = 30                 # Frame duration for VAD


def detect_end_of_speech(wav_data: bytes) -> dict:
    """Analyze WAV audio and detect if user has finished speaking.

    Returns:
        {
            "has_speech": bool,      # Whether speech was detected at all
            "speech_ended": bool,    # Whether speech started and then ended
            "speech_ms": int,        # Total milliseconds of speech
            "trailing_silence_ms": int,  # Silence at end of audio
        }
    """
    result = {
        "has_speech": False,
        "speech_ended": False,
        "speech_ms": 0,
        "trailing_silence_ms": 0,
    }

    try:
        pcm, sample_rate = _wav_to_pcm(wav_data)
    except Exception:
        return result

    vad = webrtcvad.Vad(VAD_MODE)
    frame_size = int(sample_rate * FRAME_MS / 1000) * 2  # bytes per frame

    if len(pcm) < frame_size:
        return result

    # Track speech/silence state
    speech_started = False
    consecutive_speech = 0
    consecutive_silence = 0
    total_speech_ms = 0
    last_speech_end_pos = 0

    pos = 0
    frame_count = 0
    while pos + frame_size <= len(pcm):
        chunk = pcm[pos: pos + frame_size]
        try:
            is_speech = vad.is_speech(chunk, sample_rate)
        except Exception:
            pos += frame_size
            frame_count += 1
            continue

        if is_speech:
            consecutive_speech += 1
            consecutive_silence = 0
            total_speech_ms += FRAME_MS

            if consecutive_speech >= SPEECH_START_FRAMES:
                speech_started = True
                last_speech_end_pos = frame_count
        else:
            consecutive_silence += 1
            consecutive_speech = 0

        pos += frame_size
        frame_count += 1

    trailing_silence_ms = (frame_count - last_speech_end_pos) * FRAME_MS if speech_started else 0

    result["has_speech"] = speech_started and total_speech_ms >= MIN_SPEECH_MS
    result["speech_ms"] = total_speech_ms
    result["trailing_silence_ms"] = trailing_silence_ms
    result["speech_ended"] = (
        speech_started
        and total_speech_ms >= MIN_SPEECH_MS
        and trailing_silence_ms >= SILENCE_END_MS
    )

    return result


def _wav_to_pcm(wav_data: bytes) -> tuple[bytes, int]:
    """Convert WAV to mono 16-bit PCM at a supported sample rate."""
    import audioop

    with wave.open(io.BytesIO(wav_data), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if channels == 2:
        frames = audioop.tomono(frames, sample_width, 1, 1)
    if sample_width != 2:
        frames = audioop.lin2lin(frames, sample_width, 2)
    if sample_rate not in (8000, 16000, 32000, 48000):
        frames, _ = audioop.ratecv(frames, 2, 1, sample_rate, 16000, None)
        sample_rate = 16000

    return frames, sample_rate
