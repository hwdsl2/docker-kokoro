#!/bin/bash
#
# https://github.com/hwdsl2/speakcrate
#
# Copyright (C) 2026 Lin Song <linsongui@gmail.com>
#
# This work is licensed under the MIT License
# See: https://opensource.org/licenses/MIT

export PATH="/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

KOKORO_DATA="/var/lib/kokoro"
PORT_FILE="${KOKORO_DATA}/.port"
VOICE_FILE="${KOKORO_DATA}/.voice"
SERVER_ADDR_FILE="${KOKORO_DATA}/.server_addr"
API_KEY_FILE="${KOKORO_DATA}/.api_key"
AUTH_ENABLED_FILE="${KOKORO_DATA}/.auth_enabled"

exiterr() { echo "Error: $1" >&2; exit 1; }

show_usage() {
  local exit_code="${2:-1}"
  if [ -n "$1" ]; then
    echo "Error: $1" >&2
  fi
  cat 1>&2 <<'EOF'

SpeakCrate - Server Management
https://github.com/hwdsl2/speakcrate

Usage: docker exec <container> kokoro_manage [options]

  --showinfo                           show server info (voice, endpoint, API docs)
  --showkey                            show the API key, if configured
  --getkey                             output the API key (machine-readable, no decoration)
  --listvoices                         list all available Kokoro voice IDs

  -h, --help                           show this help message and exit

Available voice IDs (Kokoro native):
  American English female: af_heart, af_aoede, af_bella, af_jessica, af_kore,
                           af_nicole, af_nova, af_river, af_sarah, af_sky, af_alloy
  American English male:   am_adam, am_michael, am_echo, am_eric, am_fenrir,
                           am_liam, am_onyx, am_puck, am_santa
  British English female:  bf_emma, bf_isabella, bf_alice, bf_lily
  British English male:    bm_george, bm_lewis, bm_daniel, bm_fable
  Japanese female:         jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro
  Japanese male:           jm_kumo
  Mandarin Chinese female: zf_xiaobei, zf_xiaoni, zf_xiaoxiao, zf_xiaoyi
  Mandarin Chinese male:   zm_yunjian, zm_yunxi, zm_yunxia, zm_yunyang
  Spanish female:          ef_dora
  Spanish male:            em_alex, em_santa
  French female:           ff_siwis
  Hindi female:            hf_alpha, hf_beta
  Hindi male:              hm_omega, hm_psi
  Italian female:          if_sara
  Italian male:            im_nicola
  Brazilian Pt female:     pf_dora
  Brazilian Pt male:       pm_alex, pm_santa

OpenAI voice aliases (mapped to Kokoro voices):
  alloy → af_alloy    echo → am_echo    fable → bm_fable
  onyx  → am_onyx     nova → af_nova    shimmer → af_bella
  ash   → am_michael  coral → af_heart  sage → af_sky  verse → bm_george

To change the active voice, set KOKORO_VOICE=<voice> in your env file and
restart the container. No model download is needed — all voices use the
same Kokoro-82M model file.

Examples:
  docker exec kokoro kokoro_manage --showinfo
  docker exec kokoro kokoro_manage --showkey
  docker exec kokoro kokoro_manage --getkey
  docker exec kokoro kokoro_manage --listvoices

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
  if [ -z "$KOKORO_PORT" ]; then
    if [ -f "$PORT_FILE" ]; then
      KOKORO_PORT=$(cat "$PORT_FILE")
    else
      KOKORO_PORT=8880
    fi
  fi

  if [ -z "$KOKORO_VOICE" ]; then
    if [ -f "$VOICE_FILE" ]; then
      KOKORO_VOICE=$(cat "$VOICE_FILE")
    else
      KOKORO_VOICE=af_heart
    fi
  fi

  if [ -f "$SERVER_ADDR_FILE" ]; then
    SERVER_ADDR=$(cat "$SERVER_ADDR_FILE")
  else
    SERVER_ADDR="<server ip>"
  fi

  if [ -f "$AUTH_ENABLED_FILE" ]; then
    KOKORO_AUTH_ENABLED=$(cat "$AUTH_ENABLED_FILE")
  fi

  if [ "$KOKORO_AUTH_ENABLED" != 0 ] && [ -z "$KOKORO_API_KEY" ] && [ -f "$API_KEY_FILE" ]; then
    KOKORO_API_KEY=$(cat "$API_KEY_FILE")
  fi

  if [ -z "$KOKORO_AUTH_ENABLED" ]; then
    if [ -n "$KOKORO_API_KEY" ]; then
      KOKORO_AUTH_ENABLED=1
    else
      KOKORO_AUTH_ENABLED=0
    fi
  fi
}

check_server() {
  if ! curl -sf "http://127.0.0.1:${KOKORO_PORT}/health" >/dev/null 2>&1; then
    exiterr "SpeakCrate server is not responding on port ${KOKORO_PORT}. Is the container fully started?"
  fi
}

parse_args() {
  show_info=0
  show_key=0
  get_key=0
  list_voices=0

  while [ "$#" -gt 0 ]; do
    case "$1" in
      --showinfo)
        show_info=1
        shift
        ;;
      --showkey)
        show_key=1
        shift
        ;;
      --getkey)
        get_key=1
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
  action_count=$((show_info + show_key + get_key + list_voices))

  if [ "$action_count" -eq 0 ]; then
    show_usage
  fi
  if [ "$action_count" -gt 1 ]; then
    show_usage "Specify only one action at a time."
  fi
}

do_show_key() {
  if [ "$KOKORO_AUTH_ENABLED" != 1 ]; then
    exiterr "API key authentication is disabled for this container."
  fi

  if [ -z "$KOKORO_API_KEY" ]; then
    if [ -f "$API_KEY_FILE" ]; then
      KOKORO_API_KEY=$(cat "$API_KEY_FILE")
    else
      exiterr "API key not found. Authentication may be disabled for this container."
    fi
  fi

  echo
  echo "==========================================================="
  echo " SpeakCrate API key"
  echo "==========================================================="
  echo "${KOKORO_API_KEY}"
  echo "==========================================================="
  echo
  echo "Use with: -H \"Authorization: Bearer ${KOKORO_API_KEY}\""
  echo
}

do_get_key() {
  if [ "$KOKORO_AUTH_ENABLED" != 1 ]; then
    exit 1
  fi

  if [ -z "$KOKORO_API_KEY" ]; then
    if [ -f "$API_KEY_FILE" ]; then
      KOKORO_API_KEY=$(cat "$API_KEY_FILE")
    else
      exit 1
    fi
  fi

  printf '%s' "$KOKORO_API_KEY"
}

do_show_info() {
  echo
  echo "==========================================================="
  echo " SpeakCrate Text-to-Speech Server"
  echo "==========================================================="
  echo " Active voice: $KOKORO_VOICE"
  echo " Endpoint:     http://${SERVER_ADDR}:${KOKORO_PORT}"
  echo "==========================================================="
  echo
  echo "API endpoints:"
  echo "  POST http://${SERVER_ADDR}:${KOKORO_PORT}/v1/audio/speech"
  echo "  GET  http://${SERVER_ADDR}:${KOKORO_PORT}/v1/voices"
  echo "  GET  http://${SERVER_ADDR}:${KOKORO_PORT}/v1/models"
  echo "  GET  http://${SERVER_ADDR}:${KOKORO_PORT}/docs     (interactive docs)"
  echo
  echo "Example synthesis:"
  echo "  curl http://${SERVER_ADDR}:${KOKORO_PORT}/v1/audio/speech \\"
  echo "    -H \"Content-Type: application/json\" \\"
  if [ "$KOKORO_AUTH_ENABLED" = 1 ]; then
    echo "    -H \"Authorization: Bearer <api-key>\" \\"
  fi
  echo "    -d '{\"model\":\"tts-1\",\"input\":\"Hello world\",\"voice\":\"af_heart\"}' \\"
  echo "    --output speech.mp3"
  if [ "$KOKORO_AUTH_ENABLED" = 1 ]; then
    echo
    echo "Use '--showkey' to display the API key."
  fi
  echo
  echo "To change the active voice:"
  echo "  Set KOKORO_VOICE=<voice_id> in your env file and restart the container."
  echo "  Run '--listvoices' to see all available voice IDs."
  echo
}

do_list_voices() {
  cat <<'EOF'

Available Kokoro voice IDs:

  American English — Female
  -------------------------
  af_heart     Warm, natural (recommended default)
  af_aoede
  af_bella     Expressive
  af_jessica   Energetic
  af_kore
  af_nicole    Friendly
  af_nova      Clear
  af_river     Calm
  af_sarah     Conversational
  af_sky       Neutral, versatile
  af_alloy     Balanced

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

  Japanese — Female
  -----------------
  jf_alpha
  jf_gongitsune
  jf_nezumi
  jf_tebukuro

  Japanese — Male
  ---------------
  jm_kumo

  Mandarin Chinese — Female
  -------------------------
  zf_xiaobei
  zf_xiaoni
  zf_xiaoxiao
  zf_xiaoyi

  Mandarin Chinese — Male
  -----------------------
  zm_yunjian
  zm_yunxi
  zm_yunxia
  zm_yunyang

  Spanish — Female
  ----------------
  ef_dora

  Spanish — Male
  --------------
  em_alex
  em_santa

  French — Female
  ---------------
  ff_siwis

  Hindi — Female
  --------------
  hf_alpha
  hf_beta

  Hindi — Male
  ------------
  hm_omega
  hm_psi

  Italian — Female
  ----------------
  if_sara

  Italian — Male
  --------------
  im_nicola

  Brazilian Portuguese — Female
  -----------------------------
  pf_dora

  Brazilian Portuguese — Male
  ---------------------------
  pm_alex
  pm_santa

OpenAI voice aliases (use these if your app sends OpenAI voice names):
  alloy → af_alloy    echo → am_echo      fable → bm_fable
  onyx  → am_onyx     nova → af_nova      shimmer → af_bella
  ash   → am_michael  coral → af_heart    sage → af_sky
  verse → bm_george

Notes:
  - All voices use the same Kokoro-82M model (~320 MB, cached in /var/lib/kokoro).
  - No re-download is required when switching voices.
  - To change the default voice, set KOKORO_VOICE=<voice_id> in your env file
    and restart the container.
  - Set KOKORO_LANG_CODE to match the language of your chosen voice:
      a=American English, b=British English, e=Spanish, f=French,
      h=Hindi, i=Italian, j=Japanese, p=Brazilian Portuguese, z=Mandarin Chinese
  - When KOKORO_LANG_CODE is unset, it is auto-derived from the voice ID prefix.

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

if [ "$show_key" = 1 ]; then
  do_show_key
  exit 0
fi

if [ "$get_key" = 1 ]; then
  do_get_key
  exit 0
fi

if [ "$list_voices" = 1 ]; then
  do_list_voices
  exit 0
fi
