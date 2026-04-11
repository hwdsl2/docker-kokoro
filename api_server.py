#!/usr/bin/env python3
"""
Kokoro Text-to-Speech API Server
Provides an OpenAI-compatible /v1/audio/speech endpoint
powered by Kokoro TTS.

https://github.com/hwdsl2/docker-kokoro

Copyright (C) 2026 Lin Song <linsongui@gmail.com>

This work is licensed under the MIT License
See: https://opensource.org/licenses/MIT
"""

import io
import logging
import os
import subprocess
import time
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_log_level_str = os.environ.get("KOKORO_LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_str, logging.INFO)
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("kokoro_server")

# ---------------------------------------------------------------------------
# Voice mapping — OpenAI voice names → Kokoro voice IDs
# ---------------------------------------------------------------------------

# All available Kokoro voices
KOKORO_VOICES = {
    # American English female
    "af_heart":    "American female — warm, natural (recommended default)",
    "af_bella":    "American female — expressive",
    "af_nova":     "American female — clear",
    "af_sky":      "American female — neutral, versatile",
    "af_sarah":    "American female — conversational",
    "af_nicole":   "American female — friendly",
    "af_alloy":    "American female — balanced",
    "af_jessica":  "American female — energetic",
    "af_river":    "American female — calm",
    # American English male
    "am_adam":     "American male — deep",
    "am_michael":  "American male — clear",
    "am_echo":     "American male — neutral",
    "am_eric":     "American male — authoritative",
    "am_fenrir":   "American male — distinctive",
    "am_liam":     "American male — conversational",
    "am_onyx":     "American male — rich",
    "am_puck":     "American male — expressive",
    "am_santa":    "American male — warm",
    # British English female
    "bf_emma":     "British female — clear, professional",
    "bf_isabella": "British female — warm",
    "bf_alice":    "British female — crisp",
    "bf_lily":     "British female — soft",
    # British English male
    "bm_george":   "British male — authoritative",
    "bm_lewis":    "British male — smooth",
    "bm_daniel":   "British male — calm",
    "bm_fable":    "British male — expressive",
}

# OpenAI API voice aliases → canonical Kokoro voice IDs
_OPENAI_VOICE_MAP = {
    "alloy":   "af_alloy",
    "echo":    "am_echo",
    "fable":   "bm_fable",
    "onyx":    "am_onyx",
    "nova":    "af_nova",
    "shimmer": "af_bella",
    "ash":     "am_michael",
    "coral":   "af_heart",
    "sage":    "af_sky",
    "verse":   "bm_george",
}

def _resolve_voice(voice: str) -> str:
    """
    Accept OpenAI voice alias or a native Kokoro voice ID.
    Returns the resolved Kokoro voice ID.
    """
    v = voice.strip().lower()
    # Direct Kokoro name (e.g. "af_heart")
    if v in KOKORO_VOICES:
        return v
    # OpenAI alias (e.g. "alloy")
    if v in _OPENAI_VOICE_MAP:
        return _OPENAI_VOICE_MAP[v]
    # Unknown — fall back to default
    default = os.environ.get("KOKORO_VOICE", "af_heart").strip()
    logger.warning("Unknown voice '%s', falling back to '%s'", voice, default)
    return default


# ---------------------------------------------------------------------------
# Model — loaded once at startup via the FastAPI lifespan hook
# ---------------------------------------------------------------------------

_pipeline = None   # KPipeline instance


def _load_model() -> None:
    """Import and initialise the Kokoro pipeline from environment config."""
    global _pipeline

    from kokoro import KPipeline  # deferred — keeps import fast

    lang_code = os.environ.get("KOKORO_LANG_CODE", "a").strip()  # 'a'=American, 'b'=British
    local_files_only = bool(os.environ.get("KOKORO_LOCAL_ONLY", "").strip())

    logger.info(
        "Loading Kokoro TTS pipeline | lang_code=%s local_only=%s",
        lang_code, local_files_only,
    )
    t0 = time.monotonic()

    if local_files_only:
        # HF_HUB_OFFLINE prevents huggingface_hub from making any network requests.
        # HUGGINGFACE_HUB_OFFLINE is the older name kept for compatibility.
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HUGGINGFACE_HUB_OFFLINE"] = "1"

    _pipeline = KPipeline(lang_code=lang_code)

    logger.info("Kokoro TTS pipeline ready in %.1fs", time.monotonic() - t0)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _load_model()
    yield


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Kokoro Text-to-Speech",
    description=(
        "OpenAI-compatible text-to-speech API powered by Kokoro TTS.\n\n"
        "https://github.com/hwdsl2/docker-kokoro"
    ),
    version="1.0.0",
    lifespan=_lifespan,
)

# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


def _verify_api_key(authorization: Optional[str] = Header(default=None)) -> None:
    """
    If KOKORO_API_KEY is set, require a matching Bearer token.
    If the env var is empty or unset the endpoint is open (no auth).
    """
    required = os.environ.get("KOKORO_API_KEY", "").strip()
    if not required:
        return
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header. Expected: Bearer <key>",
        )
    if parts[1] != required:
        raise HTTPException(status_code=401, detail="Invalid API key.")


# ---------------------------------------------------------------------------
# Audio format helpers
# ---------------------------------------------------------------------------

# Content-type for each supported response format
_FORMAT_MIME = {
    "mp3":  "audio/mpeg",
    "opus": "audio/ogg; codecs=opus",
    "aac":  "audio/aac",
    "flac": "audio/flac",
    "wav":  "audio/wav",
    "pcm":  "audio/pcm",
}

# Per-format ffmpeg output flags for formats soundfile cannot write natively.
# opus requires '-c:a libopus' explicitly; without it ffmpeg defaults to libvorbis
# for OGG containers, producing OGG/Vorbis instead of the declared OGG/Opus.
_FFMPEG_OUTPUT_ARGS = {
    "mp3":  ["-f", "mp3"],
    "aac":  ["-f", "adts"],
    "opus": ["-c:a", "libopus", "-f", "ogg"],
}


def _audio_to_bytes(samples: np.ndarray, sample_rate: int, fmt: str) -> bytes:
    """
    Convert a float32 numpy audio array to the requested output format bytes.

    - wav / flac: written directly via soundfile (no extra processes)
    - pcm: raw little-endian float32 bytes
    - mp3 / aac / opus: written as wav then transcoded via ffmpeg subprocess
    """
    if fmt == "pcm":
        return samples.astype(np.float32).tobytes()

    if fmt not in _FFMPEG_OUTPUT_ARGS:
        # wav / flac — written directly by soundfile
        buf = io.BytesIO()
        sf.write(buf, samples, sample_rate, format=fmt.upper())
        return buf.getvalue()

    # mp3 / aac / opus — encode as wav first, pipe through ffmpeg
    wav_buf = io.BytesIO()
    sf.write(wav_buf, samples, sample_rate, format="WAV")
    wav_bytes = wav_buf.getvalue()

    cmd = [
        "ffmpeg", "-y",
        "-f", "wav", "-i", "pipe:0",
        *_FFMPEG_OUTPUT_ARGS[fmt],
        "-vn", "pipe:1",
    ]
    try:
        result = subprocess.run(
            cmd,
            input=wav_bytes,
            capture_output=True,
            check=True,
            timeout=60,
        )
        return result.stdout
    except subprocess.CalledProcessError as exc:
        logger.error("ffmpeg conversion to %s failed: %s", fmt, exc.stderr.decode(errors="replace"))
        raise RuntimeError(f"Audio format conversion to {fmt} failed.") from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffmpeg is required for mp3/aac/opus output but was not found."
        ) from exc


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SpeechRequest(BaseModel):
    model: str = Field(
        default="tts-1",
        description="Model identifier. Accepted values: 'tts-1', 'tts-1-hd', 'kokoro'. "
                    "All values use the Kokoro-82M model.",
    )
    input: str = Field(
        ...,
        max_length=4096,
        description="The text to synthesize. Maximum 4096 characters.",
    )
    voice: Optional[str] = Field(
        default=None,
        description=(
            "Voice to use. Accepts OpenAI voice names (alloy, echo, fable, onyx, nova, shimmer) "
            "or native Kokoro voice IDs (af_heart, bm_george, etc.). "
            "If omitted, the server default (KOKORO_VOICE env var) is used. "
            "See GET /v1/voices for all available voices."
        ),
    )
    response_format: str = Field(
        default="mp3",
        description="Output audio format: mp3, opus, aac, flac, wav, pcm",
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="Speech speed multiplier. Range: 0.25 (slowest) to 4.0 (fastest).",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health", include_in_schema=False)
async def health():
    """Container liveness probe — used by run.sh to detect startup completion."""
    return {"status": "ok", "engine": "kokoro"}


@app.get("/v1/models")
async def list_models(_auth: None = Depends(_verify_api_key)):
    """
    List the active model in OpenAI-compatible format.
    Returns 'tts-1' and 'tts-1-hd' to satisfy clients that query models before sending requests.
    """
    return {
        "object": "list",
        "data": [
            {"id": "tts-1",    "object": "model", "created": 0, "owned_by": "kokoro"},
            {"id": "tts-1-hd", "object": "model", "created": 0, "owned_by": "kokoro"},
            {"id": "kokoro",   "object": "model", "created": 0, "owned_by": "kokoro"},
        ],
    }


@app.get("/v1/voices")
async def list_voices(_auth: None = Depends(_verify_api_key)):
    """List all available Kokoro voice IDs with descriptions."""
    return {
        "voices": [
            {"id": vid, "description": desc}
            for vid, desc in KOKORO_VOICES.items()
        ],
        "openai_aliases": _OPENAI_VOICE_MAP,
    }


@app.post("/v1/audio/speech")
async def create_speech(
    req: SpeechRequest,
    _auth: None = Depends(_verify_api_key),
):
    """
    Synthesize speech from text.

    Drop-in replacement for OpenAI's POST /v1/audio/speech endpoint.
    Accepts the same JSON body and returns binary audio in the requested format.

    Supported output formats: mp3, opus, aac, flac, wav, pcm
    """
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Kokoro engine is not loaded yet. Please retry.")

    # Validate response_format
    if req.response_format not in _FORMAT_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid response_format '{req.response_format}'. "
                   f"Must be one of: {', '.join(sorted(_FORMAT_MIME))}",
        )

    if not req.input.strip():
        raise HTTPException(status_code=400, detail="'input' must not be empty.")

    # Resolve voice: per-request value > KOKORO_VOICE env var > built-in default
    env_voice = os.environ.get("KOKORO_VOICE", "af_heart").strip()
    voice_id = _resolve_voice(req.voice) if req.voice else _resolve_voice(env_voice)

    # Per-request speed overrides env default, env default overrides built-in default
    env_speed = float(os.environ.get("KOKORO_SPEED", "1.0"))
    speed = req.speed if req.speed != 1.0 else env_speed

    logger.info(
        "Synthesizing %d chars | voice=%s speed=%.2f format=%s",
        len(req.input), voice_id, speed, req.response_format,
    )

    try:
        # Collect all audio chunks from the generator
        audio_chunks = []
        for _gs, _ps, audio in _pipeline(req.input, voice=voice_id, speed=speed):
            if audio is not None and len(audio) > 0:
                audio_chunks.append(audio)

        if not audio_chunks:
            raise ValueError("Kokoro pipeline produced no audio output.")

        combined = np.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]
        audio_bytes = _audio_to_bytes(combined, sample_rate=24000, fmt=req.response_format)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Speech synthesis failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {exc}") from exc

    return Response(
        content=audio_bytes,
        media_type=_FORMAT_MIME[req.response_format],
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("KOKORO_PORT", "8880"))
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        log_level=_log_level_str.lower(),
        workers=1,  # single worker — pipeline is loaded into process memory
    )