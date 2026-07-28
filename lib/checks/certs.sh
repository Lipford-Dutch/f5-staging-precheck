#!/usr/bin/env bash
# check: certs – SSL certificate inventory
run_check() {
  local device=$1
  ssh_exec "$device" "tmsh list sys file ssl-cert" || return 1
}
