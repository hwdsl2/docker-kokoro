[English](README.md) | [简体中文](README-zh.md) | [繁體中文](README-zh-Hant.md) | [Русский](README-ru.md)

# Kokoro TTS on Docker

[![Build Status](https://github.com/hwdsl2/docker-tts/actions/workflows/main.yml/badge.svg)](https://github.com/hwdsl2/docker-tts/actions/workflows/main.yml) &nbsp;[![License: MIT](docs/images/license.svg)](https://opensource.org/licenses/MIT)

A Docker image to run a [Kokoro](https://github.com/hexgrad/kokoro) text-to-speech server. Provides an OpenAI-compatible audio speech API. Based on Debian (python:3.12-slim). Designed to be simple, private, and self-hosted.

- OpenAI-compatible `POST /v1/audio/speech` endpoint — any app using the OpenAI TTS API switches with a one-line change
- 20+ high-quality voices: American and British English, female and male
- Accepts both OpenAI voice names (`alloy`, `nova`, `echo`, ...) and native Kokoro voice IDs (`af_heart`, `bm_george`, ...)
- Audio stays on your server — no data sent to third parties
- All major output formats supported: `mp3`, `wav`, `flac`, `opus`, `aac`, `pcm`
- Offline/air-gapped mode — run without internet access using pre-cached model (`TTS_LOCAL_ONLY`)
- Automatically built and published via [GitHub Actions](https://github.com/hwdsl2/docker-tts/actions/workflows/main.yml)
- Persistent model cache via a Docker volume
- Multi-arch: `linux/amd64`, `linux/arm64`

**Also available:** Docker images for [Whisper](https://github.com/hwdsl2/docker-whisper), [LiteLLM](https://github.com/hwdsl2/docker-litellm), [WireGuard](https://github.com/hwdsl2/docker-wireguard), [OpenVPN](https://github.com/hwdsl2/docker-openvpn), [IPsec VPN](https://github.com/hwdsl2/docker-ipsec-vpn-server) and [Headscale](https://github.com/hwdsl2/docker-headscale).

## Quick start

Use this command to set up a Kokoro TTS server:

```bash
docker run \
    --name tts \
    --restart=always \
    -v tts-data:/var/lib/tts \
    -p 8880:8880 \
    -d hwdsl2/kokoro-tts
```

**Note:** For internet-facing deployments, using a [reverse proxy](#using-a-reverse-proxy) to add HTTPS is **strongly recommended**. In that case, also replace `-p 8880:8880` with `-p 127.0.0.1:8880:8880` in the `docker run` command above, to prevent direct access to the unencrypted port.

The Kokoro model (~320 MB) is downloaded and cached on first start. Check the logs to confirm the server is ready:

```bash
docker logs tts
```

Once you see "Kokoro TTS server is ready", synthesize your first audio file:

```bash
curl http://your_server_ip:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"Hello, world!","voice":"af_heart"}' \
    --output speech.mp3
```

## Requirements

- A Linux server (local or cloud) with Docker installed
- Supported architectures: `amd64` (x86_64), `arm64` (e.g. Raspberry Pi 4/5, AWS Graviton)
- Minimum RAM: ~1 GB free (model is ~320 MB; PyTorch runtime uses additional memory)
- Internet access for the initial model download (the model is cached locally afterwards). Not required if using `TTS_LOCAL_ONLY=true` with a pre-cached model.

For internet-facing deployments, see [Using a reverse proxy](#using-a-reverse-proxy) to add HTTPS.

## Download

Get the trusted build from the [Docker Hub registry](https://hub.docker.com/r/hwdsl2/kokoro-tts/):

```bash
docker pull hwdsl2/kokoro-tts
```

Alternatively, you may download from [Quay.io](https://quay.io/repository/hwdsl2/kokoro-tts):

```bash
docker pull quay.io/hwdsl2/kokoro-tts
docker image tag quay.io/hwdsl2/kokoro-tts hwdsl2/kokoro-tts
```

Supported platforms: `linux/amd64` and `linux/arm64`.

## Environment variables

All variables are optional. If not set, secure defaults are used automatically.

This Docker image uses the following variables, that can be declared in an `env` file (see [example](tts.env.example)):

| Variable | Description | Default |
|---|---|---|
| `TTS_VOICE` | Default voice for synthesis. See [voices](#available-voices) for all options. Accepts Kokoro voice IDs (`af_heart`) or OpenAI aliases (`alloy`). | `af_heart` |
| `TTS_SPEED` | Default speech speed. Range: `0.25` (slowest) to `4.0` (fastest). | `1.0` |
| `TTS_PORT` | HTTP port for the API (1–65535). | `8880` |
| `TTS_LANG_CODE` | Language/accent for the TTS pipeline. `a` for American English, `b` for British English. | `a` |
| `TTS_API_KEY` | Optional Bearer token. If set, all API requests must include `Authorization: Bearer <key>`. | *(not set)* |
| `TTS_LOG_LEVEL` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. | `INFO` |
| `TTS_LOCAL_ONLY` | When set to any non-empty value (e.g. `true`), disables all HuggingFace model downloads. For offline or air-gapped deployments with pre-cached model. | *(not set)* |

**Note:** In your `env` file, you may enclose values in single quotes, e.g. `VAR='value'`. Do not add spaces around `=`. If you change `TTS_PORT`, update the `-p` flag in the `docker run` command accordingly.

Example using an `env` file:

```bash
cp tts.env.example tts.env
# Edit tts.env with your settings, then:
docker run \
    --name tts \
    --restart=always \
    -v tts-data:/var/lib/tts \
    -v ./tts.env:/tts.env:ro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-tts
```

The env file is bind-mounted into the container, so changes are picked up on every restart without recreating the container.

Alternatively, pass it with `--env-file`:

```bash
docker run \
    --name tts \
    --restart=always \
    -v tts-data:/var/lib/tts \
    -p 8880:8880 \
    --env-file=tts.env \
    -d hwdsl2/kokoro-tts
```

## Using docker-compose

```bash
cp tts.env.example tts.env
# Edit tts.env as needed, then:
docker compose up -d
docker logs tts
```

Example `docker-compose.yml` (already included):

```yaml
services:
  tts:
    image: hwdsl2/kokoro-tts
    container_name: tts
    restart: always
    ports:
      - "8880:8880/tcp"  # For a host-based reverse proxy, change to "127.0.0.1:8880:8880/tcp"
    volumes:
      - tts-data:/var/lib/tts
      - ./tts.env:/tts.env:ro

volumes:
  tts-data:
```

**Note:** For internet-facing deployments, using a [reverse proxy](#using-a-reverse-proxy) to add HTTPS is **strongly recommended**. In that case, also change `"8880:8880/tcp"` to `"127.0.0.1:8880:8880/tcp"` in `docker-compose.yml`, to prevent direct access to the unencrypted port.

## API reference

The API is fully compatible with [OpenAI's text-to-speech endpoint](https://platform.openai.com/docs/api-reference/audio/createSpeech). Any application already calling `https://api.openai.com/v1/audio/speech` can switch to self-hosted by setting:

```
OPENAI_BASE_URL=http://your_server_ip:8880
```

### Synthesize speech

```
POST /v1/audio/speech
Content-Type: application/json
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `model` | string | ✅ | Pass `tts-1`, `tts-1-hd`, or `kokoro` (all use Kokoro-82M). |
| `input` | string | ✅ | The text to synthesize. Maximum 4096 characters. |
| `voice` | string | ✅ | Voice to use. See [available voices](#available-voices). Accepts Kokoro IDs or OpenAI aliases. |
| `response_format` | string | — | Output format. Default: `mp3`. Options: `mp3`, `opus`, `aac`, `flac`, `wav`, `pcm`. |
| `speed` | float | — | Speech speed. Default: `1.0`. Range: `0.25`–`4.0`. |

**Example:**

```bash
curl http://your_server_ip:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"The quick brown fox jumps over the lazy dog.","voice":"af_heart"}' \
    --output speech.mp3
```

With a different voice and format:

```bash
curl http://your_server_ip:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"Hello from London.","voice":"bm_george","response_format":"wav","speed":0.9}' \
    --output speech.wav
```

With API key authentication:

```bash
curl http://your_server_ip:8880/v1/audio/speech \
    -H "Authorization: Bearer your_api_key" \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"Hello world","voice":"nova"}' \
    --output speech.mp3
```

**Response:** Binary audio data with the appropriate `Content-Type` header.

### List voices

```
GET /v1/voices
```

Returns all available Kokoro voice IDs and their OpenAI alias mappings.

```bash
curl http://your_server_ip:8880/v1/voices
```

### List models

```
GET /v1/models
```

Returns the active models in OpenAI-compatible format.

```bash
curl http://your_server_ip:8880/v1/models
```

### Interactive API docs

An interactive Swagger UI is available at:

```
http://your_server_ip:8880/docs
```

## Available voices

Use `tts_manage --listvoices` to see the full list at any time:

```bash
docker exec tts tts_manage --listvoices
```

| Voice ID | Accent | Gender | Style |
|---|---|---|---|
| `af_heart` | American | Female | Warm, natural — **default** |
| `af_bella` | American | Female | Expressive |
| `af_nova` | American | Female | Clear |
| `af_sky` | American | Female | Neutral, versatile |
| `af_sarah` | American | Female | Conversational |
| `af_nicole` | American | Female | Friendly |
| `af_alloy` | American | Female | Balanced |
| `af_jessica` | American | Female | Energetic |
| `af_river` | American | Female | Calm |
| `am_adam` | American | Male | Deep |
| `am_michael` | American | Male | Clear |
| `am_echo` | American | Male | Neutral |
| `am_eric` | American | Male | Authoritative |
| `am_liam` | American | Male | Conversational |
| `am_onyx` | American | Male | Rich |
| `am_puck` | American | Male | Expressive |
| `bf_emma` | British | Female | Clear, professional |
| `bf_isabella` | British | Female | Warm |
| `bf_alice` | British | Female | Crisp |
| `bf_lily` | British | Female | Soft |
| `bm_george` | British | Male | Authoritative |
| `bm_lewis` | British | Male | Smooth |
| `bm_daniel` | British | Male | Calm |
| `bm_fable` | British | Male | Expressive |

**OpenAI voice aliases** (accepted in the `voice` field):

| OpenAI alias | Maps to |
|---|---|
| `alloy` | `af_alloy` |
| `echo` | `am_echo` |
| `fable` | `bm_fable` |
| `onyx` | `am_onyx` |
| `nova` | `af_nova` |
| `shimmer` | `af_bella` |
| `ash` | `am_michael` |
| `coral` | `af_heart` |
| `sage` | `af_sky` |
| `verse` | `bm_george` |

> **Tip:** British voices (`bf_*`, `bm_*`) produce the best results when `TTS_LANG_CODE=b` is set.

All voices use a single shared model file (~320 MB). No re-download is needed when switching voices.

## Persistent data

All server data is stored in the Docker volume (`/var/lib/tts` inside the container):

```
/var/lib/tts/
├── models--hexgrad--Kokoro-82M/   # Cached Kokoro model files (downloaded from HuggingFace)
├── .port                          # Active port (used by tts_manage)
├── .voice                         # Active default voice (used by tts_manage)
└── .server_addr                   # Cached server IP (used by tts_manage)
```

Back up the Docker volume to preserve the downloaded model. The model is ~320 MB and only needs to be downloaded once.

## Managing the server

Use `tts_manage` inside the running container to inspect and manage the server.

**Show server info:**

```bash
docker exec tts tts_manage --showinfo
```

**List available voices:**

```bash
docker exec tts tts_manage --listvoices
```

## Changing the voice

To change the default voice, update `TTS_VOICE` in your `tts.env` file and restart the container. No model re-download is required — all voices use the same Kokoro-82M model.

```bash
# Edit tts.env: set TTS_VOICE=bm_george
docker restart tts
```

> **Note:** Individual API requests can always specify a different voice using the `voice` field, regardless of the container default.

## Using a reverse proxy

For internet-facing deployments, place a reverse proxy in front of the TTS server to handle HTTPS termination. The server works without HTTPS on a local or trusted network, but HTTPS is recommended when the API endpoint is exposed to the internet.

Use one of the following addresses to reach the TTS container from your reverse proxy:

- **`tts:8880`** — if your reverse proxy runs as a container in the **same Docker network** as the TTS server (e.g. defined in the same `docker-compose.yml`).
- **`127.0.0.1:8880`** — if your reverse proxy runs **on the host** and port `8880` is published (the default `docker-compose.yml` publishes it).

**Example with [Caddy](https://caddyserver.com/docs/) ([Docker image](https://hub.docker.com/_/caddy))** (automatic TLS via Let's Encrypt, reverse proxy in the same Docker network):

`Caddyfile`:
```
tts.example.com {
  reverse_proxy tts:8880
}
```

**Example with nginx** (reverse proxy on the host):

```nginx
server {
    listen 443 ssl;
    server_name tts.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass         http://127.0.0.1:8880;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

Set `TTS_API_KEY` in your `env` file when the server is accessible from the public internet.

## Update Docker image

To update the Docker image and container, first [download](#download) the latest version:

```bash
docker pull hwdsl2/kokoro-tts
```

If the Docker image is already up to date, you should see:

```
Status: Image is up to date for hwdsl2/kokoro-tts:latest
```

Otherwise, it will download the latest version. Remove and re-create the container:

```bash
docker rm -f tts
# Then re-run the docker run command from Quick start with the same volume and port.
```

Your downloaded model is preserved in the `tts-data` volume.

## Technical details

- Base image: `python:3.12-slim` (Debian)
- Runtime: Python 3 (virtual environment at `/opt/venv`)
- TTS engine: [Kokoro](https://github.com/hexgrad/kokoro) (Kokoro-82M, Apache 2.0) with PyTorch CPU backend
- API framework: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- Audio encoding: [soundfile](https://github.com/bastibe/python-soundfile) (wav/flac), [ffmpeg](https://ffmpeg.org/) (mp3/aac/opus)
- Data directory: `/var/lib/tts` (Docker volume)
- Model storage: HuggingFace Hub format inside the volume — downloaded once, reused on restarts
- Sample rate: 24 kHz (native Kokoro output)

## License

**Note:** The software components inside the pre-built image (such as Kokoro and its dependencies) are under the respective licenses chosen by their respective copyright holders. As for any pre-built image usage, it is the image user's responsibility to ensure that any use of this image complies with any relevant licenses for all software contained within.

Copyright (C) 2026 Lin Song   
This work is licensed under the [MIT License](https://opensource.org/licenses/MIT).

**Kokoro TTS** is Copyright (C) hexgrad, and is distributed under the [Apache License 2.0](https://github.com/hexgrad/kokoro/blob/main/LICENSE).

This project is an independent Docker setup for Kokoro and is not affiliated with, endorsed by, or sponsored by hexgrad or OpenAI.