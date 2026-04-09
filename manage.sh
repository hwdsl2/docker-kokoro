#!/bin/bash
#
# https://github.com/hwdsl2/docker-tts
#
# Copyright (C) 2026 Lin Song <linsongui@gmail.com>
#
# This work is licensed under the MIT License
# See: https://opensource.org/licenses/MIT

export PATH="/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

TTS_DATA="/var/lib/tts"
PORT_FILE="${TTS_DATA}/.port"
VOICE_FILE="${TTS_DATA}/.voice"
SERVER_ADDR_FILE="${TTS_DATA}/.server_addr"

exiterr() { echo "Error: $1" >&2; exit 1; }

show_usage() {
  local exit_code="${2:-1}"
  if [ -n "$1" ]; then
    echo "Error: $1" >&2
  fi
  cat 1>&2 <<'EOF'

Kokoro TTS Docker - Server Management
https://github.com/hwdsl2/docker-tts

Usage: docker exec <container> tts_manage [options]

  --showinfo                           show server info (voice, endpoint, API docs)
  --listvoices                         list all available Kokoro voice IDs

  -h, --help                           show this help message and exit

Available voice IDs (Kokoro native):
  American female: af_heart, af_bella, af_nova, af_sky, af_sarah,
                   af_nicole, af_alloy, af_jessica, af_river
  American male:   am_adam, am_michael, am_echo, am_eric, am_fenrir,
                   am_liam, am_onyx, am_puck, am_santa
  British female:  bf_emma, bf_isabella, bf_alice, bf_lily
  British male:    bm_george, bm_lewis, bm_daniel, bm_fable

OpenAI voice aliases (mapped to Kokoro voices):
  alloy → af_alloy    echo → am_echo    fable → bm_fable
  onyx  → am_onyx     nova → af_nova    shimmer → af_bella
  ash   → am_michael  coral → af_heart  sage → af_sky  verse → bm_george

To change the active voice, set TTS_VOICE=<voice> in your env file and
restart the container. No model download is needed — all voices use the
same Kokoro-82M model file.

Examples:
  docker exec tts tts_manage --showinfo
  docker exec tts tts_manage --listvoices

EOF
  exit "$exit_code"
}

check_container() {
  if [ ! -f "/.dockerenv" ] && [ ! -f "/run/.containerenv" ] \
    && [ -z "$KUBERNETES_SERVICE_HOST" ] \
    && ! head -n 1 /proc/1/sched 2>/dev/null | grep -q '^run\.sh '; then
    exiterr "This script must be run inside a container (e.g. Docker, Podman)."
  fi
}

load_config() {
  if [ -z "$TTS_PORT" ]; then
    if [ -f "$PORT_FILE" ]; then
      TTS_PORT=$(cat "$PORT_FILE")
    else
      TTS_PORT=8880
    fi
  fi

  if [ -z "$TTS_VOICE" ]; then
    if [ -f "$VOICE_FILE" ]; then
      TTS_VOICE=$(cat "$VOICE_FILE")
    else
      TTS_VOICE=af_heart
    fi
  fi

  if [ -f "$SERVER_ADDR_FILE" ]; then
    SERVER_ADDR=$(cat "$SERVER_ADDR_FILE")
  else
    SERVER_ADDR="<server ip>"
  fi
}

check_server() {
  if ! curl -sf "http://127.0.0.1:${TTS_PORT}/health" >/dev/null 2>&1; then
    exiterr "Kokoro TTS server is not responding on port ${TTS_PORT}. Is the container fully started?"
  fi
}

parse_args() {
  show_info=0
  list_voices=0

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --showinfo)
        show_info=1
        shift
        ;;
      --listvoices)
        list_voices=1
        shift
        ;;
      -h|--help)
        show_usage "" 0
        ;;
      *)
        show_usage "Unknown parameter: $1"
        ;;
    esac
  done
}

check_args() {
  local action_count
  action_count=$((show_info + list_voices))

  if [ "$action_count" -eq 0 ]; then
    show_usage
  fi
  if [ "$action_count" -gt 1 ]; then
    show_usage "Specify only one action at a time."
  fi
}

do_show_info() {
  echo
  echo "==========================================================="
  echo " Kokoro TTS Server"
  echo "==========================================================="
  echo " Active voice: $TTS_VOICE"
  echo " Endpoint:     http://${SERVER_ADDR}:${TTS_PORT}"
  echo "==========================================================="
  echo
  echo "API endpoints:"
  echo "  POST http://${SERVER_ADDR}:${TTS_PORT}/v1/audio/speech"
  echo "  GET  http://${SERVER_ADDR}:${TTS_PORT}/v1/voices"
  echo "  GET  http://${SERVER_ADDR}:${TTS_PORT}/v1/models"
  echo "  GET  http://${SERVER_ADDR}:${TTS_PORT}/docs     (interactive docs)"
  echo
  echo "Example synthesis:"
  echo "  curl http://${SERVER_ADDR}:${TTS_PORT}/v1/audio/speech \\"
  echo "    -H \"Content-Type: application/json\" \\"
  echo "    -d '{\"model\":\"tts-1\",\"input\":\"Hello world\",\"voice\":\"af_heart\"}' \\"
  echo "    --output speech.mp3"
  echo
  echo "To change the active voice:"
  echo "  Set TTS_VOICE=<voice_id> in your env file and restart the container."
  echo "  Run '--listvoices' to see all available voice IDs."
  echo
}

do_list_voices() {
  cat <<'EOF'

Available Kokoro voice IDs:

  American English — Female
  -------------------------
  af_heart     Warm, natural (recommended default)
  af_bella     Expressive
  af_nova      Clear
  af_sky       Neutral, versatile
  af_sarah     Conversational
  af_nicole    Friendly
  af_alloy     Balanced
  af_jessica   Energetic
  af_river     Calm

  American English — Male
  -----------------------
  am_adam      Deep
  am_michael   Clear
  am_echo      Neutral
  am_eric      Authoritative
  am_fenrir    Distinctive
  am_liam      Conversational
  am_onyx      Rich
  am_puck      Expressive
  am_santa     Warm

  British English — Female
  ------------------------
  bf_emma      Clear, professional
  bf_isabella  Warm
  bf_alice     Crisp
  bf_lily      Soft

  British English — Male
  ----------------------
  bm_george    Authoritative
  bm_lewis     Smooth
  bm_daniel    Calm
  bm_fable     Expressive

OpenAI voice aliases (use these if your app sends OpenAI voice names):
  alloy → af_alloy    echo → am_echo      fable → bm_fable
  onyx  → am_onyx     nova → af_nova      shimmer → af_bella
  ash   → am_michael  coral → af_heart    sage → af_sky
  verse → bm_george

Notes:
  - All voices use the same Kokoro-82M model (~320 MB, cached in /var/lib/tts).
  - No re-download is required when switching voices.
  - To change the default voice, set TTS_VOICE=<voice_id> in your env file
    and restart the container.
  - British voices (bf_*, bm_*) work best with TTS_LANG_CODE=b.
    American voices (af_*, am_*) work best with TTS_LANG_CODE=a (default).

EOF
}

check_container
load_config
parse_args "$@"
check_args

if [ "$show_info" = 1 ]; then
  check_server
  do_show_info
  exit 0
fi

if [ "$list_voices" = 1 ]; then
  do_list_voices
  exit 0
fi