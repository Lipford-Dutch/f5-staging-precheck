#!/usr/bin/env bash
# check: keys – SSL key inventory
run_check() {
  local device=$1
  ssh_exec "$device" "tmsh list sys file ssl-key" || return 1
}
