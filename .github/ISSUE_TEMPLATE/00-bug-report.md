---
name: Bug report
about: Tell us about a problem you are experiencing
title: ''
labels: ''
assignees: ''

---
**Checklist**

- [ ] I read the [README](https://github.com/hwdsl2/speakcrate/blob/main/README.md) or the relevant section
- [ ] I searched existing [Issues](https://github.com/hwdsl2/speakcrate/issues?q=is%3Aissue)
- [ ] This issue is about the SpeakCrate Docker image/config/API, not only Kokoro itself

<!---
If you found a reproducible bug in the upstream project itself, consider opening an issue upstream: [Kokoro](https://github.com/hexgrad/kokoro).
--->

**Describe the issue**
A clear and concise description of the problem.

**Deployment context**
- [ ] Standalone container
- [ ] Part of [self-hosted-ai-stack](https://github.com/hwdsl2/self-hosted-ai-stack)

**To Reproduce**
Steps to reproduce the behavior:

1. ...
2. ...

**Expected behavior**
A clear and concise description of what you expected to happen.

**Environment**
- Docker host OS: [e.g. Ubuntu 24.04]
- Hosting provider (if applicable): [e.g. AWS, GCP, home server]
- CPU architecture: [e.g. amd64, arm64]
- Image/tag: [e.g. `hwdsl2/kokoro-server:latest`]
- Start method: [docker run / docker compose / other]
- Published port(s): [8880]

**Configuration**
Remove secrets, API keys, tokens and private URLs before posting.

- Env file or variables changed: [kokoro.env / `-e` / compose `environment`]
- Docker run or compose changes:

**Service details**
- Voice used:
- Output format and request body size:
- Active `KOKORO_*` settings:
- Management command output, if relevant (for example `docker exec kokoro kokoro_manage --showinfo`):
- Public internet / reverse proxy / API key setup, if relevant:
- GPU/CUDA image tag and NVIDIA driver/toolkit versions, if relevant:

**Logs**
Add relevant logs with secrets removed.

```bash
docker logs kokoro
```

If using Docker Compose, you can also include:

```bash
docker compose logs kokoro
```

**Additional context**
Add any other context about the problem here.
