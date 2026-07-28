#!/usr/bin/env bats

setup() {
  source lib/common.sh
}

@test "make_temp creates a file with mode 600" {
  tmp=$(make_temp)
  [ -f "$tmp" ]
  mode=$(stat -c '%a' "$tmp" 2>/dev/null || stat -f '%Lp' "$tmp")
  [ "$mode" = "600" ]
  rm -f "$tmp"
}

@test "json_escape handles quotes and newlines" {
  result=$(json_escape 'hello "world"')
  [[ "$result" == 'hello \"world\"' ]]
}
