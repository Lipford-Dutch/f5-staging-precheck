#!/usr/bin/env bash
# Run ShellCheck across every shell script in the repository, including the
# extensionless entry point (bin/check_multi), which a bare *.sh glob misses.
set -euo pipefail
cd "$(dirname "$0")/.."    

if ! command -v shellcheck >/dev/null 2>&1; then
  echo "shellcheck not installed – see docs/INSTALL.md" >&2
  exit 1
fi

mapfile -d '' -t files < <(
  find . -type f -name '*.sh' -not -path './results/*' -not -path './.git/*' -print0
)
files+=("bin/check_multi")

# SC1091 is disabled via .shellcheckrc; -x enables following `source`.
shellcheck -x "${files[@]}"
echo "ShellCheck passed (${#files[@]} files)"
