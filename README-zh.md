[English](README.md) | [简体中文](README-zh.md) | [繁體中文](README-zh-Hant.md) | [Русский](README-ru.md)

# Docker 上的 Kokoro 文字转语音

[![构建状态](https://github.com/hwdsl2/docker-tts/actions/workflows/main.yml/badge.svg)](https://github.com/hwdsl2/docker-tts/actions/workflows/main.yml) &nbsp;[![开源协议: MIT](docs/images/license.svg)](https://opensource.org/licenses/MIT)

一个用于运行 [Kokoro](https://github.com/hexgrad/kokoro) 文字转语音服务器的 Docker 镜像。提供与 OpenAI 兼容的音频语音 API。基于 Debian（python:3.12-slim）。专为简单、私密、自托管而设计。

- 兼容 OpenAI 的 `POST /v1/audio/speech` 接口 —— 已使用 OpenAI TTS API 的应用只需修改一行即可切换
- 20+ 种高质量语音：美式英语和英式英语，男女均有
- 同时支持 OpenAI 语音名称（`alloy`、`nova`、`echo` 等）和原生 Kokoro 语音 ID（`af_heart`、`bm_george` 等）
- 音频保留在您的服务器上 —— 不向第三方发送数据
- 支持所有主流输出格式：`mp3`、`wav`、`flac`、`opus`、`aac`、`pcm`
- 离线/气隙模式 —— 使用预缓存模型无需访问互联网（`TTS_LOCAL_ONLY`）
- 通过 [GitHub Actions](https://github.com/hwdsl2/docker-tts/actions/workflows/main.yml) 自动构建和发布
- 通过 Docker 数据卷持久化模型缓存
- 多架构：`linux/amd64`、`linux/arm64`

**另提供：** [Whisper](https://github.com/hwdsl2/docker-whisper/blob/main/README-zh.md)、[LiteLLM](https://github.com/hwdsl2/docker-litellm/blob/main/README-zh.md)、[WireGuard](https://github.com/hwdsl2/docker-wireguard/blob/main/README-zh.md)、[OpenVPN](https://github.com/hwdsl2/docker-openvpn/blob/main/README-zh.md)、[IPsec VPN](https://github.com/hwdsl2/docker-ipsec-vpn-server/blob/master/README-zh.md) 和 [Headscale](https://github.com/hwdsl2/docker-headscale/blob/main/README-zh.md) 的 Docker 镜像。

## 快速开始

使用以下命令启动 Kokoro TTS 服务器：

```bash
docker run \
    --name tts \
    --restart=always \
    -v tts-data:/var/lib/tts \
    -p 8880:8880 \
    -d hwdsl2/kokoro-tts
```

**注：** 如需面向互联网的部署，**强烈建议**使用[反向代理](#使用反向代理)来添加 HTTPS。此时，还应将上述 `docker run` 命令中的 `-p 8880:8880` 替换为 `-p 127.0.0.1:8880:8880`，以防止从外部直接访问未加密端口。

Kokoro 模型（约 320 MB）将在首次启动时自动下载并缓存。查看日志确认服务器已就绪：

```bash
docker logs tts
```

看到"Kokoro TTS server is ready"后，即可合成您的第一个音频文件：

```bash
curl http://您的服务器IP:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"你好，世界！","voice":"af_heart"}' \
    --output speech.mp3
```

## 系统要求

- 安装了 Docker 的 Linux 服务器（本地或云端）
- 支持的架构：`amd64`（x86_64）、`arm64`（例如 Raspberry Pi 4/5、AWS Graviton）
- 最低可用内存：约 1 GB（模型约 320 MB；PyTorch 运行时需要额外内存）
- 首次下载模型需要互联网访问（之后模型会缓存在本地）。若使用预缓存模型并设置 `TTS_LOCAL_ONLY=true` 则不需要。

对于面向互联网的部署，请参阅[使用反向代理](#使用反向代理)以添加 HTTPS。

## 下载

从 [Docker Hub](https://hub.docker.com/r/hwdsl2/kokoro-tts/) 获取可信构建：

```bash
docker pull hwdsl2/kokoro-tts
```

也可从 [Quay.io](https://quay.io/repository/hwdsl2/kokoro-tts) 下载：

```bash
docker pull quay.io/hwdsl2/kokoro-tts
docker image tag quay.io/hwdsl2/kokoro-tts hwdsl2/kokoro-tts
```

支持平台：`linux/amd64` 和 `linux/arm64`。

## 环境变量

所有变量均为可选。若未设置，将自动使用安全的默认值。

此 Docker 镜像使用以下变量，可在 `env` 文件中声明（参见[示例](tts.env.example)）：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `TTS_VOICE` | 合成语音的默认音色。参见[可用语音](#可用语音)了解所有选项。支持 Kokoro 语音 ID（`af_heart`）或 OpenAI 别名（`alloy`）。 | `af_heart` |
| `TTS_SPEED` | 默认语速。范围：`0.25`（最慢）到 `4.0`（最快）。 | `1.0` |
| `TTS_PORT` | API 的 HTTP 端口（1–65535）。 | `8880` |
| `TTS_LANG_CODE` | TTS 管线的语言/口音。`a` 为美式英语，`b` 为英式英语。 | `a` |
| `TTS_API_KEY` | 可选的 Bearer 令牌。设置后，所有 API 请求须包含 `Authorization: Bearer <key>`。 | *(未设置)* |
| `TTS_LOG_LEVEL` | 日志级别：`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`。 | `INFO` |
| `TTS_LOCAL_ONLY` | 设置为任意非空值（例如 `true`）时，禁用所有 HuggingFace 模型下载。适用于离线或气隙部署（需预缓存模型）。 | *(未设置)* |

**注意：** 在 `env` 文件中，值可以用单引号括起来，例如 `VAR='value'`。`=` 两侧不要有空格。如果更改了 `TTS_PORT`，请相应更新 `docker run` 命令中的 `-p` 参数。

使用 `env` 文件的示例：

```bash
cp tts.env.example tts.env
# 编辑 tts.env 后执行：
docker run \
    --name tts \
    --restart=always \
    -v tts-data:/var/lib/tts \
    -v ./tts.env:/tts.env:ro \
    -p 8880:8880 \
    -d hwdsl2/kokoro-tts
```

`env` 文件以绑定挂载方式传入容器，每次重启时自动生效，无需重建容器。

## 使用 docker-compose

```bash
cp tts.env.example tts.env
# 按需编辑 tts.env，然后：
docker compose up -d
docker logs tts
```

## API 参考

该 API 与 [OpenAI 文字转语音接口](https://platform.openai.com/docs/api-reference/audio/createSpeech)完全兼容。任何已调用 `https://api.openai.com/v1/audio/speech` 的应用，只需设置以下环境变量即可切换到自托管：

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
| `voice` | 字符串 | ✅ | 使用的语音。参见[可用语音](#可用语音)。支持 Kokoro ID 或 OpenAI 别名。 |
| `response_format` | 字符串 | — | 输出格式。默认：`mp3`。选项：`mp3`、`opus`、`aac`、`flac`、`wav`、`pcm`。 |
| `speed` | 浮点数 | — | 语速。默认：`1.0`。范围：`0.25`–`4.0`。 |

**示例：**

```bash
curl http://您的服务器IP:8880/v1/audio/speech \
    -H "Content-Type: application/json" \
    -d '{"model":"tts-1","input":"敏捷的棕色狐狸跳过了懒惰的狗。","voice":"af_heart"}' \
    --output speech.mp3
```

**响应：** 带有相应 `Content-Type` 标头的二进制音频数据。

### 交互式 API 文档

访问以下地址可使用交互式 Swagger UI：

```
http://您的服务器IP:8880/docs
```

## 可用语音

随时使用 `tts_manage --listvoices` 查看完整列表：

```bash
docker exec tts tts_manage --listvoices
```

| 语音 ID | 口音 | 性别 | 风格 |
|---|---|---|---|
| `af_heart` | 美式 | 女声 | 温暖、自然 —— **默认** |
| `af_bella` | 美式 | 女声 | 富有表现力 |
| `af_nova` | 美式 | 女声 | 清晰 |
| `af_sky` | 美式 | 女声 | 中性、多用途 |
| `af_sarah` | 美式 | 女声 | 对话感强 |
| `af_nicole` | 美式 | 女声 | 亲切 |
| `am_adam` | 美式 | 男声 | 低沉 |
| `am_michael` | 美式 | 男声 | 清晰 |
| `am_echo` | 美式 | 男声 | 中性 |
| `am_onyx` | 美式 | 男声 | 醇厚 |
| `bf_emma` | 英式 | 女声 | 清晰、专业 |
| `bf_isabella` | 英式 | 女声 | 温暖 |
| `bm_george` | 英式 | 男声 | 权威 |
| `bm_lewis` | 英式 | 男声 | 流畅 |

> **提示：** 英式语音（`bf_*`、`bm_*`）在设置 `TTS_LANG_CODE=b` 时效果最佳。

所有语音共享同一个模型文件（约 320 MB）。切换语音时无需重新下载。

## 管理服务器

在运行中的容器内使用 `tts_manage` 来检查和管理服务器。

**显示服务器信息：**

```bash
docker exec tts tts_manage --showinfo
```

**列出可用语音：**

```bash
docker exec tts tts_manage --listvoices
```

## 使用反向代理

对于面向互联网的部署，请在 TTS 服务器前放置反向代理以处理 HTTPS 终止。

从反向代理访问 TTS 容器，使用以下地址之一：

- **`tts:8880`** —— 若反向代理作为容器运行在与 TTS 服务器**相同的 Docker 网络**中。
- **`127.0.0.1:8880`** —— 若反向代理运行在**主机上**且端口 `8880` 已发布。

面向公网时，请在 `env` 文件中设置 `TTS_API_KEY`。

## 更新 Docker 镜像

如需更新 Docker 镜像和容器，首先[下载](#下载)最新版本：

```bash
docker pull hwdsl2/kokoro-tts
```

如果镜像已是最新版本，您将看到：

```
Status: Image is up to date for hwdsl2/kokoro-tts:latest
```

否则将下载最新版本。删除并重新创建容器：

```bash
docker rm -f tts
# 然后使用相同的数据卷和端口重新运行快速开始中的 docker run 命令。
```

您下载的模型将保留在 `tts-data` 数据卷中。

## 授权协议

**注意：** 预构建镜像中包含的软件组件（如 Kokoro 及其依赖项）均受各自版权持有者所选许可证约束。使用预构建镜像时，用户有责任确保其使用方式符合镜像内所有软件的相关许可证要求。

版权所有 (C) 2026 Lin Song
本作品采用 [MIT 许可证](https://opensource.org/licenses/MIT)授权。

**Kokoro TTS** 版权归 hexgrad 所有，依据 [Apache License 2.0](https://github.com/hexgrad/kokoro/blob/main/LICENSE) 分发。

本项目是 Kokoro 的独立 Docker 封装，与 hexgrad 或 OpenAI 无关联、无背书。