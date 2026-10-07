---
name: 错误报告
about: 请使用这个模板来提交 bug
title: ''
labels: ''
assignees: ''

---
**任务列表**

- [ ] 我已阅读[自述文件](https://github.com/hwdsl2/speakcrate/blob/main/README-zh.md)或相关章节
- [ ] 我搜索了已有的 [Issues](https://github.com/hwdsl2/speakcrate/issues?q=is%3Aissue)
- [ ] 这个问题是关于 SpeakCrate Docker 镜像/配置/API，而不只是 Kokoro 本身

<!---
如果你确认问题属于上游项目本身，请考虑在相应上游项目提交 issue：[Kokoro](https://github.com/hexgrad/kokoro)。
--->

**问题描述**
使用清楚简明的语言描述这个问题。

**部署场景**
- [ ] 独立容器
- [ ] 属于 [self-hosted-ai-stack](https://github.com/hwdsl2/self-hosted-ai-stack/blob/main/README-zh.md)

**重现步骤**
重现该问题的步骤：

1. ...
2. ...

**期待的正确结果**
简要描述你期望发生的结果。

**环境**
- Docker 主机操作系统: [例如 Ubuntu 24.04]
- 服务提供商（如果适用）: [例如 AWS, GCP, 家用服务器]
- CPU 架构: [例如 amd64, arm64]
- 镜像/标签: [例如 `hwdsl2/kokoro-server:latest`]
- 启动方式: [docker run / docker compose / 其它]
- 发布的端口: [8880]

**配置**
发布前请删除 secrets、API keys、tokens 和私有 URL。

- 修改过的 env 文件或变量: [kokoro.env / `-e` / compose `environment`]
- Docker run 或 compose 修改：

**服务细节**
- 使用的语音：
- 输出格式和请求体大小：
- 当前 `KOKORO_*` 设置：
- 相关管理命令输出（例如 `docker exec kokoro kokoro_manage --showinfo`）：
- 公网访问/反向代理/API key 配置（如果相关）：
- GPU/CUDA 镜像标签和 NVIDIA driver/toolkit 版本（如果相关）：

**日志**
请添加相关日志，并删除敏感信息。

```bash
docker logs kokoro
```

如果使用 Docker Compose，也可以包含：

```bash
docker compose logs kokoro
```

**其它信息**
添加关于该问题的其它信息。
