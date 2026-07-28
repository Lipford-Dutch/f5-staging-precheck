#!/usr/bin/env bats
# Unit tests for lib/common.sh helpers.

setup() {
  cd "$BATS_TEST_DIRNAME/.." || exit 1
  source lib/common.sh
}

@test "make_temp creates a file with mode 600" {
  tmp=$(make_temp)
  [ -f "$tmp" ]
  mode=$(stat -c '%a' "$tmp" 2>/dev/null || stat -f '%Lp' "$tmp")
  [ "$mode" = "600" ]
  rm -f "$tmp"
}

@test "make_temp records files in the cleanup manifest" {
  _ensure_temp_manifest
  tmp=$(make_temp)
  grep -qxF "$tmp" "$TEMP_MANIFEST"
  rm -f "$tmp" "$TEMP_MANIFEST"
}

@test "cleanup_temp_files removes every recorded temp file" {
  _ensure_temp_manifest
  a=$(make_temp); b=$(make_temp)
  [ -f "$a" ] && [ -f "$b" ]
  cleanup_temp_files
  [ ! -e "$a" ] && [ ! -e "$b" ]
}

@test "json_escape handles quotes" {
  result=$(json_escape 'hello "world"')
  [ "$result" = 'hello \"world\"' ]
}

@test "json_escape handles backslashes" {
  result=$(json_escape 'a\b')
  [ "$result" = 'a\\b' ]
}

@test "json_escape handles tabs and newlines" {
  result=$(json_escape "$(printf 'a\tb')")
  [ "$result" = 'a\tb' ]
}

@test "json_escape output is valid inside JSON" {
  esc=$(json_escape 'quote " and \ slash')
  printf '{"k":"%s"}' "$esc" | python3 -c 'import json,sys; json.load(sys.stdin)'
}

@test "die exits non-zero" {
  run die "boom"
  [ "$status" -ne 0 ]
}
