# Contributing to check_multi

Thanks for helping improve `check_multi`. This document describes how to set up
a development environment, the conventions the codebase follows, and what CI
expects before a change can merge.

## Development environment

Install the developer tooling:

```bash
# Debian/Ubuntu
sudo apt-get install -y shellcheck bats

# yq (mikefarah) – required to exercise YAML config/profiles
sudo wget -qO /usr/local/bin/yq \
  https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
sudo chmod +x /usr/local/bin/yq
```

## Before you open a pull request

Run the full local verification suite:

```bash
make check
```

This runs, in order:

1. `make lint` — ShellCheck over every shell script, including the
   extensionless entry point `bin/check_multi`.
2. `make syntax` — `bash -n` parse check.
3. `make test` — the `bats` unit tests under `tests/`.
4. `make smoke` — a dry-run of every check module against the example
   inventory.

CI (`.github/workflows/ci.yml`) runs the same checks plus a Python-based Excel
report smoke test on every push and pull request.

## Coding conventions

- **Shell:** `bash` with `set -euo pipefail` in executables. Two-space indent
  (see `.editorconfig`). Keep ShellCheck clean; suppress a finding only with a
  narrowly scoped `# shellcheck disable=SCxxxx` and a comment explaining why.
- **Modules** live in `lib/`. Each is idempotent (guards against double
  sourcing) and single-purpose.
- **Temp files** must be created via `make_temp` so they are mode `0600` and
  registered for automatic cleanup.
- **Logging** goes to **stderr** via the `log_*` helpers. Only genuine
  machine-readable output (e.g. a generated file path) goes to stdout.

## Adding a new check

Drop a file in `lib/checks/<name>.sh` that defines a `run_check` function:

```bash
#!/usr/bin/env bash
# check: <name> – <description>
run_check() {
  local device=$1
  ssh_exec "$device" "tmsh ..." || return 1
}
```

Return `0` on success and non-zero on failure. Add the check name to the
`--help` text in `bin/check_multi`, the README, and the CI smoke-test loop.

## Commit messages

Use concise, imperative subject lines (e.g. "Fix summary.json device records").
Group related changes; keep unrelated changes in separate commits.
