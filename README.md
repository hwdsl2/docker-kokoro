[English](README.md) | [简体中文](README-zh.md) | [繁體中文](README-zh-Hant.md) | [Русский](README-ru.md)

# Kokoro Text-to-Speech on Docker

[![Build Status](https://github.com/hwdsl2/docker-kokoro/actions/workflows/main.yml/badge.svg)](https://github.com/hwdsl2/docker-kokoro/actions/workflows/main.yml) &nbsp;[![Docker Pulls](https://raw.githubusercontent.com/hwdsl2/badges/main/img/docker-pulls-kokoro-server.svg)](https://hub.docker.com/r/hwdsl2/kokoro-server) &nbsp;[![License: MIT](docs/images/license.svg)](https://opensource.org/licenses/MIT) &nbsp;[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://vpnsetup.net/kokoro-notebook)

Part of the [Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack) — deploy a complete self-hosted AI stack with a single command.

Docker image to run a [Kokoro](https://github.com/hexgrad/kokoro) text-to-speech server. Provides an OpenAI-compatible audio speech API. Based on Debian (python:3.12-slim). Designed to be simple, private, and self-hosted.

> 📘 **New book:** [The Self-Hosted AI Builder’s Guide](https://books2read.com/aiguide?store=amazon) — learn how to deploy this service as part of a complete, secure-by-default private AI stack.

**Features:**

- OpenAI-compatible `POST /v1/audio/speech` endpoint — any app using the OpenAI TTS API switches with a one-line change
- 54 high-quality voices across 9 languages (English, Japanese, Chinese, Spanish, French, Italian, and more)
- Accepts OpenAI voice-name aliases (`alloy`, `nova`, `echo`, ...) that map to local Kokoro voices, plus native Kokoro voice IDs (`af_heart`, `bm_george`, ...)
- Audio stays on your server — no data sent to third parties
- All major output formats supported: `mp3`, `wav`, `flac`, `opus`, `aac`, `pcm`
- Streaming support — set `stream_format` to `"audio"` or `"sse"` to receive audio as each sentence is synthesized, reducing time-to-first-audio
- NVIDIA GPU (CUDA) acceleration for faster inference (`:cuda` image tag)
- Offline/air-gapped mode — run without internet access using pre-cached model (`KOKORO_LOCAL_ONLY`)
- Automatically built and published via [GitHub Actions](https://github.com/hwdsl2/docker-kokoro/actions)
- Persistent model cache via a Docker volume
- Multi-arch: `linux/amd64`, `linux/arm64`

**Also available:**

- Try it online: [Open in Colab](https://vpnsetup.net/kokoro-notebook) — no Docker or installation required
- Related AI services: [Whisper](https://github.com/hwdsl2/docker-whisper), [Embeddings](https://github.com/hwdsl2/docker-embeddings), [LiteLLM](https://github.com/hwdsl2/docker-litellm), [Ollama](https://github.com/hwdsl2/docker-ollama), [Docling](https://github.com/hwdsl2/docker-docling), [MCP Gateway](https://github.com/hwdsl2/docker-mcp-gateway)

## Community

- 📬 [Subscribe for project updates](https://selfhostedstack.beehiiv.com/subscribe?utm_campaign=ai) (1–2 emails/month) — get free AI and VPN deployment guides (PDF)
- 💬 Join the [r/selfhostedstack](https://www.reddit.com/r/selfhostedstack/) community for discussions and showcases
- ⭐ Star the repository if you find it useful — it helps others discover it

<details>
<summary>Self-hosted VPN & networking projects</summary>

- [Setup IPsec VPN](https://github.com/hwdsl2/setup-ipsec-vpn)
- [IPsec VPN on Docker](https://github.com/hwdsl2/docker-ipsec-vpn-server)
- [WireGuard](https://github.com/hwdsl2/docker-wireguard)
- [OpenVPN](https://github.com/hwdsl2/docker-openvpn)
- [Headscale](https://github.com/hwdsl2/docker-headscale)

</details>

## Quick start

Use this command to set up a Kokoro TTS server:

```bash
docker run \
    --name kokoro \
    --restart=always \
    -v kokoro-data:/var/lib/kokoro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-server
```

<details>
<summary><strong>GPU quick start (NVIDIA CUDA)</strong></summary>

If you have an NVIDIA GPU, use the `:cuda` image for hardware-accelerated inference:

```bash
docker run \
    --name kokoro \
    --restart=always \
    --gpus=all \
    -v kokoro-data:/var/lib/kokoro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-server:cuda
```

**Requirements:** NVIDIA GPU, [NVIDIA driver](https://www.nvidia.com/en-us/drivers/) 575.57.08+ (Linux) or 576.57+ (Windows), and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed on the host. The `:cuda` image is `linux/amd64` only.

</details>

**Important:** This image requires at least 1.5 GB of available RAM due to the PyTorch runtime and Kokoro model. Systems with 1 GB or less of total RAM are not supported.

**Note:** For internet-facing deployments, using a [reverse proxy](#using-a-reverse-proxy) to add HTTPS is **strongly recommended**. In that case, also replace `-p 8880:8880` with `-p 127.0.0.1:8880:8880` in the `docker run` command above, to prevent direct access to the unencrypted port.

The Kokoro model (~320 MB) is downloaded and cached on first start. Check the logs to confirm the server is ready:

```bash
docker logs kokoro
```

Once you see "Kokoro text-to-speech server is ready", synthesize your first audio file:

```bash
curl http://your_server_ip:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"Hello, world!","voice":"af_heart"}' \
    --output speech.mp3
```

## Requirements

- A Linux server (local or cloud) with Docker installed
- Supported architectures: `amd64` (x86_64), `arm64` (e.g. Raspberry Pi 4/5, AWS Graviton)
- Minimum RAM: ~1.5 GB free (model is ~320 MB; PyTorch runtime uses additional memory)
- Internet access for the initial model download (the model is cached locally afterwards). Not required if using `KOKORO_LOCAL_ONLY=true` with a pre-cached model.

**For GPU acceleration (`:cuda` image):**

- NVIDIA GPU with CUDA support (Compute Capability 6.0+)
- [NVIDIA driver](https://www.nvidia.com/en-us/drivers/) 575.57.08+ (Linux) or 576.57+ (Windows) installed on the host
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed
- The `:cuda` image supports `linux/amd64` only

For internet-facing deployments, see [Using a reverse proxy](#using-a-reverse-proxy) to add HTTPS.

## Download

Get the trusted build from the [Docker Hub registry](https://hub.docker.com/r/hwdsl2/kokoro-server/):

```bash
docker pull hwdsl2/kokoro-server
```

For NVIDIA GPU acceleration, pull the `:cuda` tag instead:

```bash
docker pull hwdsl2/kokoro-server:cuda
```

Alternatively, you may download from [Quay.io](https://quay.io/repository/hwdsl2/kokoro-server):

```bash
docker pull quay.io/hwdsl2/kokoro-server
docker image tag quay.io/hwdsl2/kokoro-server hwdsl2/kokoro-server
```

Supported platforms: `linux/amd64` and `linux/arm64`. The `:cuda` tag supports `linux/amd64` only.

## Environment variables

All variables are optional. Fresh installs with a mounted `/var/lib/kokoro` volume auto-generate a Bearer token. Existing installs without a key remain open for backward compatibility.

This Docker image uses the following variables, that can be declared in an `env` file (see [example](kokoro.env.example)):

| Variable | Description | Default |
|---|---|---|
| `KOKORO_VOICE` | Default voice for synthesis. See [voices](#available-voices) for all options. Accepts Kokoro voice IDs (`af_heart`) or OpenAI aliases (`alloy`, `ballad`, etc.). | `af_heart` |
| `KOKORO_SPEED` | Default speech speed. Range: `0.25` (slowest) to `4.0` (fastest). | `1.0` |
| `KOKORO_PORT` | HTTP port for the API (1–65535). | `8880` |
| `KOKORO_LANG_CODE` | If set, loads only that language pipeline at startup (`a`=American English, `b`=British English, `e`=Spanish, `f`=French, `h`=Hindi, `i`=Italian, `j`=Japanese, `p`=Brazilian Portuguese, `z`=Mandarin Chinese). When unset, the pipeline is auto-selected from the `KOKORO_VOICE` prefix. Additional pipelines are created on demand when a request uses a different language. | *(not set)* |
| `KOKORO_API_KEY` | Optional Bearer token. Fresh persistent installs auto-generate one. If set, all API requests must include `Authorization: Bearer <key>`. Set explicitly empty to disable authentication. | Auto-generated for fresh persistent installs |
| `KOKORO_LOG_LEVEL` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. | `INFO` |
| `KOKORO_LOCAL_ONLY` | When set to any non-empty value (e.g. `true`), disables all HuggingFace model downloads. For offline or air-gapped deployments with pre-cached model. | *(not set)* |
| `KOKORO_DISABLE_USAGE_COUNTS` | Set to `1` to disable anonymous aggregate usage counts. | *(not set)* |

**Note:** In your `env` file, you may enclose values in single quotes, e.g. `VAR='value'`. Do not add spaces around `=`. If you change `KOKORO_PORT`, update the `-p` flag in the `docker run` command accordingly.

Example using an `env` file:

```bash
cp kokoro.env.example kokoro.env
# Edit kokoro.env with your settings, then:
docker run \
    --name kokoro \
    --restart=always \
    -v kokoro-data:/var/lib/kokoro \
    -v ./kokoro.env:/kokoro.env:ro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-server
```

The env file is bind-mounted into the container, so changes are picked up on every restart without recreating the container.

<details>
<summary>Alternatively, pass it with <code>--env-file</code></summary>

```bash
docker run \
    --name kokoro \
    --restart=always \
    -v kokoro-data:/var/lib/kokoro \
    -p 8880:8880 \
    --env-file=kokoro.env \
    -d hwdsl2/kokoro-server
```

</details>

## Using docker-compose

```bash
cp kokoro.env.example kokoro.env
# Edit kokoro.env as needed, then:
docker compose up -d
docker logs kokoro
```

Example `docker-compose.yml` (already included):

```yaml
services:
  kokoro:
    image: hwdsl2/kokoro-server
    container_name: kokoro
    restart: always
    ports:
      - "8880:8880/tcp"  # For a host-based reverse proxy, change to "127.0.0.1:8880:8880/tcp"
    volumes:
      - kokoro-data:/var/lib/kokoro
      - ./kokoro.env:/kokoro.env:ro

volumes:
  kokoro-data:
    name: kokoro-data
```

**Note:** For internet-facing deployments, using a [reverse proxy](#using-a-reverse-proxy) to add HTTPS is **strongly recommended**. In that case, also change `"8880:8880/tcp"` to `"127.0.0.1:8880:8880/tcp"` in `docker-compose.yml`, to prevent direct access to the unencrypted port.

<details>
<summary><strong>Using docker-compose with GPU (NVIDIA CUDA)</strong></summary>

A separate `docker-compose.cuda.yml` is provided for GPU deployments:

```bash
cp kokoro.env.example kokoro.env
# Edit kokoro.env as needed, then:
docker compose -f docker-compose.cuda.yml up -d
docker logs kokoro
```

Example `docker-compose.cuda.yml` (already included):

```yaml
services:
  kokoro:
    image: hwdsl2/kokoro-server:cuda
    container_name: kokoro
    restart: always
    ports:
      - "8880:8880/tcp"  # For a host-based reverse proxy, change to "127.0.0.1:8880:8880/tcp"
    volumes:
      - kokoro-data:/var/lib/kokoro
      - ./kokoro.env:/kokoro.env:ro
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  kokoro-data:
    name: kokoro-data
```

</details>

## API reference

The API is compatible with [OpenAI's text-to-speech endpoint](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create). Any application already calling `https://api.openai.com/v1/audio/speech` can switch to self-hosted by setting:

OpenAI voice names are accepted as local aliases for client compatibility. These aliases map to Kokoro voices and do not reproduce OpenAI's proprietary voices. The `voice` field may be a string or an object with an `id` field; unknown voices return `400`.

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
| `voice` | string or object | ✅ | Voice to use. See [available voices](#available-voices). Accepts Kokoro IDs, OpenAI aliases that map to local Kokoro voices, or an object with an `id` field. Unknown voices return `400`. |
| `response_format` | string | — | Output format. Default: `mp3`. Options: `mp3`, `opus`, `aac`, `flac`, `wav`, `pcm`. `pcm` is raw signed 16-bit little-endian audio at 24 kHz mono, with no header. |
| `speed` | float | — | Speech speed. Default: `1.0`. Range: `0.25`–`4.0`. |
| `instructions` | string | — | Control the voice with additional instructions. Accepted for API compatibility but not currently supported by the Kokoro engine (ignored). |
| `stream_format` | string | — | The format to stream the audio in. Options: `audio`, `sse`. When set to `audio`, audio bytes are streamed via chunked transfer encoding. When set to `sse`, the response uses Server-Sent Events with `speech.audio.delta` and `speech.audio.done` events (OpenAI streaming speech protocol). For SSE WAV, the first delta is a streaming WAV header and later deltas are raw PCM_S16LE at 24 kHz mono. SSE PCM deltas are raw PCM_S16LE at 24 kHz mono with no header. If omitted, the full audio is returned as a single response. |
| `volume_multiplier` | float | — | Output volume multiplier. Default: `1.0`. Range: `0.1`–`2.0`. Values above `1.0` amplify, below `1.0` attenuate. Samples are clipped after scaling to prevent distortion. |

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

Use `kokoro_manage --listvoices` to see the full list at any time:

```bash
docker exec kokoro kokoro_manage --listvoices
```

**American English:**

| Voice ID | Gender | Style |
|---|---|---|
| `af_heart` | Female | Warm, natural — **default** |
| `af_aoede` | Female | |
| `af_bella` | Female | Expressive |
| `af_jessica` | Female | Energetic |
| `af_kore` | Female | |
| `af_nicole` | Female | Friendly |
| `af_nova` | Female | Clear |
| `af_river` | Female | Calm |
| `af_sarah` | Female | Conversational |
| `af_sky` | Female | Neutral, versatile |
| `af_alloy` | Female | Balanced |
| `am_adam` | Male | Deep |
| `am_michael` | Male | Clear |
| `am_echo` | Male | Neutral |
| `am_eric` | Male | Authoritative |
| `am_fenrir` | Male | Distinctive |
| `am_liam` | Male | Conversational |
| `am_onyx` | Male | Rich |
| `am_puck` | Male | Expressive |
| `am_santa` | Male | Warm |

**British English:**

| Voice ID | Gender | Style |
|---|---|---|
| `bf_emma` | Female | Clear, professional |
| `bf_isabella` | Female | Warm |
| `bf_alice` | Female | Crisp |
| `bf_lily` | Female | Soft |
| `bm_george` | Male | Authoritative |
| `bm_lewis` | Male | Smooth |
| `bm_daniel` | Male | Calm |
| `bm_fable` | Male | Expressive |

**Japanese:** `jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`, `jm_kumo`

**Mandarin Chinese:** `zf_xiaobei`, `zf_xiaoni`, `zf_xiaoxiao`, `zf_xiaoyi`, `zm_yunjian`, `zm_yunxi`, `zm_yunxia`, `zm_yunyang`

**Spanish:** `ef_dora`, `em_alex`, `em_santa`

**French:** `ff_siwis`

**Hindi:** `hf_alpha`, `hf_beta`, `hm_omega`, `hm_psi`

**Italian:** `if_sara`, `im_nicola`

**Brazilian Portuguese:** `pf_dora`, `pm_alex`, `pm_santa`

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
| `ballad` | `bm_lewis` |
| `marin` | `af_nicole` |
| `cedar` | `am_adam` |

> **Tip:** The server automatically selects the correct language pipeline from the voice ID prefix — no configuration needed. For example, `jf_alpha` loads the Japanese pipeline, `bf_emma` loads British English. Additional language pipelines are created on demand when needed.

All voices use a single shared model file (~320 MB). No re-download is needed when switching voices.

## Persistent data

All server data is stored in the Docker volume (`/var/lib/kokoro` inside the container):

```
/var/lib/kokoro/
├── hub/                           # Cached Kokoro model files (downloaded from HuggingFace)
├── .port                          # Active port (used by kokoro_manage)
├── .voice                         # Active default voice (used by kokoro_manage)
└── .server_addr                   # Cached server IP (used by kokoro_manage)
```

Back up the Docker volume to preserve the downloaded model. The model is ~320 MB and only needs to be downloaded once.

## Managing the server

Use `kokoro_manage` inside the running container to inspect and manage the server.

**Show server info:**

```bash
docker exec kokoro kokoro_manage --showinfo
```

**List available voices:**

```bash
docker exec kokoro kokoro_manage --listvoices
```

## Changing the voice

To change the default voice, update `KOKORO_VOICE` in your `kokoro.env` file and restart the container. No model re-download is required — all voices use the same Kokoro-82M model.

```bash
# Edit kokoro.env: set KOKORO_VOICE=bm_george
docker restart kokoro
```

> **Note:** Individual API requests can always specify a different voice using the `voice` field, regardless of the container default.

## Securing your server

If your Kokoro TTS server is reachable from the public internet — even briefly — apply at minimum these protections. Kokoro is CPU/GPU-intensive, so an unauthenticated endpoint can be abused to burn your compute resources.

**1. Use an API key.** Fresh installs with a mounted `/var/lib/kokoro` volume auto-generate an API key. Display it with `docker exec kokoro kokoro_manage --showkey`, or use `docker exec kokoro kokoro_manage --getkey` in scripts. Existing installs without a key remain open for backward compatibility; set `KOKORO_API_KEY` in your `env` file to enable authentication manually. All authenticated requests must include `Authorization: Bearer <key>`.

```bash
# Generate a 32-byte random key
openssl rand -hex 32
```

**2. Bind to localhost when fronted by a reverse proxy.** Replace `-p 8880:8880` with `-p 127.0.0.1:8880:8880` (or change `"8880:8880/tcp"` to `"127.0.0.1:8880:8880/tcp"` in `docker-compose.yml`) so the unencrypted port is not reachable directly from outside the host.

**3. Limit request body size at the proxy.** TTS requests carry text input; configure your reverse proxy to reject oversized request bodies (e.g. nginx `client_max_body_size 1M;`).

**4. Mind the log level.** `KOKORO_LOG_LEVEL=DEBUG` may write input text to logs. Keep it at `INFO` or higher on shared systems.

**5. Enable CORS at the proxy if calling from a browser.** The server does not set `Access-Control-Allow-Origin` headers by default; add them at your reverse proxy if you intend to call the API directly from a web page on a different origin.

**6. Consider rate limiting.** Place a rate-limit (e.g. nginx `limit_req_zone`, Caddy `rate_limit`) in front of the server to cap concurrent synthesis requests per client IP.

## Using a reverse proxy

For internet-facing deployments, place a reverse proxy in front of the TTS server to handle HTTPS termination. The server works without HTTPS on a local or trusted network, but HTTPS is recommended when the API endpoint is exposed to the internet.

Use one of the following addresses to reach the TTS container from your reverse proxy:

- **`kokoro:8880`** — if your reverse proxy runs as a container in the **same Docker network** as the TTS server (e.g. defined in the same `docker-compose.yml`).
- **`127.0.0.1:8880`** — if your reverse proxy runs **on the host** and port `8880` is published (the default `docker-compose.yml` publishes it).

**Example with [Caddy](https://caddyserver.com/docs/) ([Docker image](https://hub.docker.com/_/caddy))** (automatic TLS via Let's Encrypt, reverse proxy in the same Docker network):

`Caddyfile`:
```
kokoro.example.com {
  reverse_proxy kokoro:8880
}
```

**Example with nginx** (reverse proxy on the host):

```nginx
server {
    listen 443 ssl;
    server_name kokoro.example.com;

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

## Update Docker image

To update the Docker image and container, first [download](#download) the latest version:

```bash
docker pull hwdsl2/kokoro-server
```

If the Docker image is already up to date, you should see:

```
Status: Image is up to date for hwdsl2/kokoro-server:latest
```

Otherwise, it will download the latest version. Remove and re-create the container:

```bash
docker rm -f kokoro
# Then re-run the docker run command from Quick start with the same volume and port.
```

Your downloaded model is preserved in the `kokoro-data` volume.

## Using with other AI services

Kokoro can be used as the text-to-speech service in a broader self-hosted AI setup.

For full and lightweight Docker Compose stacks, manual `docker run` examples, and voice/RAG/MCP pipeline examples with Kokoro, Embeddings, LiteLLM, Ollama, Docling, and MCP Gateway, see [Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack).

## Usage counts

This image uses public GitHub release asset download counts for anonymous, aggregate usage counts. Counts are approximate and are not unique users or active installs. The image does not send a telemetry payload or use a private collector. It only attempts the best-effort count after the server starts successfully with a mounted `/var/lib/kokoro` volume, and again when that persistent install first runs a different image build. To opt out, set `KOKORO_DISABLE_USAGE_COUNTS=1`.

## Technical details

- Base image: `python:3.12-slim` (Debian)
- Runtime: Python 3 (virtual environment at `/opt/venv`)
- TTS engine: [Kokoro](https://github.com/hexgrad/kokoro) (Kokoro-82M, Apache 2.0) with PyTorch (CPU and CUDA GPU)
- API framework: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- Audio encoding: [soundfile](https://github.com/bastibe/python-soundfile) (wav/flac), [ffmpeg](https://ffmpeg.org/) (mp3/aac/opus)
- Data directory: `/var/lib/kokoro` (Docker volume)
- Model storage: HuggingFace Hub format inside the volume — downloaded once, reused on restarts
- Sample rate: 24 kHz (native Kokoro output)

## License

**Note:** The software components inside the pre-built image (such as Kokoro and its dependencies) are under the respective licenses chosen by their respective copyright holders. As for any pre-built image usage, it is the image user's responsibility to ensure that any use of this image complies with any relevant licenses for all software contained within.

Copyright (C) 2026 Lin Song   
This work is licensed under the [MIT License](https://opensource.org/licenses/MIT).

**Kokoro TTS** is Copyright (C) hexgrad, and is distributed under the [Apache License 2.0](https://github.com/hexgrad/kokoro/blob/main/LICENSE).

This project is an independent Docker setup for Kokoro and is not affiliated with, endorsed by, or sponsored by hexgrad or OpenAI.
