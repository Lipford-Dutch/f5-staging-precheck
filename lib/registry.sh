#!/usr/bin/env bash
# lib/registry.sh – discovery of pluggable check modules.
# A "check" is any lib/checks/<name>.sh that defines a run_check() function.
[[ -n "${_CHECK_MULTI_REGISTRY_LOADED:-}" ]] && return 0
readonly _CHECK_MULTI_REGISTRY_LOADED=1

# Print every available check name, one per line, sorted.
list_available_checks() {
  local dir="${SCRIPT_DIR}/lib/checks" f name
  [[ -d "$dir" ]] || return 0
  for f in "$dir"/*.sh; do
    [[ -e "$f" ]] || continue
    name="$(basename "$f" .sh)"
    printf '%s\n' "$name"
  done | sort
}

# True when a name is a syntactically valid check identifier. Restricting to
# [A-Za-z0-9_-] prevents path traversal (e.g. "../common") from sourcing files
# outside lib/checks/.
is_valid_check_name() {
  [[ ${1:-} =~ ^[A-Za-z0-9_-]+$ ]]
}

# True when a check module file exists for the given (validated) name.
check_module_exists() {
  local name=${1:-}
  is_valid_check_name "$name" || return 1
  [[ -f "${SCRIPT_DIR}/lib/checks/${name}.sh" ]]
}

# Print up to three check names similar to $1 (substring match either way),
# used to power "did you mean…?" hints on a mistyped check name.
suggest_check() {
  local target=${1:-} c
  [[ -n "$target" ]] || return 0
  while IFS= read -r c; do
    if [[ "$c" == *"$target"* || "$target" == *"$c"* ]]; then
      printf '%s\n' "$c"
    fi
  done < <(list_available_checks) | head -3
}
