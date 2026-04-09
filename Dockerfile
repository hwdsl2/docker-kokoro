#
# Copyright (C) 2026 Lin Song <linsongui@gmail.com>
#
# This work is licensed under the MIT License
# See: https://opensource.org/licenses/MIT

FROM python:3.12-slim

WORKDIR /opt/src

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# libsndfile1 is required by soundfile for audio encoding.
# ffmpeg is used for mp3/aac/opus output format conversion.
# Note: ffmpeg from Debian repos is licensed under LGPL 2.1+/GPL 2+.
# See: https://ffmpeg.org/legal.html
RUN set -x \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl ffmpeg libsndfile1 \
    && python3 -m venv /opt/venv \
    && ARCH=$(uname -m) \
    && if [ "$ARCH" = "x86_64" ]; then \
         pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu; \
       else \
         pip install --no-cache-dir torch; \
       fi \
    && pip install --no-cache-dir \
         "kokoro>=0.9" \
         soundfile \
         fastapi \
         "uvicorn[standard]" \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && find /opt/venv -name '*.pyi' -delete \
    && { find /opt/venv -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true; } \
    && mkdir -p /var/lib/tts

COPY ./run.sh /opt/src/run.sh
COPY ./manage.sh /opt/src/manage.sh
COPY ./api_server.py /opt/src/api_server.py
COPY ./LICENSE.md /opt/src/LICENSE.md
RUN chmod 755 /opt/src/run.sh /opt/src/manage.sh \
    && ln -s /opt/src/manage.sh /usr/local/bin/tts_manage

EXPOSE 8880/tcp
VOLUME ["/var/lib/tts"]
CMD ["/opt/src/run.sh"]

ARG BUILD_DATE
ARG VERSION
ARG VCS_REF
ENV IMAGE_VER=$BUILD_DATE

LABEL maintainer="Lin Song <linsongui@gmail.com>" \
    org.opencontainers.image.created="$BUILD_DATE" \
    org.opencontainers.image.version="$VERSION" \
    org.opencontainers.image.revision="$VCS_REF" \
    org.opencontainers.image.authors="Lin Song <linsongui@gmail.com>" \
    org.opencontainers.image.title="Kokoro TTS on Docker" \
    org.opencontainers.image.description="Docker image to run a Kokoro text-to-speech server, providing an OpenAI-compatible audio speech API." \
    org.opencontainers.image.url="https://github.com/hwdsl2/docker-tts" \
    org.opencontainers.image.source="https://github.com/hwdsl2/docker-tts" \
    org.opencontainers.image.documentation="https://github.com/hwdsl2/docker-tts"