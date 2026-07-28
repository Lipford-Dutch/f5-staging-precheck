#!/usr/bin/env bats
# Unit tests for lib/inventory.sh device-list parsing and validation.

setup() {
  cd "$BATS_TEST_DIRNAME/.." || exit 1
  source lib/common.sh
  source lib/inventory.sh
  INV="$(make_temp)"
}

teardown() {
  rm -f "$INV"
}

@test "loads valid hosts and skips comments and blanks" {
  printf '# comment\nf5-a.example.com\n\n  f5-b.example.com  \n' > "$INV"
  run load_and_validate_inventory "$INV"
  [ "$status" -eq 0 ]
  [[ "$output" == *"f5-a.example.com"* ]]
  [[ "$output" == *"f5-b.example.com"* ]]
}

@test "trims surrounding whitespace" {
  printf '   host.example.com   \n' > "$INV"
  run load_and_validate_inventory "$INV"
  [ "$status" -eq 0 ]
  # Last stdout line is the emitted device (log lines go to stderr).
  [ "${lines[-1]}" = "host.example.com" ]
}

@test "rejects entries with shell metacharacters" {
  printf 'good.example.com\nevil.com; rm -rf /\n' > "$INV"
  # Capture stdout only (device list); warnings go to stderr.
  output="$(load_and_validate_inventory "$INV" 2>/dev/null)"
  [[ "$output" == *"good.example.com"* ]]
  [[ "$output" != *"rm -rf"* ]]
}

@test "fails on a missing inventory file" {
  run load_and_validate_inventory "/no/such/file"
  [ "$status" -eq 2 ]
}

@test "fails on an empty inventory file" {
  : > "$INV"
  run load_and_validate_inventory "$INV"
  [ "$status" -eq 2 ]
}

@test "fails when only comments are present" {
  printf '# just a comment\n\n' > "$INV"
  run load_and_validate_inventory "$INV"
  [ "$status" -eq 2 ]
}
