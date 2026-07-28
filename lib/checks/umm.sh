#!/usr/bin/env bash
# check: umm – Provisioned modules
run_check() {
  local device=$1
  ssh_exec "$device" "tmsh list sys provision" || return 1
}
