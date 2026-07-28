#!/usr/bin/env bash
# check: preflight – Lightweight connectivity + version check
run_check() {
  local device=$1
  ssh_test_connectivity "$device" || return 1
  ssh_exec "$device" "tmsh show sys version" || return 1
}
