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

import asyncio
import io
import logging
import os
import struct
import subprocess
import threading
import time
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import Response, StreamingResponse
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
#
# Two KPipeline instances are kept: one for American English ('a') and one for
# British English ('b').  The correct pipeline is selected automatically from
# the first character of the resolved Kokoro voice ID (af_* / am_* → 'a',
# bf_* / bm_* → 'b'), so a single server instance correctly handles both
# accents without requiring a KOKORO_LANG_CODE restart.
#
# If KOKORO_LANG_CODE is set in the environment, only that one pipeline is
# loaded (useful on memory-constrained hosts where only one accent is needed).
# ---------------------------------------------------------------------------

_pipelines: dict = {}   # lang_code ('a' | 'b') → KPipeline instance

# Serialise all inference calls (batch and streaming) so the KPipeline is
# never invoked concurrently from multiple async tasks / threads.
_inference_lock = threading.Lock()


def _load_model() -> None:
    """Import and initialise Kokoro KPipeline instance(s) from environment config."""
    global _pipelines

    from kokoro import KPipeline  # deferred — keeps import fast

    local_files_only = bool(os.environ.get("KOKORO_LOCAL_ONLY", "").strip())

    if local_files_only:
        # HF_HUB_OFFLINE prevents huggingface_hub from making any network requests.
        # HUGGINGFACE_HUB_OFFLINE is the older name kept for compatibility.
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HUGGINGFACE_HUB_OFFLINE"] = "1"

    # Determine which lang_code(s) to load.
    # KOKORO_LANG_CODE can restrict to a single pipeline to save memory.
    env_lang = os.environ.get("KOKORO_LANG_CODE", "").strip()
    codes_to_load = [env_lang] if env_lang else ["a", "b"]

    for code in codes_to_load:
        logger.info(
            "Loading Kokoro TTS pipeline | lang_code=%s local_only=%s",
            code, local_files_only,
        )
        t0 = time.monotonic()
        _pipelines[code] = KPipeline(lang_code=code)
        logger.info("Pipeline lang_code='%s' ready in %.1fs", code, time.monotonic() - t0)


def _get_pipeline(voice_id: str):
    """
    Return the KPipeline instance whose lang_code matches the voice ID prefix.
    Kokoro voice IDs follow the convention <lang><gender>_<name>, where the
    first character is the language code: 'a' for American English, 'b' for
    British English.  If no matching pipeline was loaded (e.g. KOKORO_LANG_CODE
    restricted loading to one accent), the sole loaded pipeline is returned with
    a warning.
    """
    lang_code = voice_id[0].lower() if voice_id else "a"
    if lang_code in _pipelines:
        return _pipelines[lang_code]
    # Fallback: use whichever pipeline was loaded
    logger.warning(
        "No pipeline for lang_code='%s' (voice '%s'); using available pipeline. "
        "Set KOKORO_LANG_CODE='' to load both 'a' and 'b' pipelines.",
        lang_code, voice_id,
    )
    return next(iter(_pipelines.values()))


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


def _wav_streaming_header(sample_rate: int, channels: int = 1) -> bytes:
    """
    Build a WAV/RIFF header for streaming use.

    The RIFF chunk size and data sub-chunk size are both set to 0xFFFFFFFF
    (the maximum uint32 value), which signals to decoders that the length is
    unknown / continuous.  The actual payload that follows must be signed
    16-bit little-endian PCM samples (PCM_S16LE).

    Most audio players (ffmpeg, VLC, browser MediaSource, etc.) accept this
    convention for live/streaming WAV.
    """
    bits_per_sample = 16
    byte_rate       = sample_rate * channels * bits_per_sample // 8
    block_align     = channels * bits_per_sample // 8
    _MAX            = 0xFFFFFFFF  # unknown / streaming length

    return struct.pack(
        "<4sI4s"        # RIFF descriptor
        "4sIHHIIHH"     # fmt  sub-chunk (16 bytes)
        "4sI",          # data sub-chunk header
        b"RIFF", _MAX, b"WAVE",
        b"fmt ", 16,
        1,              # PCM audio format
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data", _MAX,
    )


# ---------------------------------------------------------------------------
# SSE-style streaming helper for TTS
# ---------------------------------------------------------------------------


async def _stream_audio(
    text: str,
    voice_id: str,
    speed: float,
    fmt: str,
    volume: float = 1.0,
):
    """
    Async generator that yields encoded audio bytes one KPipeline chunk at a
    time, enabling clients to begin playback before synthesis of the full text
    has completed.

    Synthesis runs in a thread-pool worker via run_in_executor so the uvicorn
    event loop stays responsive during the CPU-bound model inference.
    _inference_lock ensures only one synthesis (batch or streaming) runs at a
    time, matching the single-worker server model.

    Format notes
    ------------
    pcm   — raw little-endian float32 samples; no container overhead.
    wav   — a streaming WAV header (RIFF sizes = 0xFFFFFFFF) is emitted first,
            followed by signed 16-bit little-endian PCM sample data.
    mp3   — each chunk is encoded independently via ffmpeg and yielded; mp3
            frames are self-synchronising so the concatenated stream is valid.
    aac   — each chunk encoded as ADTS frames via ffmpeg; ADTS is also
            self-synchronising and concatenates cleanly.
    flac / opus — each chunk yields a complete encoded file; these container
            formats do not concatenate cleanly but are included for completeness.
    """
    pipeline = _get_pipeline(voice_id)
    loop = asyncio.get_running_loop()
    chunk_queue: asyncio.Queue = asyncio.Queue()

    def _run() -> None:
        with _inference_lock:
            try:
                for _gs, _ps, audio in pipeline(text, voice=voice_id, speed=speed):
                    if audio is not None and len(audio) > 0:
                        loop.call_soon_threadsafe(chunk_queue.put_nowait, audio)
            except Exception as exc:  # noqa: BLE001
                loop.call_soon_threadsafe(chunk_queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(chunk_queue.put_nowait, None)  # sentinel

    loop.run_in_executor(None, _run)

    # Emit WAV streaming header before the first audio chunk
    if fmt == "wav":
        yield _wav_streaming_header(sample_rate=24000)

    while True:
        item = await chunk_queue.get()
        if item is None:
            break
        if isinstance(item, Exception):
            logger.error("Streaming synthesis error: %s", item)
            return

        # Apply volume multiplier before encoding
        if volume != 1.0:
            item = (item * volume).clip(-1.0, 1.0)

        if fmt == "pcm":
            yield item.astype(np.float32).tobytes()
        elif fmt == "wav":
            # Convert float32 [-1, 1] → signed int16, emit raw PCM samples
            s16 = (item * 32767.0).clip(-32768, 32767).astype(np.int16)
            yield s16.tobytes()
        else:
            # mp3 / aac / opus / flac — encode via ffmpeg and yield
            try:
                yield _audio_to_bytes(item, 24000, fmt)
            except Exception as exc:
                logger.error("Streaming chunk encoding to %s failed: %s", fmt, exc)
                return


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
    stream: bool = Field(
        default=False,
        description=(
            "Stream audio chunks as they are synthesized. "
            "When true, the response body is a continuous audio stream delivered "
            "via chunked transfer encoding — playback can begin before synthesis "
            "of the full text completes, reducing time-to-first-audio. "
            "pcm and wav are the most efficient streaming formats; mp3 and aac "
            "also stream cleanly. response_format is honoured for all formats."
        ),
    )
    volume_multiplier: float = Field(
        default=1.0,
        ge=0.1,
        le=2.0,
        description=(
            "Output volume multiplier applied to the synthesized audio before encoding. "
            "Range: 0.1 (quieter) to 2.0 (louder). Default: 1.0 (no change). "
            "Values above 1.0 amplify the signal; values below 1.0 attenuate it. "
            "Samples are clipped to [-1, 1] after scaling to prevent distortion."
        ),
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

    When stream=true the response uses chunked transfer encoding and audio
    playback can begin before the full text has been synthesized.  pcm and wav
    are the most efficient streaming formats; mp3 and aac also stream cleanly
    because their container frames are self-synchronising.
    """
    if not _pipelines:
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

    volume = req.volume_multiplier

    logger.info(
        "Synthesizing %d chars | voice=%s speed=%.2f format=%s stream=%s volume=%.2f",
        len(req.input), voice_id, speed, req.response_format, req.stream, volume,
    )

    # ------------------------------------------------------------------
    # Streaming path — synthesis runs in a thread; audio chunks are
    # yielded to the client as soon as each sentence is ready.
    # ------------------------------------------------------------------
    if req.stream:
        return StreamingResponse(
            _stream_audio(req.input, voice_id, speed, req.response_format, volume),
            media_type=_FORMAT_MIME[req.response_format],
            headers={
                "X-Accel-Buffering": "no",   # disable nginx proxy buffering
                "Cache-Control": "no-cache",
            },
        )

    # ------------------------------------------------------------------
    # Batch path — inference runs in a thread-pool worker so the event
    # loop remains free to handle health checks and other requests while
    # the CPU-bound model runs.
    # ------------------------------------------------------------------
    def _run_batch() -> bytes:
        _pipeline = _get_pipeline(voice_id)
        with _inference_lock:
            audio_chunks = []
            for _gs, _ps, audio in _pipeline(req.input, voice=voice_id, speed=speed):
                if audio is not None and len(audio) > 0:
                    audio_chunks.append(audio)
        if not audio_chunks:
            raise ValueError("Kokoro pipeline produced no audio output.")
        combined = np.concatenate(audio_chunks) if len(audio_chunks) > 1 else audio_chunks[0]
        if volume != 1.0:
            combined = (combined * volume).clip(-1.0, 1.0)
        return _audio_to_bytes(combined, sample_rate=24000, fmt=req.response_format)

    try:
        audio_bytes = await asyncio.get_running_loop().run_in_executor(None, _run_batch)
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
        workers=1,  # single worker — pipelines are loaded into process memory
    )