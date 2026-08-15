[English](README.md) | [简体中文](README-zh.md) | [繁體中文](README-zh-Hant.md) | [Русский](README-ru.md)

# Docker 上的 Kokoro 文字转语音

[![构建状态](https://github.com/hwdsl2/docker-kokoro/actions/workflows/main.yml/badge.svg)](https://github.com/hwdsl2/docker-kokoro/actions/workflows/main.yml) &nbsp;[![Docker Pulls](https://raw.githubusercontent.com/hwdsl2/badges/main/img/docker-pulls-kokoro-server.svg)](https://hub.docker.com/r/hwdsl2/kokoro-server) &nbsp;[![开源协议: MIT](docs/images/license.svg)](https://opensource.org/licenses/MIT) &nbsp;[![在 Colab 中打开](https://colab.research.google.com/assets/colab-badge.svg)](https://vpnsetup.net/kokoro-notebook)

[Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack/blob/main/README-zh.md) 的一部分 ─ 一条命令部署完整的自托管 AI 技术栈。

一个用于运行 [Kokoro](https://github.com/hexgrad/kokoro) 文字转语音服务器的 Docker 镜像。提供与 OpenAI 兼容的音频语音 API。基于 Debian（python:3.12-slim）。专为简单、私密、自托管而设计。

**功能特性：**

- 兼容 OpenAI 的 `POST /v1/audio/speech` 接口 —— 已使用 OpenAI TTS API 的应用只需修改一行即可切换
- 54 种高质量语音，覆盖 9 种语言（英语、日语、中文、西班牙语、法语、意大利语等）
- 支持映射到本地 Kokoro 语音的 OpenAI 语音名称别名（`alloy`、`nova`、`echo` 等），以及原生 Kokoro 语音 ID（`af_heart`、`bm_george` 等）
- 音频保留在您的服务器上 —— 不向第三方发送数据
- 支持所有主流输出格式：`mp3`、`wav`、`flac`、`opus`、`aac`、`pcm`
- 流式传输支持 —— 设置 `stream_format` 为 `"audio"` 或 `"sse"` 可在每句话合成完成后立即接收音频，减少首次出声的等待时间
- NVIDIA GPU（CUDA）加速推理（`:cuda` 镜像标签）
- 离线/气隙模式 —— 使用预缓存模型无需访问互联网（`KOKORO_LOCAL_ONLY`）
- 通过 [GitHub Actions](https://github.com/hwdsl2/docker-kokoro/actions) 自动构建和发布
- 通过 Docker 数据卷持久化模型缓存
- 多架构：`linux/amd64`、`linux/arm64`

**另提供：**

- **新书：**[The Self-Hosted AI Builder’s Guide](https://books2read.com/aiguide?store=amazon)——将此服务部署为安全、完整的私有 AI 技术栈的一部分
- 在线试用：[在 Colab 中打开](https://vpnsetup.net/kokoro-notebook)——无需 Docker 或安装
- 相关 AI 服务：[Whisper](https://github.com/hwdsl2/docker-whisper/blob/main/README-zh.md)、[Embeddings](https://github.com/hwdsl2/docker-embeddings/blob/main/README-zh.md)、[LiteLLM](https://github.com/hwdsl2/docker-litellm/blob/main/README-zh.md)、[Ollama](https://github.com/hwdsl2/docker-ollama/blob/main/README-zh.md)、[Docling](https://github.com/hwdsl2/docker-docling/blob/main/README-zh.md)、[MCP Gateway](https://github.com/hwdsl2/docker-mcp-gateway/blob/main/README-zh.md)

## 社区

- 📬 [订阅项目更新](https://selfhostedstack.beehiiv.com/subscribe?utm_campaign=ai-zh)（每月 1–2 封邮件）——获取免费的 AI 和 VPN 部署指南（PDF，英文）
- 💬 加入 [r/selfhostedstack](https://www.reddit.com/r/selfhostedstack/) 社区，参与讨论和项目展示
- ⭐ 如果你觉得本项目有用，请为仓库加星——这有助于让更多人发现它。

<details>
<summary>自托管 VPN 和网络项目</summary>

- [Setup IPsec VPN](https://github.com/hwdsl2/setup-ipsec-vpn/blob/master/README-zh.md)
- [Docker 上的 IPsec VPN](https://github.com/hwdsl2/docker-ipsec-vpn-server/blob/master/README-zh.md)
- [WireGuard](https://github.com/hwdsl2/docker-wireguard/blob/main/README-zh.md)
- [OpenVPN](https://github.com/hwdsl2/docker-openvpn/blob/main/README-zh.md)
- [Headscale](https://github.com/hwdsl2/docker-headscale/blob/main/README-zh.md)

</details>

## 快速开始

使用以下命令启动 Kokoro TTS 服务器：

```bash
docker run \
    --name kokoro \
    --restart=always \
    -v kokoro-data:/var/lib/kokoro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-server
```

<details>
<summary><strong>GPU 快速开始（NVIDIA CUDA）</strong></summary>

如果您有 NVIDIA GPU，可使用 `:cuda` 镜像进行硬件加速推理：

```bash
docker run \
    --name kokoro \
    --restart=always \
    --gpus=all \
    -v kokoro-data:/var/lib/kokoro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-server:cuda
```

**要求：** NVIDIA GPU、已在主机上安装 [NVIDIA 驱动](https://www.nvidia.com/en-us/drivers/) 575.57.08+（Linux）或 576.57+（Windows），以及 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)。`:cuda` 镜像仅支持 `linux/amd64`。

</details>

**重要：** 由于包含 PyTorch 运行时和 Kokoro 模型，该镜像需要至少 1.5 GB 可用内存。总内存为 1 GB 或更少的系统不受支持。

**注：** 如需面向互联网的部署，**强烈建议**使用[反向代理](#使用反向代理)来添加 HTTPS。此时，还应将上述 `docker run` 命令中的 `-p 8880:8880` 替换为 `-p 127.0.0.1:8880:8880`，以防止从外部直接访问未加密端口。

Kokoro 模型（约 320 MB）将在首次启动时自动下载并缓存。查看日志确认服务器已就绪：

```bash
docker logs kokoro
```

看到 "Kokoro text-to-speech server is ready" 后，即可合成您的第一个音频文件：

```bash
curl http://您的服务器IP:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"你好，世界！","voice":"af_heart"}' \
    --output speech.mp3
```

## 系统要求

- 安装了 Docker 的 Linux 服务器（本地或云端）
- 支持的架构：`amd64`（x86_64）、`arm64`（例如 Raspberry Pi 4/5、AWS Graviton）
- 最低可用内存：约 1.5 GB（模型约 320 MB；PyTorch 运行时需要额外内存）
- 首次下载模型需要互联网访问（之后模型会缓存在本地）。若使用预缓存模型并设置 `KOKORO_LOCAL_ONLY=true` 则不需要。

**GPU 加速（`:cuda` 镜像）要求：**

- 支持 CUDA 的 NVIDIA GPU（计算能力 6.0+）
- 主机上已安装 [NVIDIA 驱动](https://www.nvidia.com/en-us/drivers/) 575.57.08+（Linux）或 576.57+（Windows）
- 已安装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- `:cuda` 镜像仅支持 `linux/amd64`

对于面向互联网的部署，请参阅[使用反向代理](#使用反向代理)以添加 HTTPS。

## 下载

从 [Docker Hub](https://hub.docker.com/r/hwdsl2/kokoro-server/) 获取可信构建：

```bash
docker pull hwdsl2/kokoro-server
```

如需 NVIDIA GPU 加速，请拉取 `:cuda` 标签：

```bash
docker pull hwdsl2/kokoro-server:cuda
```

也可从 [Quay.io](https://quay.io/repository/hwdsl2/kokoro-server) 下载：

```bash
docker pull quay.io/hwdsl2/kokoro-server
docker image tag quay.io/hwdsl2/kokoro-server hwdsl2/kokoro-server
```

支持平台：`linux/amd64` 和 `linux/arm64`。`:cuda` 标签仅支持 `linux/amd64`。

## 环境变量

所有变量均为可选。挂载 `/var/lib/kokoro` 数据卷的新安装会自动生成 Bearer 令牌。没有密钥的既有安装会保持开放以兼容旧行为。

此 Docker 镜像使用以下变量，可在 `env` 文件中声明（参见[示例](kokoro.env.example)）：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `KOKORO_VOICE` | 合成语音的默认音色。参见[可用语音](#可用语音)了解所有选项。支持 Kokoro 语音 ID（`af_heart`）或 OpenAI 别名（`alloy`、`ballad` 等）。 | `af_heart` |
| `KOKORO_SPEED` | 默认语速。范围：`0.25`（最慢）到 `4.0`（最快）。 | `1.0` |
| `KOKORO_PORT` | API 的 HTTP 端口（1–65535）。 | `8880` |
| `KOKORO_LANG_CODE` | 若已设置，则在启动时仅加载该语言的语音处理管线（`a`=美式英语，`b`=英式英语，`e`=西班牙语，`f`=法语，`h`=印地语，`i`=意大利语，`j`=日语，`p`=巴西葡萄牙语，`z`=普通话）。未设置时，根据 `KOKORO_VOICE` 前缀自动选择语音处理管线。当请求使用其他语言时，会按需创建对应的语音处理管线。 | *(未设置)* |
| `KOKORO_API_KEY` | 可选的 Bearer 令牌。新持久化安装会自动生成。设置后所有 API 请求须包含 `Authorization: Bearer <key>`。显式设置为空可禁用认证。 | 新持久化安装自动生成 |
| `KOKORO_LOG_LEVEL` | 日志级别：`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`。 | `INFO` |
| `KOKORO_LOCAL_ONLY` | 设置为任意非空值（例如 `true`）时，禁用所有 HuggingFace 模型下载。适用于离线或气隙部署（需预缓存模型）。 | *(未设置)* |
| `KOKORO_DISABLE_USAGE_COUNTS` | 设为 `1` 可禁用匿名聚合使用计数。 | *(未设置)* |

**注：** 在 `env` 文件中，值可以用单引号括起来，例如 `VAR='value'`。`=` 两侧不要有空格。如果更改了 `KOKORO_PORT`，请相应更新 `docker run` 命令中的 `-p` 参数。

使用 `env` 文件的示例：

```bash
cp kokoro.env.example kokoro.env
# 编辑 kokoro.env 后执行：
docker run \
    --name kokoro \
    --restart=always \
    -v kokoro-data:/var/lib/kokoro \
    -v ./kokoro.env:/kokoro.env:ro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-server
```

`env` 文件以绑定挂载方式传入容器，每次重启时自动生效，无需重建容器。

<details>
<summary>也可通过 <code>--env-file</code> 传入</summary>

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

## 使用 docker-compose

```bash
cp kokoro.env.example kokoro.env
# 按需编辑 kokoro.env，然后：
docker compose up -d
docker logs kokoro
```

示例 `docker-compose.yml`（已包含在项目中）：

```yaml
services:
  kokoro:
    image: hwdsl2/kokoro-server
    container_name: kokoro
    restart: always
    ports:
      - "8880:8880/tcp"  # 如使用主机反向代理，改为 "127.0.0.1:8880:8880/tcp"
    volumes:
      - kokoro-data:/var/lib/kokoro
      - ./kokoro.env:/kokoro.env:ro

volumes:
  kokoro-data:
    name: kokoro-data
```

**注：** 如需面向公网部署，强烈建议使用[反向代理](#使用反向代理)启用 HTTPS。此时请将 `docker-compose.yml` 中的 `"8880:8880/tcp"` 改为 `"127.0.0.1:8880:8880/tcp"`，以防止未加密端口被直接访问。

<details>
<summary><strong>使用 docker-compose 启用 GPU（NVIDIA CUDA）</strong></summary>

GPU 部署提供单独的 `docker-compose.cuda.yml` 文件：

```bash
cp kokoro.env.example kokoro.env
# 按需编辑 kokoro.env，然后：
docker compose -f docker-compose.cuda.yml up -d
docker logs kokoro
```

示例 `docker-compose.cuda.yml`（已包含在项目中）：

```yaml
services:
  kokoro:
    image: hwdsl2/kokoro-server:cuda
    container_name: kokoro
    restart: always
    ports:
      - "8880:8880/tcp"  # 如使用主机反向代理，改为 "127.0.0.1:8880:8880/tcp"
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

## API 参考

该 API 与 [OpenAI 文字转语音接口](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create)兼容。任何已调用 `https://api.openai.com/v1/audio/speech` 的应用，只需设置以下环境变量即可切换到自托管：

为便于客户端兼容，OpenAI 语音名称会作为本地别名接受。这些别名会映射到 Kokoro 语音，并不会复现 OpenAI 的专有语音。`voice` 字段可以是字符串，也可以是带有 `id` 字段的对象；未知语音会返回 `400`。

```
OPENAI_BASE_URL=http://您的服务器IP:8880
```

### 合成语音

```
POST /v1/audio/speech
Content-Type: application/json
```

**请求体：**

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---|---|
| `model` | 字符串 | ✅ | 传入 `tts-1`、`tts-1-hd` 或 `kokoro`（均使用 Kokoro-82M）。 |
| `input` | 字符串 | ✅ | 要合成的文本。最多 4096 个字符。 |
| `voice` | 字符串或对象 | ✅ | 使用的语音。参见[可用语音](#可用语音)。支持 Kokoro ID、映射到本地 Kokoro 语音的 OpenAI 别名，或带有 `id` 字段的对象。未知语音会返回 `400`。 |
| `response_format` | 字符串 | — | 输出格式。默认：`mp3`。选项：`mp3`、`opus`、`aac`、`flac`、`wav`、`pcm`。`pcm` 是 24 kHz、单声道、无文件头的原始有符号 16 位小端音频。 |
| `speed` | 浮点数 | — | 语速。默认：`1.0`。范围：`0.25`–`4.0`。 |
| `instructions` | 字符串 | — | 通过附加指令控制语音。为 API 兼容性而接受，但 Kokoro 引擎当前不支持（将被忽略）。 |
| `stream_format` | 字符串 | — | 音频流式传输格式。选项：`audio`、`sse`。设为 `audio` 时，音频字节通过分块传输编码传送。设为 `sse` 时，响应使用 Server-Sent Events，包含 `speech.audio.delta` 和 `speech.audio.done` 事件（OpenAI 流式语音协议）。SSE WAV 的第一个 delta 是流式 WAV 头，后续 delta 为 24 kHz 单声道原始 PCM_S16LE；SSE PCM delta 为 24 kHz 单声道、无文件头的原始 PCM_S16LE。省略时返回完整音频。 |
| `volume_multiplier` | 浮点数 | — | 输出音量倍数。默认：`1.0`。范围：`0.1`–`2.0`。大于 `1.0` 时增大音量，小于 `1.0` 时减小音量。缩放后样本将被截断以防止失真。 |

**示例：**

```bash
curl http://您的服务器IP:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"敏捷的棕色狐狸跳过了懒惰的狗。","voice":"af_heart"}' \
    --output speech.mp3
```

使用不同语音和格式：

```bash
curl http://您的服务器IP:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"Hello from London.","voice":"bm_george","response_format":"wav","speed":0.9}' \
    --output speech.wav
```

使用 API 密钥认证：

```bash
curl http://您的服务器IP:8880/v1/audio/speech \
    -H "Authorization: Bearer your_api_key" \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"Hello world","voice":"nova"}' \
    --output speech.mp3
```

**响应：** 带有相应 `Content-Type` 标头的二进制音频数据。

### 列出语音

```
GET /v1/voices
```

返回所有可用的 Kokoro 语音 ID 及其 OpenAI 别名映射。

```bash
curl http://您的服务器IP:8880/v1/voices
```

### 列出模型

```
GET /v1/models
```

以 OpenAI 兼容格式返回当前活跃模型。

```bash
curl http://您的服务器IP:8880/v1/models
```

### 交互式 API 文档

访问以下地址可使用交互式 Swagger UI：

```
http://您的服务器IP:8880/docs
```

## 可用语音

随时使用 `kokoro_manage --listvoices` 查看完整列表：

```bash
docker exec kokoro kokoro_manage --listvoices
```

**美式英语：**

| 语音 ID | 性别 | 风格 |
|---|---|---|
| `af_heart` | 女声 | 温暖、自然 —— **默认** |
| `af_aoede` | 女声 | |
| `af_bella` | 女声 | 富有表现力 |
| `af_jessica` | 女声 | 活力 |
| `af_kore` | 女声 | |
| `af_nicole` | 女声 | 亲切 |
| `af_nova` | 女声 | 清晰 |
| `af_river` | 女声 | 沉静 |
| `af_sarah` | 女声 | 对话感强 |
| `af_sky` | 女声 | 中性、多用途 |
| `af_alloy` | 女声 | 均衡 |
| `am_adam` | 男声 | 低沉 |
| `am_michael` | 男声 | 清晰 |
| `am_echo` | 男声 | 中性 |
| `am_eric` | 男声 | 权威 |
| `am_fenrir` | 男声 | 独特 |
| `am_liam` | 男声 | 对话感强 |
| `am_onyx` | 男声 | 醇厚 |
| `am_puck` | 男声 | 富有表现力 |
| `am_santa` | 男声 | 温暖 |

**英式英语：**

| 语音 ID | 性别 | 风格 |
|---|---|---|
| `bf_emma` | 女声 | 清晰、专业 |
| `bf_isabella` | 女声 | 温暖 |
| `bf_alice` | 女声 | 清脆 |
| `bf_lily` | 女声 | 柔和 |
| `bm_george` | 男声 | 权威 |
| `bm_lewis` | 男声 | 流畅 |
| `bm_daniel` | 男声 | 沉静 |
| `bm_fable` | 男声 | 富有表现力 |

**日语：** `jf_alpha`、`jf_gongitsune`、`jf_nezumi`、`jf_tebukuro`、`jm_kumo`

**普通话：** `zf_xiaobei`、`zf_xiaoni`、`zf_xiaoxiao`、`zf_xiaoyi`、`zm_yunjian`、`zm_yunxi`、`zm_yunxia`、`zm_yunyang`

**西班牙语：** `ef_dora`、`em_alex`、`em_santa`

**法语：** `ff_siwis`

**印地语：** `hf_alpha`、`hf_beta`、`hm_omega`、`hm_psi`

**意大利语：** `if_sara`、`im_nicola`

**巴西葡萄牙语：** `pf_dora`、`pm_alex`、`pm_santa`

**OpenAI 语音别名：** `alloy`、`echo`、`fable`、`onyx`、`nova`、`shimmer`、`ash`、`coral`、`sage`、`verse`、`ballad`、`marin`、`cedar`（会映射到本地 Kokoro 语音）。

> **提示：** 服务器会根据语音 ID 前缀自动选择对应的语言处理管线，无需任何配置。例如，`jf_alpha` 会加载日语管线，`bf_emma` 会加载英式英语管线。其他语言的管线会在需要时按需创建。

所有语音共享同一个模型文件（约 320 MB）。切换语音时无需重新下载。

## 持久化数据

所有服务器数据存储在 Docker 数据卷（容器内的 `/var/lib/kokoro`）中：

```
/var/lib/kokoro/
├── hub/                           # 缓存的 Kokoro 模型文件（从 HuggingFace 下载）
├── .port                          # 当前端口（供 kokoro_manage 使用）
├── .voice                         # 当前默认语音（供 kokoro_manage 使用）
└── .server_addr                   # 缓存的服务器 IP（供 kokoro_manage 使用）
```

备份 Docker 数据卷以保留已下载的模型。模型约 320 MB，仅需下载一次。

## 管理服务器

在运行中的容器内使用 `kokoro_manage` 来检查和管理服务器。

**显示服务器信息：**

```bash
docker exec kokoro kokoro_manage --showinfo
```

**列出可用语音：**

```bash
docker exec kokoro kokoro_manage --listvoices
```

## 更换语音

要更换默认语音，请在 `kokoro.env` 文件中更新 `KOKORO_VOICE` 并重启容器。无需重新下载模型 —— 所有语音共用同一个 Kokoro-82M 模型。

```bash
# 编辑 kokoro.env：设置 KOKORO_VOICE=bm_george
docker restart kokoro
```

> **注：** 单次 API 请求始终可以通过 `voice` 字段指定不同的语音，不受容器默认设置影响。

## 保护你的服务器

如果你的 Kokoro TTS 服务器可从公网访问 —— 即使只是短暂可达 —— 也请至少采取以下保护措施。Kokoro 对 CPU/GPU 资源消耗较大，未做身份验证的接口可能被滥用，浪费你的计算资源。

**1. 使用 API 密钥。** 挂载 `/var/lib/kokoro` 数据卷的新安装会自动生成 API 密钥。可用 `docker exec kokoro kokoro_manage --showkey` 查看；脚本中可用 `docker exec kokoro kokoro_manage --getkey`。没有密钥的既有安装会保持开放以兼容旧行为；也可以在 `env` 文件中设置 `KOKORO_API_KEY` 手动启用认证。所有已认证请求必须包含 `Authorization: Bearer <key>`。

```bash
# 生成 32 字节的随机密钥
openssl rand -hex 32
```

**2. 在反向代理后面时绑定到 localhost。** 将 `-p 8880:8880` 替换为 `-p 127.0.0.1:8880:8880`（或在 `docker-compose.yml` 中将 `"8880:8880/tcp"` 改为 `"127.0.0.1:8880:8880/tcp"`），使未加密端口无法从主机外部直接访问。

**3. 在代理处限制请求体大小。** TTS 请求携带文本输入；配置反向代理以拒绝过大的请求体（例如 nginx `client_max_body_size 1M;`）。

**4. 注意日志级别。** `KOKORO_LOG_LEVEL=DEBUG` 可能会将输入文本写入日志。在共享系统上请保持 `INFO` 或更高级别。

**5. 浏览器调用时在代理处启用 CORS。** 本服务器默认不设置 `Access-Control-Allow-Origin` 响应头；若需在不同源的网页中直接调用本 API，请在反向代理处添加 CORS 头。

**6. 考虑限流。** 在服务器前部署限流（如 nginx `limit_req_zone`、Caddy `rate_limit`），限制每个客户端 IP 的并发合成请求数。

## 使用反向代理

对于面向互联网的部署，请在 TTS 服务器前放置反向代理以处理 HTTPS 终止。

从反向代理访问 TTS 容器，使用以下地址之一：

- **`kokoro:8880`** —— 若反向代理作为容器运行在与 TTS 服务器**相同的 Docker 网络**中。
- **`127.0.0.1:8880`** —— 若反向代理运行在**主机上**且端口 `8880` 已发布。

**使用 [Caddy](https://caddyserver.com/docs/)（[Docker 镜像](https://hub.docker.com/_/caddy)）的示例**（通过 Let's Encrypt 自动申请 TLS，反向代理在同一 Docker 网络中）：

`Caddyfile`：
```
kokoro.example.com {
  reverse_proxy kokoro:8880
}
```

**使用 nginx 的示例**（反向代理运行在主机上）：

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

## 更新 Docker 镜像

如需更新 Docker 镜像和容器，首先[下载](#下载)最新版本：

```bash
docker pull hwdsl2/kokoro-server
```

如果镜像已是最新版本，您将看到：

```
Status: Image is up to date for hwdsl2/kokoro-server:latest
```

否则将下载最新版本。删除并重新创建容器：

```bash
docker rm -f kokoro
# 然后使用相同的数据卷和端口重新运行快速开始中的 docker run 命令。
```

您下载的模型将保留在 `kokoro-data` 数据卷中。

## 与其他 AI 服务配合使用

Kokoro 可作为更广泛的自托管 AI 设置中的文字转语音服务。

如需完整和轻量级 Docker Compose 技术栈、手动 `docker run` 示例，以及结合 Kokoro、Embeddings、LiteLLM、Ollama、Docling 和 MCP Gateway 的语音/RAG/MCP 流水线示例，请参阅 [Self-Hosted AI Stack](https://github.com/hwdsl2/self-hosted-ai-stack/blob/main/README-zh.md)。

## 使用计数

此镜像使用公开的 GitHub Release 资源下载次数进行匿名聚合使用计数。计数是近似值，不代表唯一用户或活跃安装。镜像不会发送遥测负载，也不会使用私有收集器。仅当服务器成功启动且挂载了 `/var/lib/kokoro` 卷后，才会以尽力而为方式计数；当该持久化安装首次运行不同镜像构建时，也会再次计数。要退出，请设置 `KOKORO_DISABLE_USAGE_COUNTS=1`。

## 技术细节

- 基础镜像：`python:3.12-slim`（Debian）
- 运行时：Python 3（虚拟环境位于 `/opt/venv`）
- TTS 引擎：[Kokoro](https://github.com/hexgrad/kokoro)（Kokoro-82M，Apache 2.0），使用 PyTorch（CPU 和 CUDA GPU）
- API 框架：[FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- 音频编码：[soundfile](https://github.com/bastibe/python-soundfile)（wav/flac）、[ffmpeg](https://ffmpeg.org/)（mp3/aac/opus）
- 数据目录：`/var/lib/kokoro`（Docker 数据卷）
- 模型存储：数据卷内的 HuggingFace Hub 格式 —— 下载一次，重启后复用
- 采样率：24 kHz（Kokoro 原生输出）

## 授权协议

**注：** 预构建镜像中包含的软件组件（如 Kokoro 及其依赖项）均受各自版权持有者所选许可证约束。使用预构建镜像时，用户有责任确保其使用方式符合镜像内所有软件的相关许可证要求。

版权所有 (C) 2026 Lin Song
本作品采用 [MIT 许可证](https://opensource.org/licenses/MIT)授权。

**Kokoro TTS** 版权归 hexgrad 所有，依据 [Apache License 2.0](https://github.com/hexgrad/kokoro/blob/main/LICENSE) 分发。

本项目是 Kokoro 的独立 Docker 封装，与 hexgrad 或 OpenAI 无关联、无背书。
