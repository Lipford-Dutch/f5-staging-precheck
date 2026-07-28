# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **`summary.json` device records were empty.** In `lib/summary.sh` the per-device
  `printf` calls were missing their `>> "$tmp"` redirection, so every device
  object rendered as `{}` and the field text leaked onto the function's stdout,
  corrupting the summary path returned to the caller (and thus the `--excel`
  report path).
- **Temporary files were never cleaned up.** `make_temp` is invoked via command
  substitution, so the in-memory `TEMP_FILES` array populated inside the
  subshell never reached the parent's EXIT trap. Temp-file tracking now uses an
  on-disk manifest shared across subshells, so every temp file is reliably
  removed on exit/interrupt.
- **Broken message parsing in summaries.** `lib/summary.sh` used
  `cut -d' ' -f3-`, which pulled the hostname into the message field whenever a
  record had inconsistent spacing. Parsing now uses a single `read`, and
  `lib/parallel.sh` writes consistent single-space records.
- **Audit `timestamp_start` was overwritten** with the end time on completion;
  the real start time is now preserved for the whole run.
- `bin/check_multi` and the helper scripts are now committed with the executable
  bit set.

### Added
- **CI workflow** (`.github/workflows/ci.yml`): ShellCheck, `bash -n` syntax,
  `bats` unit tests, a dry-run smoke test of every check module with
  `summary.json` validation, and an Excel report generation smoke test.
- **Expanded test suite**: new `bats` tests for inventory validation and
  `summary.json` generation (including a regression guard for the fixes above),
  plus additional `common.sh` coverage.
- Developer tooling: `Makefile` (`lint`/`syntax`/`test`/`smoke`/`check`/`clean`),
  `.shellcheckrc`, `.editorconfig`, `CONTRIBUTING.md`, and this changelog.
- `NO_COLOR` support: colour output is suppressed when `NO_COLOR` is set.

### Changed
- `scripts/shellcheck_all.sh` now also lints the extensionless entry point
  `bin/check_multi`, uses `.shellcheckrc`, and reports the file count.
- README: added a Requirements table, a Development section, and a live CI badge;
  corrected the quick-start clone instructions.

### Removed
- Deleted the committed `check_multi_2.0-alpha.zip`, a binary artifact that
  duplicated the repository contents.

## [2.0.0-alpha] - 2026-07-28

Initial alpha of the redesigned, modular `check_multi` framework: plugin-style
check modules, YAML configuration with environment profiles, a secure SSH
abstraction with retries, controlled parallelism, an audit trail, structured
`summary.json`, and optional executive Excel reports.
