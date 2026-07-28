#!/usr/bin/env bash
# lib/inventory.sh – load and validate device lists
[[ -n "${_CHECK_MULTI_INVENTORY_LOADED:-}" ]] && return 0
readonly _CHECK_MULTI_INVENTORY_LOADED=1

load_and_validate_inventory() {
  local file=$1
  local -a devices=()
  local line cleaned

  [[ -f "$file" ]] || { log_error "Inventory file not found: $file"; return 2; }
  [[ -s "$file" ]] || { log_error "Inventory file is empty: $file"; return 2; }

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

    # Trim leading/trailing whitespace with Bash parameter expansion.
    cleaned=$line
    cleaned=${cleaned#"${cleaned%%[![:space:]]*}"}
    cleaned=${cleaned%"${cleaned##*[![:space:]]}"}
    # Strip an inline trailing comment (e.g. "host  # note").
    cleaned=${cleaned%%[[:space:]]#*}
    cleaned=${cleaned%"${cleaned##*[![:space:]]}"}
    [[ -z "$cleaned" ]] && continue

    # Reject anything that is not a plausible hostname/IP: shell metacharacters
    # or whitespace would be dangerous once interpolated into a remote command.
    if [[ "$cleaned" =~ [[:space:]\;\&\|\>\<\$\`\(\)\{\}\'\"] ]]; then
      log_warn "Skipping invalid inventory entry: $cleaned"
      continue
    fi

    devices+=("$cleaned")
  done < "$file"

  if (( ${#devices[@]} == 0 )); then
    log_error "No valid devices found in $file"
    return 2
  fi

  log_info "Loaded ${#devices[@]} devices from $file"
  printf '%s\n' "${devices[@]}"
}
