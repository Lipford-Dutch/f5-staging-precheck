#!/usr/bin/env bash
# lib/parallel.sh – controlled parallel execution of checks
[[ -n "${_CHECK_MULTI_PARALLEL_LOADED:-}" ]] && return 0
readonly _CHECK_MULTI_PARALLEL_LOADED=1

run_parallel_checks() {
  local check_name=$1
  shift
  local -a devices=("$@")
  local total=${#devices[@]}
  local max_jobs=${MAX_THREADS:-12}
  local results_file
  local device
  local running

  results_file=$(make_temp) || return 1
  RESULTS_FILE="$results_file"
  export RESULTS_FILE

  log_info "Running '$check_name' on $total devices (max $max_jobs parallel)"

  for device in "${devices[@]}"; do
    # Throttle concurrency (ignore errors from jobs/wc under set -e)
    while true; do
      running=$(jobs -r 2>/dev/null | wc -l | tr -d '[:space:]')
      running=${running:-0}
      if (( running < max_jobs )); then
        break
      fi
      sleep 0.25
    done

    (
      if run_check "$device" >/dev/null 2>&1; then
        echo "SUCCESS $device" >> "$results_file"
      else
        echo "FAILED $device" >> "$results_file"
      fi
    ) &
  done

  wait || true

  local success failed
  success=$(grep -c '^SUCCESS' "$results_file" 2>/dev/null | head -1 | tr -d '[:space:]')
  failed=$(grep -c '^FAILED'  "$results_file" 2>/dev/null | head -1 | tr -d '[:space:]')
  success=${success:-0}
  failed=${failed:-0}

  PARALLEL_SUCCESS=$success
  PARALLEL_FAILED=$failed
  PARALLEL_TOTAL=$total
  export PARALLEL_SUCCESS PARALLEL_FAILED PARALLEL_TOTAL

  log_info "Finished: $success succeeded, $failed failed (total $total)"

  if (( failed > 0 )); then
    return 4
  fi
  return 0
}
