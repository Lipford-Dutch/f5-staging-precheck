#!/usr/bin/env bats
# Integration tests for the bin/check_multi entry point: argument validation,
# error handling and the safe dry-run path. No network access is used.

setup() {
  cd "$BATS_TEST_DIRNAME/.." || exit 1
  BIN=./bin/check_multi
  INV=examples/devices.txt
}

@test "--version prints the version" {
  run "$BIN" --version
  [ "$status" -eq 0 ]
  [[ "$output" == *"check_multi"* ]]
}

@test "--list-checks lists modules" {
  run "$BIN" --list-checks
  [ "$status" -eq 0 ]
  [[ "$output" == *"platform"* ]]
  [[ "$output" == *"preflight"* ]]
}

@test "no arguments is a usage error" {
  run "$BIN"
  [ "$status" -eq 1 ]
}

@test "unknown check is rejected" {
  run "$BIN" not_a_real_check "$INV"
  [ "$status" -ne 0 ]
  [[ "$output" == *"Unknown check"* ]]
}

@test "unknown check offers a suggestion when similar" {
  run "$BIN" cert "$INV"
  [ "$status" -ne 0 ]
  [[ "$output" == *"Did you mean"* ]]
  [[ "$output" == *"certs"* ]]
}

@test "non-integer --threads is rejected" {
  run "$BIN" -t abc platform "$INV"
  [ "$status" -ne 0 ]
  [[ "$output" == *"positive integer"* ]]
}

@test "zero --threads is rejected" {
  run "$BIN" -t 0 platform "$INV"
  [ "$status" -ne 0 ]
}

@test "an option missing its value is reported" {
  run "$BIN" -t
  [ "$status" -ne 0 ]
  [[ "$output" == *"requires a value"* ]]
}

@test "a missing inventory file is reported" {
  run "$BIN" platform /no/such/inventory.txt
  [ "$status" -ne 0 ]
  [[ "$output" == *"not found"* ]]
}

@test "dry-run against the example inventory succeeds" {
  run "$BIN" --dry-run platform "$INV"
  [ "$status" -eq 0 ]
  rm -rf results
}

@test "dry-run writes a populated summary.json" {
  run "$BIN" --dry-run --output-dir "$BATS_TEST_TMPDIR/out" platform "$INV"
  [ "$status" -eq 0 ]
  [ -f "$BATS_TEST_TMPDIR/out/summary.json" ]
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert d['devices'] and all(x['name'] for x in d['devices'])" \
    "$BATS_TEST_TMPDIR/out/summary.json"
}

@test "prod run without a TTY and without --yes aborts" {
  run "$BIN" -e prod platform "$INV" < /dev/null
  [ "$status" -ne 0 ]
  [[ "$output" == *"Aborted"* || "$output" == *"Confirmation required"* ]]
}
