#!/usr/bin/env bash
# check: syncgroup – Device Service Clustering / sync status
run_check() {
  local device=$1
  ssh_exec "$device" "tmsh show cm sync-status" || return 1
}
