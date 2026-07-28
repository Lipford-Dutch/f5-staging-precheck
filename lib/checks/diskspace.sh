#!/usr/bin/env bash
# check: diskspace – Filesystem utilisation
# A full /var or /config filesystem will fail a UCS save or software install,
# so capturing utilisation is a key pre-flight for any change window.
run_check() {
  local device=$1
  ssh_exec "$device" "df -h /var /config /shared /usr 2>/dev/null; tmsh show sys disk 2>/dev/null" || return 1
}
