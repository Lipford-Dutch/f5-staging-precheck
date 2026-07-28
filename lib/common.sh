#!/usr/bin/env bash
# lib/common.sh – logging, colours, utilities, temp files, error handling
[[ -n "${_CHECK_MULTI_COMMON_LOADED:-}" ]] && return 0
readonly _CHECK_MULTI_COMMON_LOADED=1

if [[ -t 1 ]]; then
  RED='\033[0;31m'; YEL='\033[0;33m'; GRN='\033[0;32m'
  CYN='\033[0;36m'; BLD='\033[1m'; RST='\033[0m'
else
  RED= YEL= GRN= CYN= BLD= RST=
fi

log_info()  { echo -e "${CYN}[INFO]${RST}  $(date +%H:%M:%S) $*" >&2; }
log_warn()  { echo -e "${YEL}[WARN]${RST}  $(date +%H:%M:%S) $*" >&2; }
log_error() { echo -e "${RED}[ERROR]${RST} $(date +%H:%M:%S) $*" >&2; }
log_ok()    { echo -e "${GRN}[OK]${RST}    $(date +%H:%M:%S) $*" >&2; }
log_debug() { [[ ${VERBOSE:-false} == true ]] && echo -e "[DEBUG] $(date +%H:%M:%S) $*" >&2 || true; }

die() { log_error "$*"; exit 1; }

declare -a TEMP_FILES=()
_CLEANUP_DONE=0

make_temp() {
  local tmp mode

  if ! tmp=$(mktemp -t "check_multi.XXXXXX" 2>/dev/null); then
    tmp="/tmp/check_multi.${RANDOM}.${RANDOM}.$$"
    if ! : > "$tmp" 2>/dev/null; then
      log_error "Failed to create temporary file"
      return 1
    fi
  fi

  if ! chmod 0600 "$tmp" 2>/dev/null; then
    log_error "Failed to set mode 0600 on $tmp"
    rm -f -- "$tmp"
    return 1
  fi

  mode=$(stat -c '%a' "$tmp" 2>/dev/null || stat -f '%Lp' "$tmp" 2>/dev/null || echo "unknown")
  if [[ "$mode" != "600" ]]; then
    log_error "Mode verification failed on $tmp (got $mode, expected 600)"
    rm -f -- "$tmp"
    return 1
  fi

  TEMP_FILES+=("$tmp")
  printf '%s\n' "$tmp"
}

cleanup_temp_files() {
  (( _CLEANUP_DONE )) && return 0
  _CLEANUP_DONE=1

  local f
  for f in "${TEMP_FILES[@]+"${TEMP_FILES[@]}"}"; do
    [[ -n "$f" && -e "$f" ]] && rm -f -- "$f" 2>/dev/null || true
  done
  TEMP_FILES=()
}

register_temp_cleanup() {
  trap cleanup_temp_files EXIT
  trap 'cleanup_temp_files; exit 130' INT
  trap 'cleanup_temp_files; exit 143' TERM
  trap 'cleanup_temp_files; exit 129' HUP
}

json_escape() {
  local s=${1:-}
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/\\n}
  s=${s//$'\r'/\\r}
  s=${s//$'\t'/\\t}
  printf '%s' "$s"
}
