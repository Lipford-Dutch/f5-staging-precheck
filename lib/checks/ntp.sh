#!/usr/bin/env bash
# check: ntp – NTP configuration and clock synchronisation
# Clock skew breaks certificate validation, HA heartbeats and log correlation,
# so verifying NTP before staging changes avoids a common class of failures.
run_check() {
  local device=$1
  ssh_exec "$device" "tmsh list sys ntp; tmsh show sys ntp status 2>/dev/null || ntpq -pn 2>/dev/null" || return 1
}
