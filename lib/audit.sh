#!/usr/bin/env bash
# lib/audit.sh – immutable run audit trail
[[ -n "${_CHECK_MULTI_AUDIT_LOADED:-}" ]] && return 0
readonly _CHECK_MULTI_AUDIT_LOADED=1

AUDIT_RUN_ID=""
AUDIT_FILE=""

start_audit_run() {
  [[ ${AUDIT_ENABLED:-true} == true ]] || return 0

  AUDIT_RUN_ID="$(date +%Y%m%d_%H%M%S)_$$"
  local audit_dir="${OUTPUT_DIR}/audit"
  mkdir -p "$audit_dir"
  chmod 0750 "$audit_dir"

  AUDIT_FILE="${audit_dir}/run_${AUDIT_RUN_ID}.json"

  cat > "$AUDIT_FILE" <<EOF
{
  "run_id": "$(json_escape "$AUDIT_RUN_ID")",
  "timestamp_start": "$(date -Iseconds)",
  "user": "$(json_escape "${USER:-unknown}")",
  "host": "$(json_escape "$(hostname 2>/dev/null || echo unknown)")",
  "check": "$(json_escape "${CHECK_NAME:-}")",
  "inventory": "$(json_escape "${INVENTORY_FILE:-}")",
  "dry_run": ${DRY_RUN:-false},
  "threads": ${MAX_THREADS:-12},
  "status": "running"
}
EOF
  chmod 0640 "$AUDIT_FILE"
  log_debug "Audit trail started: $AUDIT_FILE"
}

end_audit_run() {
  [[ ${AUDIT_ENABLED:-true} == true && -n "$AUDIT_FILE" ]] || return 0

  local status="success"
  local failed_count=${PARALLEL_FAILED:-0}
  failed_count=${failed_count//[^0-9]/}
  failed_count=${failed_count:-0}
  (( failed_count > 0 )) && status="partial_failure"

  cat > "$AUDIT_FILE" <<EOF
{
  "run_id": "$(json_escape "$AUDIT_RUN_ID")",
  "timestamp_start": "$(date -Iseconds)",
  "timestamp_end": "$(date -Iseconds)",
  "user": "$(json_escape "${USER:-unknown}")",
  "check": "$(json_escape "${CHECK_NAME:-}")",
  "inventory": "$(json_escape "${INVENTORY_FILE:-}")",
  "dry_run": ${DRY_RUN:-false},
  "threads": ${MAX_THREADS:-12},
  "devices_total": ${PARALLEL_TOTAL:-0},
  "devices_success": ${PARALLEL_SUCCESS:-0},
  "devices_failed": ${PARALLEL_FAILED:-0},
  "status": "$status"
}
EOF
  chmod 0640 "$AUDIT_FILE"
  log_info "Audit trail written: $AUDIT_FILE"
}
