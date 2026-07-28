#!/usr/bin/env bash
# check: network – Interfaces and trunks
run_check() {
  local device=$1
  ssh_exec "$device" "tmsh show net interface; tmsh show net trunk" || return 1
}
