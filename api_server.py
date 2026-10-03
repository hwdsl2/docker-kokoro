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
import base64
import io
import json
import logging
import os
import struct
import subprocess
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Literal, Optional, Union

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    "af_heart":      "American female — warm, natural (recommended default)",
    "af_aoede":      "American female",
    "af_bella":      "American female — expressive",
    "af_jessica":    "American female — energetic",
    "af_kore":       "American female",
    "af_nicole":     "American female — friendly",
    "af_nova":       "American female — clear",
    "af_river":      "American female — calm",
    "af_sarah":      "American female — conversational",
    "af_sky":        "American female — neutral, versatile",
    "af_alloy":      "American female — balanced",
    # American English male
    "am_adam":       "American male — deep",
    "am_michael":    "American male — clear",
    "am_echo":       "American male — neutral",
    "am_eric":       "American male — authoritative",
    "am_fenrir":     "American male — distinctive",
    "am_liam":       "American male — conversational",
    "am_onyx":       "American male — rich",
    "am_puck":       "American male — expressive",
    "am_santa":      "American male — warm",
    # British English female
    "bf_emma":       "British female — clear, professional",
    "bf_isabella":   "British female — warm",
    "bf_alice":      "British female — crisp",
    "bf_lily":       "British female — soft",
    # British English male
    "bm_george":     "British male — authoritative",
    "bm_lewis":      "British male — smooth",
    "bm_daniel":     "British male — calm",
    "bm_fable":      "British male — expressive",
    # Japanese female
    "jf_alpha":      "Japanese female",
    "jf_gongitsune": "Japanese female",
    "jf_nezumi":     "Japanese female",
    "jf_tebukuro":   "Japanese female",
    # Japanese male
    "jm_kumo":       "Japanese male",
    # Mandarin Chinese female
    "zf_xiaobei":    "Mandarin Chinese female",
    "zf_xiaoni":     "Mandarin Chinese female",
    "zf_xiaoxiao":   "Mandarin Chinese female",
    "zf_xiaoyi":     "Mandarin Chinese female",
    # Mandarin Chinese male
    "zm_yunjian":    "Mandarin Chinese male",
    "zm_yunxi":      "Mandarin Chinese male",
    "zm_yunxia":     "Mandarin Chinese male",
    "zm_yunyang":    "Mandarin Chinese male",
    # Spanish female
    "ef_dora":       "Spanish female",
    # Spanish male
    "em_alex":       "Spanish male",
    "em_santa":      "Spanish male",
    # French female
    "ff_siwis":      "French female",
    # Hindi female
    "hf_alpha":      "Hindi female",
    "hf_beta":       "Hindi female",
    # Hindi male
    "hm_omega":      "Hindi male",
    "hm_psi":        "Hindi male",
    # Italian female
    "if_sara":       "Italian female",
    # Italian male
    "im_nicola":     "Italian male",
    # Brazilian Portuguese female
    "pf_dora":       "Brazilian Portuguese female",
    # Brazilian Portuguese male
    "pm_alex":       "Brazilian Portuguese male",
    "pm_santa":      "Brazilian Portuguese male",
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
    "ballad":  "bm_lewis",
    "marin":   "af_nicole",
    "cedar":   "am_adam",
}


class VoiceReference(BaseModel):
    id: str = Field(..., description="Local Kokoro voice ID or supported OpenAI voice alias.")


def _voice_id_from_request(voice: Union[str, VoiceReference, dict[str, Any]]) -> str:
    if isinstance(voice, str):
        return voice
    if isinstance(voice, VoiceReference):
        return voice.id
    if isinstance(voice, dict) and "id" in voice:
        return str(voice["id"])
    raise HTTPException(
        status_code=400,
        detail="Invalid voice value. Provide a voice string or an object with an 'id' field.",
    )


def _resolve_voice(voice: Union[str, VoiceReference, dict[str, Any]]) -> str:
    """
    Accept OpenAI voice alias or a native Kokoro voice ID.
    Returns the resolved Kokoro voice ID.
    """
    raw_voice = _voice_id_from_request(voice)
    v = raw_voice.strip().lower()
    if not v:
        raise HTTPException(
            status_code=400,
            detail="Voice must not be empty. Use GET /v1/voices to list supported voices.",
        )
    # Direct Kokoro name (e.g. "af_heart")
    if v in KOKORO_VOICES:
        return v
    # OpenAI alias (e.g. "alloy")
    if v in _OPENAI_VOICE_MAP:
        return _OPENAI_VOICE_MAP[v]
    raise HTTPException(
        status_code=400,
        detail=f"Unknown voice '{raw_voice}'. Use GET /v1/voices to list supported voices.",
    )


# ---------------------------------------------------------------------------
# Model — loaded once at startup via the FastAPI lifespan hook
#
# One KPipeline instance is kept per language code.  At startup, the pipeline
# for the default voice's language is loaded (derived from the first character
# of KOKORO_VOICE, e.g. "af_heart" → 'a', "jf_alpha" → 'j').  If
# KOKORO_LANG_CODE is set explicitly, that pipeline is loaded instead.
#
# When a request uses a voice from a different language, the required pipeline
# is created on demand by _get_pipeline() and cached for subsequent requests.
# ---------------------------------------------------------------------------

_pipelines: dict = {}   # lang_code → KPipeline instance

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

    # Determine which lang_code to load at startup.
    # If KOKORO_LANG_CODE is set explicitly, use it.
    # Otherwise derive the lang code from the first character of KOKORO_VOICE
    # (e.g. "af_heart" → "a", "jf_alpha" → "j"). Additional pipelines for
    # other languages are created lazily on first request via _get_pipeline().
    env_lang = os.environ.get("KOKORO_LANG_CODE", "").strip()
    if env_lang:
        codes_to_load = [env_lang]
    else:
        default_voice = os.environ.get("KOKORO_VOICE", "af_heart").strip()
        codes_to_load = [default_voice[0].lower()] if default_voice else ["a"]

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
    first character is the language code (a=American English, b=British English,
    e=Spanish, f=French, h=Hindi, i=Italian, j=Japanese, p=Brazilian Portuguese,
    z=Mandarin Chinese).
    If the required pipeline has not been loaded yet, it is created on demand
    and cached for subsequent requests.
    """
    lang_code = voice_id[0].lower() if voice_id else "a"
    if lang_code not in _pipelines:
        from kokoro import KPipeline  # deferred import (already imported in _load_model)
        local_files_only = bool(os.environ.get("KOKORO_LOCAL_ONLY", "").strip())
        if local_files_only:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["HUGGINGFACE_HUB_OFFLINE"] = "1"
        logger.info(
            "Creating pipeline on demand | lang_code=%s local_only=%s",
            lang_code, local_files_only,
        )
        with _inference_lock:
            # Double-check inside the lock to avoid duplicate creation
            if lang_code not in _pipelines:
                _pipelines[lang_code] = KPipeline(lang_code=lang_code)
    return _pipelines[lang_code]


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

# CORS
cors_origins = os.getenv("CORS_ALLOW_ORIGINS")

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins.split(","),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
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


def _audio_to_pcm16le(samples: np.ndarray) -> bytes:
    """
    Convert float audio samples to raw signed 16-bit little-endian PCM.

    Kokoro returns float samples in approximately [-1, 1]. OpenAI-compatible
    response_format="pcm" is raw PCM_S16LE at 24 kHz mono, without a header.
    """
    pcm = np.asarray(samples, dtype=np.float32)
    pcm = (pcm * 32767.0).clip(-32768, 32767).astype("<i2", copy=False)
    return pcm.tobytes()


def _audio_to_bytes(samples: np.ndarray, sample_rate: int, fmt: str) -> bytes:
    """
    Convert a float32 numpy audio array to the requested output format bytes.

    - wav / flac: written directly via soundfile (no extra processes)
    - pcm: raw signed 16-bit little-endian samples, no header
    - mp3 / aac / opus: written as wav then transcoded via ffmpeg subprocess
    """
    if fmt == "pcm":
        return _audio_to_pcm16le(samples)

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


def _sse_audio_delta(audio_bytes: bytes) -> str:
    """Build one OpenAI-style SSE audio delta frame."""
    payload = json.dumps({
        "type": "speech.audio.delta",
        "audio": base64.b64encode(audio_bytes).decode("ascii"),
    })
    return f"data: {payload}\n\n"


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
    pcm   — raw signed 16-bit little-endian samples; no container overhead.
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

        # Ensure chunk is a numpy array (Kokoro pipeline may yield torch Tensors,
        # including CUDA tensors when running on GPU).
        if not isinstance(item, np.ndarray):
            if hasattr(item, "detach"):  # torch.Tensor (CPU or CUDA)
                item = item.detach().cpu().numpy()
            else:
                item = np.asarray(item)

        # Apply volume multiplier before encoding
        if volume != 1.0:
            item = (item * volume).clip(-1.0, 1.0)

        if fmt == "pcm":
            yield _audio_to_pcm16le(item)
        elif fmt == "wav":
            yield _audio_to_pcm16le(item)
        else:
            # mp3 / aac / opus / flac — encode via ffmpeg and yield
            try:
                yield _audio_to_bytes(item, 24000, fmt)
            except Exception as exc:
                logger.error("Streaming chunk encoding to %s failed: %s", fmt, exc)
                return


async def _stream_audio_sse(
    text: str,
    voice_id: str,
    speed: float,
    fmt: str,
    volume: float = 1.0,
):
    """
    Async generator that yields Server-Sent Events (SSE) using the OpenAI
    streaming speech protocol.

    Event types emitted:
      - speech.audio.delta  — base64-encoded audio chunk
      - speech.audio.done   — synthesis complete

    For response_format="wav", the first delta is a 44-byte streaming WAV
    header, followed by raw signed 16-bit little-endian PCM audio deltas.

    The stream is terminated with a `data: [DONE]` sentinel, matching the
    OpenAI SDK expectations.
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

    if fmt == "wav":
        yield _sse_audio_delta(_wav_streaming_header(sample_rate=24000))

    while True:
        item = await chunk_queue.get()
        if item is None:
            break
        if isinstance(item, Exception):
            logger.error("Streaming synthesis error: %s", item)
            err_payload = json.dumps({
                "error": {
                    "type": "synthesis_error",
                    "message": str(item),
                }
            })
            yield f"data: {err_payload}\n\n"
            return

        # Ensure chunk is a numpy array
        if not isinstance(item, np.ndarray):
            if hasattr(item, "detach"):
                item = item.detach().cpu().numpy()
            else:
                item = np.asarray(item)

        # Apply volume multiplier before encoding
        if volume != 1.0:
            item = (item * volume).clip(-1.0, 1.0)

        # Encode audio chunk to the requested format
        try:
            if fmt == "pcm" or fmt == "wav":
                audio_bytes = _audio_to_pcm16le(item)
            else:
                audio_bytes = _audio_to_bytes(item, 24000, fmt)
        except Exception as exc:
            logger.error("SSE chunk encoding to %s failed: %s", fmt, exc)
            return

        yield _sse_audio_delta(audio_bytes)

    # Emit speech.audio.done event
    yield f'data: {json.dumps({"type": "speech.audio.done"})}\n\n'
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SpeechRequest(BaseModel):
    model: str = Field(
        ...,
        description="Model identifier. Accepted values: 'tts-1', 'tts-1-hd', 'kokoro'. "
                    "All values use the Kokoro-82M model.",
    )
    input: str = Field(
        ...,
        max_length=4096,
        description="The text to synthesize. Maximum 4096 characters.",
    )
    voice: Union[str, VoiceReference] = Field(
        ...,
        description=(
            "Voice to use. Accepts OpenAI voice names (alloy, ash, ballad, cedar, "
            "coral, echo, fable, marin, onyx, nova, sage, shimmer, verse), "
            "a voice object with an id field, or native Kokoro voice IDs "
            "(af_heart, bm_george, etc.). See GET /v1/voices for all available voices."
        ),
    )
    instructions: Optional[str] = Field(
        default=None,
        max_length=4096,
        description=(
            "Control the voice of your generated audio with additional instructions. "
            "This parameter is accepted for API compatibility but is not currently "
            "supported by the Kokoro engine and will be ignored."
        ),
    )
    response_format: Optional[Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]] = Field(
        default="mp3",
        description="The format to audio in. Supported formats are mp3, opus, aac, flac, wav, and pcm.",
    )
    speed: Optional[float] = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="The speed of the generated audio. Select a value from 0.25 to 4.0. 1.0 is the default.",
    )
    stream_format: Optional[Literal["sse", "audio"]] = Field(
        default=None,
        description=(
            "The format to stream the audio in. Supported formats are 'sse' and "
            "'audio'. When set to 'audio', audio bytes are streamed via chunked "
            "transfer encoding. When set to 'sse', the response is a "
            "text/event-stream with speech.audio.delta events containing "
            "base64-encoded audio chunks, followed by a speech.audio.done event. "
            "If not set, the full audio is returned as a single response."
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

    When stream_format is set to 'audio', the response uses chunked transfer
    encoding and audio playback can begin before the full text has been
    synthesized.  When stream_format is 'sse', the response is a
    text/event-stream with speech.audio.delta and speech.audio.done events
    following the OpenAI streaming speech protocol.
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

    # Resolve voice
    voice_id = _resolve_voice(req.voice)

    # Per-request speed overrides env default, env default overrides built-in default
    env_speed = float(os.environ.get("KOKORO_SPEED", "1.0"))
    speed = req.speed if req.speed != 1.0 else env_speed

    volume = req.volume_multiplier

    logger.info(
        "Synthesizing %d chars | voice=%s speed=%.2f format=%s stream_format=%s volume=%.2f",
        len(req.input), voice_id, speed, req.response_format, req.stream_format, volume,
    )

    # ------------------------------------------------------------------
    # Streaming path — synthesis runs in a thread; audio chunks are
    # yielded to the client as soon as each sentence is ready.
    # ------------------------------------------------------------------
    if req.stream_format == "sse":
        return StreamingResponse(
            _stream_audio_sse(req.input, voice_id, speed, req.response_format, volume),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )

    if req.stream_format == "audio":
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
        # np.concatenate returns a numpy array; for the single-chunk case convert
        # explicitly to handle torch Tensors (including CUDA tensors on GPU).
        if len(audio_chunks) > 1:
            combined = np.concatenate([
                c.detach().cpu().numpy() if hasattr(c, "detach") else np.asarray(c)
                for c in audio_chunks
            ])
        else:
            c = audio_chunks[0]
            combined = c.detach().cpu().numpy() if hasattr(c, "detach") else np.asarray(c)
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
