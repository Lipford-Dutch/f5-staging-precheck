#!/usr/bin/env bats
# Unit tests for lib/registry.sh check discovery.

setup() {
  cd "$BATS_TEST_DIRNAME/.." || exit 1
  SCRIPT_DIR="$PWD"
  source lib/common.sh
  source lib/registry.sh
}

@test "list_available_checks returns known checks, sorted and unique" {
  run list_available_checks
  [ "$status" -eq 0 ]
  [[ "$output" == *"platform"* ]]
  [[ "$output" == *"preflight"* ]]
  # Sorted: certs precedes platform in the output.
  certs_line=$(printf '%s\n' "$output" | grep -n '^certs$' | cut -d: -f1)
  plat_line=$(printf '%s\n' "$output" | grep -n '^platform$' | cut -d: -f1)
  [ "$certs_line" -lt "$plat_line" ]
}

@test "check_module_exists is true for a real check" {
  check_module_exists platform
}

@test "check_module_exists is false for an unknown check" {
  ! check_module_exists definitely_not_a_check
}

@test "check_module_exists is false for empty input" {
  ! check_module_exists ""
}

@test "check_module_exists cannot escape the checks directory" {
  ! check_module_exists "../common"
}

@test "suggest_check offers a substring match" {
  run suggest_check cert
  [ "$status" -eq 0 ]
  [[ "$output" == *"certs"* ]]
}

@test "suggest_check returns nothing for a wild miss" {
  run suggest_check zzzzz
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}
