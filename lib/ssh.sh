#!/usr/bin/env bash
# lib/ssh.sh – Secure, retry-capable SSH execution abstraction
[[ -n "${_CHECK_MULTI_SSH_LOADED:-}" ]] && return 0
readonly _CHECK_MULTI_SSH_LOADED=1

: "${SSH_CONNECT_TIMEOUT:=8}"
: "${SSH_COMMAND_TIMEOUT:=45}"
: "${SSH_RETRIES:=2}"
: "${SSH_BACKOFF:=3}"
: "${STRICT_HOST_KEY:=false}"
: "${USE_PASSWORD:=false}"
: "${SSH_USER:=}"
: "${DRY_RUN:=false}"
: "${VERBOSE:=false}"

_ssh_build_opts() {
  local -a opts=(
    -o "ConnectTimeout=${SSH_CONNECT_TIMEOUT}"
    -o "ServerAliveInterval=15"
    -o "ServerAliveCountMax=3"
    -o "LogLevel=ERROR"
    -o "BatchMode=yes"
  )

  if [[ "${STRICT_HOST_KEY}" == "true" ]]; then
    opts+=(-o "StrictHostKeyChecking=yes")
  else
    opts+=(-o "StrictHostKeyChecking=no")
    opts+=(-o "UserKnownHostsFile=/dev/null")
  fi

  if [[ -n "${SSH_USER}" ]]; then
    opts+=(-l "${SSH_USER}")
  fi

  SSH_OPTS=("${opts[@]}")
}

ssh_exec() {
  local host="$1"
  local remote_cmd="$2"
  local label="${3:-}"

  if [[ -z "$host" || -z "$remote_cmd" ]]; then
    log_error "ssh_exec: host and command are required"
    return 2
  fi

  if [[ "${DRY_RUN}" == "true" ]]; then
    if [[ -n "$label" ]]; then
      log_debug "DRY-RUN [${label}] → ${host}"
    else
      log_debug "DRY-RUN → ${host} : ${remote_cmd}"
    fi
    echo "DRY-RUN: ${remote_cmd}"
    return 0
  fi

  _ssh_build_opts

  local attempt=1
  local max_attempts=$(( SSH_RETRIES + 1 ))
  local rc=0
  local output=""
  local tmp_err
  tmp_err="$(make_temp)" || return 3

  while (( attempt <= max_attempts )); do
    log_debug "SSH attempt ${attempt}/${max_attempts} → ${host}"

    if [[ "${USE_PASSWORD}" == "true" ]]; then
      if [[ -z "${SSHPASS:-}" ]]; then
        log_error "USE_PASSWORD=true but SSHPASS is empty"
        rm -f "${tmp_err}"
        return 3
      fi
      # shellcheck disable=SC2029
      output=$(SSHPASS="${SSHPASS}" sshpass -e \
        ssh "${SSH_OPTS[@]}" \
        "${host}" \
        "timeout ${SSH_COMMAND_TIMEOUT} bash -c $(printf '%q' "${remote_cmd}")" \
        2>"${tmp_err}") && rc=0 || rc=$?
    else
      # shellcheck disable=SC2029
      output=$(ssh "${SSH_OPTS[@]}" \
        "${host}" \
        "timeout ${SSH_COMMAND_TIMEOUT} bash -c $(printf '%q' "${remote_cmd}")" \
        2>"${tmp_err}") && rc=0 || rc=$?
    fi

    if (( rc == 0 )); then
      printf '%s\n' "${output}"
      rm -f "${tmp_err}"
      return 0
    fi

    local err_msg
    err_msg="$(cat "${tmp_err}" 2>/dev/null || true)"

    if (( attempt < max_attempts )); then
      log_warn "SSH to ${host} failed (rc=${rc}) – retry ${attempt}/${SSH_RETRIES} in ${SSH_BACKOFF}s"
      [[ -n "${err_msg}" && "${VERBOSE}" == "true" ]] && log_debug "stderr: ${err_msg}"
      sleep "${SSH_BACKOFF}"
      (( attempt++ ))
    else
      log_error "SSH to ${host} failed after ${max_attempts} attempts (rc=${rc})"
      [[ -n "${err_msg}" ]] && log_error "Last error: ${err_msg}"
      rm -f "${tmp_err}"
      return "${rc}"
    fi
  done

  rm -f "${tmp_err}"
  return 1
}

ssh_test_connectivity() {
  local host="$1"
  ssh_exec "${host}" "echo OK" "connectivity-test"
}

ssh_run_tmsh() {
  local host="$1"
  shift
  local tmsh_args=("$@")
  local cmd="tmsh ${tmsh_args[*]}"
  ssh_exec "${host}" "${cmd}"
}

prompt_password_if_needed() {
  if [[ "${USE_PASSWORD}" != "true" ]]; then
    return 0
  fi

  if [[ -n "${SSHPASS:-}" ]]; then
    return 0
  fi

  echo -n "SSH Password (input will be hidden): "
  read -rs SSHPASS
  echo ""
  export SSHPASS

  if [[ -z "${SSHPASS}" ]]; then
    die "Password cannot be empty when password authentication is requested"
  fi
}

clear_password() {
  unset SSHPASS
  export -n SSHPASS 2>/dev/null || true
}

print_ssh_security_banner() {
  if [[ "${USE_PASSWORD}" == "true" ]]; then
    echo ""
    echo -e "${RED}${BLD}╔══════════════════════════════════════════════════════════════════════╗${RST}"
    echo -e "${RED}${BLD}║  SECURITY WARNING – PASSWORD AUTHENTICATION ENABLED                  ║${RST}"
    echo -e "${RED}${BLD}║                                                                      ║${RST}"
    echo -e "${RED}${BLD}║  sshpass is used. Credentials can appear in process lists.           ║${RST}"
    echo -e "${RED}${BLD}║  Prefer SSH public-key authentication or a secrets manager.          ║${RST}"
    echo -e "${RED}${BLD}║  This mode exists only for emergency / migration use.                ║${RST}"
    echo -e "${RED}${BLD}╚══════════════════════════════════════════════════════════════════════╝${RST}"
    echo ""
  fi

  if [[ "${STRICT_HOST_KEY}" != "true" ]]; then
    log_warn "StrictHostKeyChecking is disabled (set via environment profile to enforce)"
  fi
}
