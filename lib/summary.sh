#!/usr/bin/env bash
# lib/summary.sh – build structured summary.json for Excel / audit consumers
[[ -n "${_CHECK_MULTI_SUMMARY_LOADED:-}" ]] && return 0
readonly _CHECK_MULTI_SUMMARY_LOADED=1

generate_summary_json() {
  local summary_file="${OUTPUT_DIR}/summary.json"
  local results_file="${RESULTS_FILE:-}"
  local tmp
  tmp=$(make_temp) || return 1

  {
    printf '{\n'
    printf '  "run_id": "%s",\n'          "$(json_escape "${AUDIT_RUN_ID:-$(date +%Y%m%d_%H%M%S)_$$}")"
    printf '  "timestamp": "%s",\n'       "$(date -Iseconds)"
    printf '  "user": "%s",\n'            "$(json_escape "${USER:-unknown}")"
    printf '  "host": "%s",\n'            "$(json_escape "$(hostname 2>/dev/null || echo unknown)")"
    printf '  "check": "%s",\n'           "$(json_escape "${CHECK_NAME:-unknown}")"
    printf '  "environment": "%s",\n'     "$(json_escape "${ENV_NAME:-unknown}")"
    printf '  "inventory": "%s",\n'       "$(json_escape "${INVENTORY_FILE:-}")"
    printf '  "version": "%s",\n'         "$(json_escape "${VERSION:-2.0.0-alpha}")"
    printf '  "dry_run": %s,\n'           "${DRY_RUN:-false}"
    printf '  "threads": %s,\n'           "${MAX_THREADS:-12}"
    printf '  "total": %s,\n'             "${PARALLEL_TOTAL:-0}"
    printf '  "success": %s,\n'           "${PARALLEL_SUCCESS:-0}"
    printf '  "failed": %s,\n'            "${PARALLEL_FAILED:-0}"

    local rate=0
    if (( ${PARALLEL_TOTAL:-0} > 0 )); then
      rate=$(awk "BEGIN {printf \"%.1f\", (${PARALLEL_SUCCESS:-0} / ${PARALLEL_TOTAL}) * 100}")
    fi
    printf '  "success_rate": %s,\n' "$rate"
    printf '  "devices": [\n'
  } > "$tmp"

  local first=true
  if [[ -f "$results_file" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -z "$line" ]] && continue
      local status device message duration=0

      status=$(echo "$line" | awk '{print $1}')
      device=$(echo "$line" | awk '{print $2}')
      message=$(echo "$line" | cut -d' ' -f3- | sed 's/^[[:space:]]*//')

      [[ -z "$device" ]] && continue

      if [[ "$first" == true ]]; then
        first=false
      else
        printf ',\n' >> "$tmp"
      fi

      printf '    {\n' >> "$tmp"
      printf '      "name": "%s",\n'     "$(json_escape "$device")"
      printf '      "status": "%s",\n'   "$(json_escape "$status")"
      printf '      "duration": %s,\n'   "$duration"
      printf '      "message": "%s"\n'   "$(json_escape "$message")"
      printf '    }' >> "$tmp"
    done < "$results_file"
  fi

  {
    printf '\n  ]\n'
    printf '}\n'
  } >> "$tmp"

  mv "$tmp" "$summary_file"
  chmod 0640 "$summary_file"
  log_info "Summary JSON written → $summary_file"
  echo "$summary_file"
}
