#!/usr/bin/env bats
# Contract tests: every check module must define run_check() and, in dry-run
# mode, complete successfully without a network.

setup() {
  cd "$BATS_TEST_DIRNAME/.." || exit 1
  SCRIPT_DIR="$PWD"
  source lib/common.sh
  source lib/ssh.sh
}

@test "every check module defines a run_check function" {
  for f in lib/checks/*.sh; do
    ( source "$f"; declare -F run_check >/dev/null ) \
      || { echo "missing run_check in $f"; return 1; }
  done
}

@test "every check module runs cleanly in dry-run mode" {
  DRY_RUN=true
  for f in lib/checks/*.sh; do
    (
      source "$f"
      run_check "device.example.com" >/dev/null 2>&1
    ) || { echo "dry-run failed for $f"; return 1; }
  done
}
