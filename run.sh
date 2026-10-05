#!/bin/bash
#
# Docker script to configure and start a Kokoro text-to-speech server
#
# DO NOT RUN THIS SCRIPT ON YOUR PC OR MAC! THIS IS ONLY MEANT TO BE RUN
# IN A CONTAINER!
#
# This file is part of Kokoro TTS Docker image, available at:
# https://github.com/hwdsl2/docker-kokoro
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

fetch_public_ip() {
  local ip_addr ip_url
  for ip_url in https://ipv4.icanhazip.com https://api.ipify.org; do
    ip_addr=$(curl -q -4fsS --max-time 10 "$ip_url" 2>/dev/null) || continue
    ip_addr=${ip_addr%$'\r'}
    [[ "$ip_addr" != *$'\n'* && "$ip_addr" != *$'\r'* ]] || continue
    if check_ip "$ip_addr"; then
      printf '%s' "$ip_addr"
      return 0
    fi
  done
  return 1
}

# Source bind-mounted env file if present (takes precedence over --env-file)
if [ -f /kokoro.env ]; then
  # shellcheck disable=SC1091
  . /kokoro.env
fi

if [ ! -f "/.dockerenv" ] && [ ! -f "/run/.containerenv" ] \
  && [ -z "$KUBERNETES_SERVICE_HOST" ] \
  && ! head -n 1 /proc/1/sched 2>/dev/null | grep -q '^run\.sh '; then
  exiterr "This script ONLY runs in a container (e.g. Docker, Podman)."
fi

KOKORO_API_KEY_WAS_SET=${KOKORO_API_KEY+x}

# Read and sanitize environment variables
KOKORO_VOICE=$(nospaces "$KOKORO_VOICE")
KOKORO_VOICE=$(noquotes "$KOKORO_VOICE")
KOKORO_SPEED=$(nospaces "$KOKORO_SPEED")
KOKORO_SPEED=$(noquotes "$KOKORO_SPEED")
KOKORO_PORT=$(nospaces "$KOKORO_PORT")
KOKORO_PORT=$(noquotes "$KOKORO_PORT")
KOKORO_LANG_CODE=$(nospaces "$KOKORO_LANG_CODE")
KOKORO_LANG_CODE=$(noquotes "$KOKORO_LANG_CODE")
KOKORO_API_KEY=$(nospaces "$KOKORO_API_KEY")
KOKORO_API_KEY=$(noquotes "$KOKORO_API_KEY")
KOKORO_LOG_LEVEL=$(nospaces "$KOKORO_LOG_LEVEL")
KOKORO_LOG_LEVEL=$(noquotes "$KOKORO_LOG_LEVEL")
KOKORO_LOCAL_ONLY=$(nospaces "$KOKORO_LOCAL_ONLY")
KOKORO_LOCAL_ONLY=$(noquotes "$KOKORO_LOCAL_ONLY")

# Apply defaults
[ -z "$KOKORO_VOICE" ]     && KOKORO_VOICE=af_heart
[ -z "$KOKORO_SPEED" ]     && KOKORO_SPEED=1.0
[ -z "$KOKORO_PORT" ]      && KOKORO_PORT=8880
[ -z "$KOKORO_LOG_LEVEL" ] && KOKORO_LOG_LEVEL=INFO

# Validate port
if ! check_port "$KOKORO_PORT"; then
  exiterr "KOKORO_PORT must be an integer between 1 and 65535."
fi

# Validate voice name (Kokoro native prefix or OpenAI alias)
case "$KOKORO_VOICE" in
  af_*|am_*|bf_*|bm_*) ;;
  ef_*|em_*) ;;
  ff_*) ;;
  hf_*|hm_*) ;;
  if_*|im_*) ;;
  jf_*|jm_*) ;;
  pf_*|pm_*) ;;
  zf_*|zm_*) ;;
  alloy|echo|fable|onyx|nova|shimmer|ash|coral|sage|verse) ;;
  *) exiterr "KOKORO_VOICE '$KOKORO_VOICE' is not recognized. Use a Kokoro voice ID (e.g. af_heart, bm_george, jf_alpha) or an OpenAI alias (e.g. alloy, nova)." ;;
esac

# Validate lang code (optional — when unset, the pipeline is auto-selected from the voice ID)
case "$KOKORO_LANG_CODE" in
  a|b|e|f|h|i|j|p|z|"") ;;
  *) exiterr "KOKORO_LANG_CODE '$KOKORO_LANG_CODE' is not recognized. Valid codes: a (American English), b (British English), e (Spanish), f (French), h (Hindi), i (Italian), j (Japanese), p (Brazilian Portuguese), z (Mandarin Chinese)." ;;
esac

# Validate speed
if ! printf '%s' "$KOKORO_SPEED" | grep -Eq '^[0-9]+(\.[0-9]+)?$'; then
  exiterr "KOKORO_SPEED must be a number (e.g. 1.0)."
fi

# Validate log level
case "$KOKORO_LOG_LEVEL" in
  DEBUG|INFO|WARNING|ERROR|CRITICAL) ;;
  *) exiterr "KOKORO_LOG_LEVEL must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL." ;;
esac

mkdir -p /var/lib/kokoro

DATA_DIR="/var/lib/kokoro"
API_KEY_FILE="${DATA_DIR}/.api_key"
AUTH_ENABLED_FILE="${DATA_DIR}/.auth_enabled"
AUTO_API_KEY_MARKER="${DATA_DIR}/.auto_api_key_created"
USAGE_STATE_DIR="${DATA_DIR}/.kokoro-usage"
USAGE_BASE_URL=${KOKORO_USAGE_BASE_URL:-https://github.com/hwdsl2/ai-stack-extras/releases/download/v1.0.0}
data_mounted=false
data_existing=false

if grep -q " ${DATA_DIR} " /proc/mounts 2>/dev/null; then
  data_mounted=true
fi
if $data_mounted && find "$DATA_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null | grep -q .; then
  data_existing=true
fi

usage_arch() {
  local arch
  arch=$(uname -m 2>/dev/null || printf 'unknown')
  case "$arch" in
    x86_64|amd64) printf 'amd64' ;;
    aarch64|arm64) printf 'arm64' ;;
    *) printf 'other' ;;
  esac
}

write_usage_state() {
  local state_file version tmp_file
  state_file=$1
  version=$2
  mkdir -p "$USAGE_STATE_DIR"
  tmp_file=$(mktemp "$USAGE_STATE_DIR/.usage.XXXXXX")
  printf '%s\n' "$version" > "$tmp_file"
  chmod 0644 "$tmp_file" 2>/dev/null || true
  mv "$tmp_file" "$state_file"
}

fetch_usage_asset() {
  local asset base_url
  asset=$1
  base_url=${USAGE_BASE_URL%/}
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --max-time 5 -o /dev/null "$base_url/$asset" >/dev/null 2>&1
  elif command -v wget >/dev/null 2>&1; then
    wget -q -T 5 -O /dev/null "$base_url/$asset" >/dev/null 2>&1
  else
    return 1
  fi
}

read_state_value() {
  [ -r "$1" ] || return 0
  tr -d '[:space:]' < "$1"
}

report_usage_counts() {
  local current_version accel arch state_file last_version action

  [ "${KOKORO_DISABLE_USAGE_COUNTS:-0}" != "1" ] || return 0
  $data_mounted || return 0

  current_version="${IMAGE_FLAVOR:-unknown}-${IMAGE_VER:-unknown}"
  case "${IMAGE_FLAVOR:-}" in
    cuda) accel=cuda ;;
    *) accel=cpu ;;
  esac
  arch=$(usage_arch)

  state_file="$USAGE_STATE_DIR/kokoro.version"
  last_version=$(read_state_value "$state_file")
  action=

  if [ -z "$last_version" ]; then
    if $data_existing; then
      action=upgrade
    else
      action=deploy
    fi
  elif [ "$last_version" != "$current_version" ]; then
    action=upgrade
  fi

  if [ -n "$action" ]; then
    if fetch_usage_asset "cu-v1-kokoro-$action-$accel-$arch"; then
      write_usage_state "$state_file" "$current_version"
    fi
  fi
}

if [ -n "$KOKORO_API_KEY" ]; then
  printf '%s' "$KOKORO_API_KEY" > "$API_KEY_FILE"
  chmod 600 "$API_KEY_FILE"
elif [ -z "$KOKORO_API_KEY_WAS_SET" ] && [ -f "$API_KEY_FILE" ]; then
  KOKORO_API_KEY=$(cat "$API_KEY_FILE")
elif [ -z "$KOKORO_API_KEY_WAS_SET" ] && $data_mounted && ! $data_existing; then
  KOKORO_API_KEY="kokoro-$(head -c 32 /dev/urandom | od -A n -t x1 | tr -d ' \n' | head -c 48)"
  printf '%s' "$KOKORO_API_KEY" > "$API_KEY_FILE"
  chmod 600 "$API_KEY_FILE"
  printf '%s\n' "true" > "$AUTO_API_KEY_MARKER"
  chmod 600 "$AUTO_API_KEY_MARKER"
fi
if [ -n "$KOKORO_API_KEY" ]; then
  printf '%s' "1" > "$AUTH_ENABLED_FILE"
else
  printf '%s' "0" > "$AUTH_ENABLED_FILE"
fi

# Determine server address for display
public_ip=$(fetch_public_ip) || public_ip=""
if check_ip "$public_ip"; then
  server_addr="$public_ip"
else
  server_addr="<server ip>"
fi

# Export all config for the Python API server
export KOKORO_VOICE
export KOKORO_SPEED
export KOKORO_PORT
export KOKORO_LANG_CODE
export KOKORO_API_KEY
export KOKORO_LOG_LEVEL
export KOKORO_LOCAL_ONLY

# Point Kokoro / HuggingFace Hub at the persistent Docker volume.
export HF_HOME=/var/lib/kokoro
export HF_HUB_CACHE=/var/lib/kokoro/hub
export HUGGINGFACE_HUB_CACHE=/var/lib/kokoro/hub

# Persist config values so kokoro_manage can read them without the env file
printf '%s' "$KOKORO_PORT"    > /var/lib/kokoro/.port
printf '%s' "$KOKORO_VOICE"   > /var/lib/kokoro/.voice
printf '%s' "$server_addr" > /var/lib/kokoro/.server_addr

echo
echo "Kokoro TTS Docker - https://github.com/hwdsl2/docker-kokoro"

if ! grep -q " /var/lib/kokoro " /proc/mounts 2>/dev/null; then
  echo
  echo "Note: /var/lib/kokoro is not mounted. Model files will be lost on"
  echo "      container removal. Mount a Docker volume at /var/lib/kokoro"
  echo "      to persist the downloaded model across container restarts."
  if [ -z "$KOKORO_API_KEY" ] && [ -z "$KOKORO_API_KEY_WAS_SET" ]; then
    echo "      API key authentication was not auto-enabled because the"
    echo "      data directory is not persistent."
  fi
elif [ -z "$KOKORO_API_KEY" ] && [ -z "$KOKORO_API_KEY_WAS_SET" ] && $data_existing; then
  echo
  echo "Warning: Existing Kokoro data was found but no API key is configured."
  echo "         Preserving no-auth behavior for backward compatibility."
  echo "         Set KOKORO_API_KEY to enable authentication."
fi

echo
echo "Starting Kokoro text-to-speech server..."
echo "  Voice:     $KOKORO_VOICE"
echo "  Speed:     $KOKORO_SPEED"
if [ -n "$KOKORO_LANG_CODE" ]; then
  echo "  Lang:      $KOKORO_LANG_CODE"
else
  echo "  Lang:      auto (derived from voice ID)"
fi
echo "  Port:      $KOKORO_PORT"
if [ -n "$KOKORO_LOCAL_ONLY" ]; then
  echo "  Mode:      local-only (no HuggingFace downloads)"
fi

if [ -z "$KOKORO_LOCAL_ONLY" ]; then
  if [ ! -d "/var/lib/kokoro/hub/models--hexgrad--Kokoro-82M" ]; then
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
  echo "Stopping Kokoro server..."
  kill "${KOKORO_PID:-}" 2>/dev/null
  wait "${KOKORO_PID:-}" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

# Start the FastAPI server in the background
cd /opt/src && python3 /opt/src/api_server.py &
KOKORO_PID=$!

# Wait for the server to become ready.
# Allow up to 300 seconds — first-run model download can take several minutes.
wait_for_server() {
  local i=0
  while [ "$i" -lt 300 ]; do
    if ! kill -0 "$KOKORO_PID" 2>/dev/null; then
      return 1
    fi
    if curl -sf "http://127.0.0.1:${KOKORO_PORT}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  return 1
}

if ! wait_for_server; then
  if ! kill -0 "$KOKORO_PID" 2>/dev/null; then
    echo "Error: Kokoro TTS server failed to start. Check the container logs for details." >&2
  else
    echo "Error: Kokoro TTS server did not become ready within 300 seconds." >&2
    kill "$KOKORO_PID" 2>/dev/null
  fi
  exit 1
fi

report_usage_counts

echo
echo "==========================================================="
echo " Kokoro text-to-speech server is ready"
echo "==========================================================="
echo " Voice:    $KOKORO_VOICE"
echo " Endpoint: http://${server_addr}:${KOKORO_PORT}"
echo "==========================================================="
echo
echo "Synthesize speech:"
echo "  curl http://${server_addr}:${KOKORO_PORT}/v1/audio/speech \\"
if [ -n "$KOKORO_API_KEY" ]; then
  echo "    -H \"Authorization: Bearer <api-key>\" \\"
fi
echo "    -H \"Content-Type: application/json\" \\"
echo "    -d '{\"model\":\"tts-1\",\"input\":\"Hello world\",\"voice\":\"af_heart\"}' \\"
echo "    --output speech.mp3"
echo
if [ -n "$KOKORO_API_KEY" ]; then
  echo "API key authentication is enabled."
  echo "Replace <api-key> with the key from: docker exec <container> kokoro_manage --getkey"
  echo
fi
echo "Interactive API docs: http://${server_addr}:${KOKORO_PORT}/docs"
echo
echo "To set up HTTPS, see: Using a reverse proxy"
echo "  https://github.com/hwdsl2/docker-kokoro#using-a-reverse-proxy"
echo
echo "Setup complete."
echo

# Wait for the server process to exit
wait "$KOKORO_PID"
