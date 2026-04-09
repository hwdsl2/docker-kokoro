#!/bin/bash
#
# Docker script to configure and start a Kokoro text-to-speech server
#
# DO NOT RUN THIS SCRIPT ON YOUR PC OR MAC! THIS IS ONLY MEANT TO BE RUN
# IN A CONTAINER!
#
# This file is part of Kokoro TTS Docker image, available at:
# https://github.com/hwdsl2/docker-tts
#
# Copyright (C) 2026 Lin Song <linsongui@gmail.com>
#
# This work is licensed under the MIT License
# See: https://opensource.org/licenses/MIT

export PATH="/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

exiterr()  { echo "Error: $1" >&2; exit 1; }
nospaces() { printf '%s' "$1" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'; }
noquotes() { printf '%s' "$1" | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/"; }

check_port() {
  printf '%s' "$1" | tr -d '\n' | grep -Eq '^[0-9]+$' \
  && [ "$1" -ge 1 ] && [ "$1" -le 65535 ]
}

check_ip() {
  IP_REGEX='^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$'
  printf '%s' "$1" | tr -d '\n' | grep -Eq "$IP_REGEX"
}

# Source bind-mounted env file if present (takes precedence over --env-file)
if [ -f /tts.env ]; then
  # shellcheck disable=SC1091
  . /tts.env
fi

if [ ! -f "/.dockerenv" ] && [ ! -f "/run/.containerenv" ] \
  && [ -z "$KUBERNETES_SERVICE_HOST" ] \
  && ! head -n 1 /proc/1/sched 2>/dev/null | grep -q '^run\.sh '; then
  exiterr "This script ONLY runs in a container (e.g. Docker, Podman)."
fi

# Read and sanitize environment variables
TTS_VOICE=$(nospaces "$TTS_VOICE")
TTS_VOICE=$(noquotes "$TTS_VOICE")
TTS_SPEED=$(nospaces "$TTS_SPEED")
TTS_SPEED=$(noquotes "$TTS_SPEED")
TTS_PORT=$(nospaces "$TTS_PORT")
TTS_PORT=$(noquotes "$TTS_PORT")
TTS_LANG_CODE=$(nospaces "$TTS_LANG_CODE")
TTS_LANG_CODE=$(noquotes "$TTS_LANG_CODE")
TTS_API_KEY=$(nospaces "$TTS_API_KEY")
TTS_API_KEY=$(noquotes "$TTS_API_KEY")
TTS_LOG_LEVEL=$(nospaces "$TTS_LOG_LEVEL")
TTS_LOG_LEVEL=$(noquotes "$TTS_LOG_LEVEL")
TTS_LOCAL_ONLY=$(nospaces "$TTS_LOCAL_ONLY")
TTS_LOCAL_ONLY=$(noquotes "$TTS_LOCAL_ONLY")

# Apply defaults
[ -z "$TTS_VOICE" ]     && TTS_VOICE=af_heart
[ -z "$TTS_SPEED" ]     && TTS_SPEED=1.0
[ -z "$TTS_PORT" ]      && TTS_PORT=8880
[ -z "$TTS_LANG_CODE" ] && TTS_LANG_CODE=a
[ -z "$TTS_LOG_LEVEL" ] && TTS_LOG_LEVEL=INFO

# Validate port
if ! check_port "$TTS_PORT"; then
  exiterr "TTS_PORT must be an integer between 1 and 65535."
fi

# Validate voice name (Kokoro native prefix or OpenAI alias)
case "$TTS_VOICE" in
  af_*|am_*|bf_*|bm_*) ;;
  alloy|echo|fable|onyx|nova|shimmer|ash|coral|sage|verse) ;;
  *) exiterr "TTS_VOICE '$TTS_VOICE' is not recognized. Use a Kokoro voice ID (e.g. af_heart, bm_george) or an OpenAI alias (e.g. alloy, nova)." ;;
esac

# Validate lang code
case "$TTS_LANG_CODE" in
  a|b) ;;
  *) exiterr "TTS_LANG_CODE must be 'a' (American English) or 'b' (British English)." ;;
esac

# Validate speed
if ! printf '%s' "$TTS_SPEED" | grep -Eq '^[0-9]+(\.[0-9]+)?$'; then
  exiterr "TTS_SPEED must be a number (e.g. 1.0)."
fi

# Validate log level
case "$TTS_LOG_LEVEL" in
  DEBUG|INFO|WARNING|ERROR|CRITICAL) ;;
  *) exiterr "TTS_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL." ;;
esac

mkdir -p /var/lib/tts

# Determine server address for display
public_ip=$(curl -s --max-time 10 http://ipv4.icanhazip.com 2>/dev/null || true)
check_ip "$public_ip" || public_ip=$(curl -s --max-time 10 http://ip1.dynupdate.no-ip.com 2>/dev/null || true)
if check_ip "$public_ip"; then
  server_addr="$public_ip"
else
  server_addr="<server ip>"
fi

# Export all config for the Python API server
export TTS_VOICE
export TTS_SPEED
export TTS_PORT
export TTS_LANG_CODE
export TTS_API_KEY
export TTS_LOG_LEVEL
export TTS_LOCAL_ONLY
# Point Kokoro / HuggingFace Hub at the persistent Docker volume
export HF_HOME=/var/lib/tts

# Persist config values so tts_manage can read them without the env file
printf '%s' "$TTS_PORT"    > /var/lib/tts/.port
printf '%s' "$TTS_VOICE"   > /var/lib/tts/.voice
printf '%s' "$server_addr" > /var/lib/tts/.server_addr

echo
echo "Kokoro TTS Docker - https://github.com/hwdsl2/docker-tts"

if ! grep -q " /var/lib/tts " /proc/mounts 2>/dev/null; then
  echo
  echo "Note: /var/lib/tts is not mounted. Model files will be lost on"
  echo "      container removal. Mount a Docker volume at /var/lib/tts"
  echo "      to persist the downloaded model across container restarts."
fi

echo
echo "Starting Kokoro TTS server..."
echo "  Voice:     $TTS_VOICE"
echo "  Speed:     $TTS_SPEED"
echo "  Lang:      $TTS_LANG_CODE"
echo "  Port:      $TTS_PORT"
if [ -n "$TTS_LOCAL_ONLY" ]; then
  echo "  Mode:      local-only (no HuggingFace downloads)"
fi

if [ -z "$TTS_LOCAL_ONLY" ]; then
  if [ ! -d "/var/lib/tts/models--hexgrad--Kokoro-82M" ]; then
    echo
    echo "Note: Kokoro model not found in cache. It will be downloaded"
    echo "      from HuggingFace on first start (~320 MB)."
  fi
fi
echo

# Graceful shutdown — registered before starting the server so any SIGTERM
# received during the model-download startup phase is handled cleanly.
cleanup() {
  echo
  echo "Stopping Kokoro TTS server..."
  kill "${TTS_PID:-}" 2>/dev/null
  wait "${TTS_PID:-}" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

# Start the FastAPI server in the background
cd /opt/src && python3 /opt/src/api_server.py &
TTS_PID=$!

# Wait for the server to become ready.
# Allow up to 300 seconds — first-run model download can take several minutes.
wait_for_server() {
  local i=0
  while [ "$i" -lt 300 ]; do
    if ! kill -0 "$TTS_PID" 2>/dev/null; then
      return 1
    fi
    if curl -sf "http://127.0.0.1:${TTS_PORT}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}

if ! wait_for_server; then
  if ! kill -0 "$TTS_PID" 2>/dev/null; then
    echo "Error: Kokoro TTS server failed to start. Check the container logs for details." >&2
  else
    echo "Error: Kokoro TTS server did not become ready within 300 seconds." >&2
    kill "$TTS_PID" 2>/dev/null
  fi
  exit 1
fi

echo
echo "==========================================================="
echo " Kokoro TTS server is ready"
echo "==========================================================="
echo " Voice:    $TTS_VOICE"
echo " Endpoint: http://${server_addr}:${TTS_PORT}"
echo "==========================================================="
echo
echo "Synthesize speech:"
echo "  curl http://${server_addr}:${TTS_PORT}/v1/audio/speech \\"
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"model\":\"tts-1\",\"input\":\"Hello world\",\"voice\":\"af_heart\"}' \\"
echo "    --output speech.mp3"
echo
if [ -n "$TTS_API_KEY" ]; then
  echo "API key authentication is enabled."
  echo "Include header:  -H \"Authorization: Bearer \$TTS_API_KEY\""
  echo
fi
echo "Interactive API docs: http://${server_addr}:${TTS_PORT}/docs"
echo
echo "To set up HTTPS, see: Using a reverse proxy"
echo "  https://github.com/hwdsl2/docker-tts#using-a-reverse-proxy"
echo
echo "Setup complete."
echo

# Wait for the server process to exit
wait "$TTS_PID"