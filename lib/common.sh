#!/usr/bin/env bash
# lib/common.sh – logging, colours, utilities, temp files, error handling
[[ -n "${_CHECK_MULTI_COMMON_LOADED:-}" ]] && return 0
readonly _CHECK_MULTI_COMMON_LOADED=1

# Colour codes are emitted only when stdout is a TTY (and NO_COLOR is unset,
# per https://no-color.org/). These are consumed across sourced modules and
# bin/check_multi, so shellcheck cannot see every use.
# shellcheck disable=SC2034
if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  RED=$'\033[0;31m'; YEL=$'\033[0;33m'; GRN=$'\033[0;32m'
  CYN=$'\033[0;36m'; BLD=$'\033[1m'; RST=$'\033[0m'
else
  RED=''; YEL=''; GRN=''; CYN=''; BLD=''; RST=''
fi

log_info()  { echo -e "${CYN}[INFO]${RST}  $(date +%H:%M:%S) $*" >&2; }
log_warn()  { echo -e "${YEL}[WARN]${RST}  $(date +%H:%M:%S) $*" >&2; }
log_error() { echo -e "${RED}[ERROR]${RST} $(date +%H:%M:%S) $*" >&2; }
log_ok()    { echo -e "${GRN}[OK]${RST}    $(date +%H:%M:%S) $*" >&2; }
log_debug() {
  [[ ${VERBOSE:-false} == true ]] || return 0
  echo -e "[DEBUG] $(date +%H:%M:%S) $*" >&2
}

die() { log_error "$*"; exit 1; }

# Temporary files are tracked in an on-disk manifest rather than a shell array.
# make_temp is almost always invoked via command substitution — `t=$(make_temp)`
# — which runs in a subshell, so an in-memory array would never propagate back to
# the parent that installs the cleanup trap. A manifest file is shared across
# subshells (including the parallel worker subshells), so every temp file is
# recorded and reliably removed on exit.
: "${TEMP_MANIFEST:=}"
_CLEANUP_DONE=0

_ensure_temp_manifest() {
  if [[ -z "${TEMP_MANIFEST}" ]]; then
    TEMP_MANIFEST="$(mktemp -t "check_multi.manifest.XXXXXX" 2>/dev/null || echo "/tmp/check_multi.manifest.$$")"
    export TEMP_MANIFEST
  fi
}

make_temp() {
  local tmp mode
  _ensure_temp_manifest

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

  # Single-line appends stay within PIPE_BUF, so concurrent workers do not
  # interleave partial paths.
  printf '%s\n' "$tmp" >> "$TEMP_MANIFEST" 2>/dev/null || true
  printf '%s\n' "$tmp"
}

cleanup_temp_files() {
  (( _CLEANUP_DONE )) && return 0
  _CLEANUP_DONE=1

  [[ -n "${TEMP_MANIFEST}" && -f "${TEMP_MANIFEST}" ]] || return 0

  local f
  while IFS= read -r f; do
    [[ -n "$f" && -e "$f" ]] || continue
    rm -f -- "$f" 2>/dev/null || true
  done < "${TEMP_MANIFEST}"

  rm -f -- "${TEMP_MANIFEST}" 2>/dev/null || true
}

register_temp_cleanup() {
  _ensure_temp_manifest
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
