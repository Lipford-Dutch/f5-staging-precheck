#!/usr/bin/env bats
# Unit tests for lib/summary.sh JSON generation.
# Regression guard: device records must be fully populated and the function
# must emit ONLY the summary path on stdout (logs go to stderr).

setup() {
  cd "$BATS_TEST_DIRNAME/.." || exit 1
  source lib/common.sh
  source lib/summary.sh

  OUTPUT_DIR="$(mktemp -d)"
  RESULTS_FILE="$(make_temp)"
  printf 'SUCCESS f5-a.example.com\nFAILED  f5-b.example.com connection timed out\n' > "$RESULTS_FILE"
  PARALLEL_TOTAL=2 PARALLEL_SUCCESS=1 PARALLEL_FAILED=1
  CHECK_NAME=platform ENV_NAME=lab INVENTORY_FILE=examples/devices.txt VERSION=test
}

teardown() {
  rm -rf "$OUTPUT_DIR" "$RESULTS_FILE"
}

@test "generate_summary_json returns a single valid path on stdout" {
  # Logs go to stderr; stdout must be exactly the summary path (one line).
  local out
  out="$(generate_summary_json 2>/dev/null)"
  [ "$(printf '%s\n' "$out" | wc -l)" -eq 1 ]
  [ -f "$out" ]
}

@test "device records are fully populated" {
  path="$(generate_summary_json)"
  python3 - "$path" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["total"] == 2, d["total"]
assert len(d["devices"]) == 2, d["devices"]
names = {x["name"] for x in d["devices"]}
assert names == {"f5-a.example.com", "f5-b.example.com"}, names
byname = {x["name"]: x for x in d["devices"]}
assert byname["f5-a.example.com"]["status"] == "SUCCESS"
assert byname["f5-b.example.com"]["status"] == "FAILED"
assert byname["f5-b.example.com"]["message"] == "connection timed out"
PY
}

@test "success_rate is computed correctly" {
  path="$(generate_summary_json)"
  rate="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["success_rate"])' "$path")"
  [ "$rate" = "50.0" ]
}
