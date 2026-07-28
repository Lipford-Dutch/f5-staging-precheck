#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v bats >/dev/null 2>&1; then
  echo "bats not installed – skipping tests"
  exit 0
fi
bats tests/
