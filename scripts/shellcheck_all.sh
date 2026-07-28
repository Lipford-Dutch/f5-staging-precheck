#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
find . -name '*.sh' -not -path './results/*' -print0 \
  | xargs -0 shellcheck -x -e SC1091
echo "ShellCheck passed"
