#!/usr/bin/env bash
# lib/config.sh – load YAML defaults + environment profiles
[[ -n "${_CHECK_MULTI_CONFIG_LOADED:-}" ]] && return 0
readonly _CHECK_MULTI_CONFIG_LOADED=1

load_config() {
  local cfg=${1:-}
  [[ -f "$cfg" ]] || { log_warn "Config file not found: $cfg – using built-in defaults"; return 0; }

  if ! command -v yq >/dev/null 2>&1; then
    log_warn "yq not found – YAML config disabled, using built-in defaults"
    return 0
  fi

  MAX_THREADS=$(yq -r '.max_threads // 12' "$cfg")
  SSH_CONNECT_TIMEOUT=$(yq -r '.ssh.connect_timeout // 8' "$cfg")
  SSH_COMMAND_TIMEOUT=$(yq -r '.ssh.command_timeout // 45' "$cfg")
  SSH_RETRIES=$(yq -r '.ssh.retries // 2' "$cfg")
  SSH_BACKOFF=$(yq -r '.ssh.backoff_seconds // 3' "$cfg")
  STRICT_HOST_KEY=$(yq -r '.ssh.strict_host_key_checking // false' "$cfg")
  OUTPUT_BASE=$(yq -r '.output.base_dir // "./results"' "$cfg")
  AUDIT_ENABLED=$(yq -r '.audit.enabled // true' "$cfg")

  export MAX_THREADS SSH_CONNECT_TIMEOUT SSH_COMMAND_TIMEOUT \
         SSH_RETRIES SSH_BACKOFF STRICT_HOST_KEY OUTPUT_BASE AUDIT_ENABLED
}

load_environment_profile() {
  local env_name=${1:-lab}
  local profile="${SCRIPT_DIR}/config/environments/${env_name}.yaml"

  [[ -f "$profile" ]] || { log_debug "No profile for environment '$env_name'"; return 0; }

  if ! command -v yq >/dev/null 2>&1; then
    return 0
  fi

  local v
  v=$(yq -r '.max_threads // ""' "$profile")
  [[ -n "$v" && "$v" != "null" ]] && MAX_THREADS=$v

  v=$(yq -r '.ssh.strict_host_key_checking // ""' "$profile")
  [[ -n "$v" && "$v" != "null" ]] && STRICT_HOST_KEY=$v

  v=$(yq -r '.ssh.retries // ""' "$profile")
  [[ -n "$v" && "$v" != "null" ]] && SSH_RETRIES=$v

  export MAX_THREADS STRICT_HOST_KEY SSH_RETRIES
  log_info "Loaded environment profile: $env_name"
}
