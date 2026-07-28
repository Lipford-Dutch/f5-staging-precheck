#!/usr/bin/env bats
# Unit tests for validation/confirmation helpers in lib/common.sh.

setup() {
  cd "$BATS_TEST_DIRNAME/.." || exit 1
  source lib/common.sh
}

@test "is_uint accepts plain integers" {
  is_uint 0
  is_uint 12
  is_uint 9999
}

@test "is_uint rejects non-integers" {
  ! is_uint abc
  ! is_uint 1.5
  ! is_uint -3
  ! is_uint ""
  ! is_uint "12x"
}

@test "require_cmd succeeds for an existing command" {
  run require_cmd bash
  [ "$status" -eq 0 ]
}

@test "require_cmd dies for a missing command" {
  run require_cmd this_command_does_not_exist_42
  [ "$status" -ne 0 ]
  [[ "$output" == *"Required command not found"* ]]
}

@test "confirm auto-approves when ASSUME_YES=true" {
  ASSUME_YES=true
  run confirm "proceed?"
  [ "$status" -eq 0 ]
}

@test "confirm refuses on non-interactive stdin without ASSUME_YES" {
  ASSUME_YES=false
  run confirm "proceed?" < /dev/null
  [ "$status" -ne 0 ]
}
