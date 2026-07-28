#!/usr/bin/env bash
# check: license – Licence status and service-check date
# Surfaces expired/expiring licences and enabled feature modules before an
# upgrade or migration relies on them.
run_check() {
  local device=$1
  ssh_exec "$device" "tmsh show sys license" || return 1
}
