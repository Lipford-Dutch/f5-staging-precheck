#!/usr/bin/env bash
# lib/common.sh – logging, colours, utilities, temp files, error handling
[[ -n "${_CHECK_MULTI_COMMON_LOADED:-}" ]] && return 0
readonly _CHECK_MULTI_COMMON_LOADED=1

# Colour codes are emitted only when stderr is a TTY (all logs go to stderr)
# and NO_COLOR is unset, per https://no-color.org/. init_colors is re-runnable
# so a late `--no-color` flag can disable colour after the module is sourced.
# The colour variables are consumed across other sourced modules, so the linter
# cannot see every use (hence the disable below).
# shellcheck disable=SC2034
init_colors() {
  if [[ -t 2 && -z "${NO_COLOR:-}" ]]; then
    RED=$'\033[0;31m'; YEL=$'\033[0;33m'; GRN=$'\033[0;32m'
    CYN=$'\033[0;36m'; BLD=$'\033[1m'; RST=$'\033[0m'
  else
    RED=''; YEL=''; GRN=''; CYN=''; BLD=''; RST=''
  fi
}
init_colors

log_info()  { echo -e "${CYN}[INFO]${RST}  $(date +%H:%M:%S) $*" >&2; }
log_warn()  { echo -e "${YEL}[WARN]${RST}  $(date +%H:%M:%S) $*" >&2; }
log_error() { echo -e "${RED}[ERROR]${RST} $(date +%H:%M:%S) $*" >&2; }
log_ok()    { echo -e "${GRN}[OK]${RST}    $(date +%H:%M:%S) $*" >&2; }
log_debug() {
  [[ ${VERBOSE:-false} == true ]] || return 0
  echo -e "[DEBUG] $(date +%H:%M:%S) $*" >&2
}

die() { log_error "$*"; exit 1; }

# Install a diagnostic trap that reports the failing command and line number.
# Call once from the entry point after logging is available.
install_error_trap() {
  trap '_on_error $? $LINENO "${BASH_COMMAND}"' ERR
}
_on_error() {
  local rc=$1 line=$2 cmd=$3
  log_error "Unexpected failure (rc=${rc}) at line ${line}: ${cmd}"
}

# True when the argument is a non-negative integer.
is_uint() { [[ ${1:-} =~ ^[0-9]+$ ]]; }

# require_cmd <command> [hint] – die with a friendly message if missing.
require_cmd() {
  local cmd=$1 hint=${2:-}
  command -v "$cmd" >/dev/null 2>&1 && return 0
  die "Required command not found: ${cmd}${hint:+ (${hint})}"
}

# confirm <prompt> – interactive yes/No gate.
# Honours ASSUME_YES=true; on a non-interactive stdin it refuses (returns 1)
# so unattended runs cannot silently proceed through a safety prompt.
confirm() {
  local prompt=${1:-"Proceed?"} reply
  if [[ ${ASSUME_YES:-false} == true ]]; then
    return 0
  fi
  if [[ ! -t 0 ]]; then
    log_error "Confirmation required but stdin is not a TTY; pass --yes to proceed"
    return 1
  fi
  printf '%b%s [y/N]: %b' "${YEL}" "$prompt" "${RST}" >&2
  read -r reply
  [[ $reply =~ ^[Yy]([Ee][Ss])?$ ]]
}

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
