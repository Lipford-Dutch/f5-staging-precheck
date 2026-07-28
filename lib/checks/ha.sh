#!/usr/bin/env bash
# check: ha – High-availability / failover state
# Confirms the active/standby role and failover health so changes are not
# pushed to the wrong unit of an HA pair.
run_check() {
  local device=$1
  ssh_exec "$device" "tmsh show sys failover; tmsh show cm failover-status 2>/dev/null" || return 1
}
