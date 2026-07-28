#!/usr/bin/env bash
# check: platform – Version, hardware, provisioned modules
run_check() {
  local device=$1
  local out
  out=$(ssh_exec "$device" "tmsh show sys version; tmsh show sys hardware; tmsh list sys provision") || return 1
  printf '%s\n' "$out"
}
