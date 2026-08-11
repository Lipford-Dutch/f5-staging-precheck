# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **An unprovisioned module no longer reports as a failure.** Found by the first
  live run against a real BIG-IP VE (TMOS 17.5.1.8, LTM-only): every GTM endpoint
  returns HTTP 404, and the GTM checkers reported four HIGH failures
  (`could not read wide IPs: ... HTTP 404`), which would wrongly push a device to
  NO-GO. A 404 means the collection does not exist — the module is not
  provisioned — which is an absence to report, not a read failure.
  - New `NotFound(ClientError)` exception; the REST client raises it on 404 while
    other 4xx still raise `UnexpectedResponse`.
  - GTM and LTM checkers report `INFO` ("… not provisioned on this device") when
    every relevant endpoint 404s. Genuine read errors (auth, timeout, 5xx) and
    partial absences (one record type missing) are unchanged, so nothing is
    masked — verified by `tests/python/test_not_provisioned.py`.
  - The live `live_ctx` fixture now uses **real detected roles** instead of
    hard-coding `{LTM, GTM}`, so live output matches production role filtering.
  - Fixtures refreshed to a real 17.5.1.8 device (`VERSION`,
    `PROVISION_LTM_ONLY`, `NODE_STATS_UNKNOWN`, `STANDALONE_LTM_ONLY`), plus a
    live regression test asserting unprovisioned modules never `FAIL`.

### Added
- **`bigip-precheck` live testing — real-device integration suite + `capture`.**
  - `tests/live/` — an env-gated pytest suite that authenticates to a real BIG-IP
    over iControl REST and asserts the whole pipeline runs (token login, version
    probe, role auto-detection, every checker, and a full orchestrator GO/NO-GO
    run) without any checker crashing. Skipped unless `BIGIP_LIVE_HOST` is set, so
    normal CI stays offline.
  - `capture` CLI command — issues read-only GETs against a device and writes
    **sanitized** payloads (secrets, `registrationKey`, and host/IP scrubbed;
    aborts on any leak) for use as offline fixtures.
  - `examples/bigip-precheck/lab-standalone.yaml` and
    [`docs/bigip-precheck/LIVE-TESTING.md`](docs/bigip-precheck/LIVE-TESTING.md)
    runbook. The harness and capture were validated end-to-end against a local
    self-signed HTTPS iControl emulator before shipping.

- **`bigip-precheck` phase B — LTM + GTM object checks, role auto-detection, snapshots.**
  Builds on phase A:
  - **LTM checkers** — `ltm.virtual-servers`, `ltm.pools` (incl. zero-active-member
    detection), `ltm.nodes`. Objects offline while still enabled are traffic-impacting
    failures; disabled objects are informational.
  - **GTM checkers** — `gtm.wide-ips` and `gtm.pools` (sweeping A/AAAA/CNAME record
    types), `gtm.servers`, `gtm.datacenters`.
  - **REST role auto-detection** — when a device has no configured roles, LTM/GTM are
    inferred from `/sys/provision`; checks are role-filtered per device.
  - **Pre/post object snapshots** — every run writes a schema-versioned
    `snapshot-<session>.json`; `run --baseline <snap>` diffs against it and forces
    **NO-GO** on any availability regression, and a new `diff` command compares two
    snapshots directly (exit `2` on regression). New `ltm-only` / `gtm-only` profiles.

- **`bigip-precheck` — new Python upgrade-readiness validator (phase A / alpha).**
  A read-only, iControl REST–driven companion to the Bash `check_multi` tool that
  produces a per-device and overall **GO / NO-GO** verdict before an upgrade or
  change window. Highlights:
  - System checks (`system.version`, `system.license`, `system.provisioning`,
    `system.boot-volumes`) and HA checks (`ha.failover-status`, `ha.sync-status`).
  - Token-authenticated REST client with retry/backoff+jitter and a TMOS version
    probe; checkers depend on a `RestClient` protocol so the suite runs with no lab.
  - Orchestration that evaluates the **standby member before the active** within
    an HA group and records dependency-blocked checks as explicit `SKIP`s.
  - Design bias *never a silent PASS*: a check that cannot confirm health degrades
    to `WARN`/`FAIL`, and an unexpected checker error becomes a `FAIL`.
  - Full audit trail (redacted JSONL + human log), SHA-256 report integrity
    sidecar, Rich console dashboard and schema-versioned JSON report.
  - Typer CLI (`run`, `list-checks`, `validate-config`, `version`) with CI mode
    and exit codes `0` GO / `2` NO-GO / `3` config error.
  - 50 offline tests (pytest), `ruff` + strict `mypy` clean, and a dedicated CI
    job. Secrets are resolved from the environment and never stored in config.
  - See [`src/bigip_precheck/README.md`](src/bigip_precheck/README.md),
    [`docs/bigip-precheck/ARCHITECTURE.md`](docs/bigip-precheck/ARCHITECTURE.md)
    and [`docs/bigip-precheck/TESTING.md`](docs/bigip-precheck/TESTING.md).
    LTM/GTM checks (PR B), the SNMP cross-check layer (PR C) and richer reports
    (PR D) follow.

### Security
- **Path-traversal in check selection closed.** Check names are now validated
  against `^[A-Za-z0-9_-]+$` before a module is resolved, so a crafted name such
  as `../common` can no longer source a `.sh` file outside `lib/checks/`.
- Inventory validation additionally rejects `()`, `{}` and quote characters.

### Added
- **Documentation site + GitHub Pages CI/CD.** A dependency-light generator
  (`scripts/build_docs.py`) renders the Markdown under `docs/` into a styled,
  responsive, theme-aware (light/dark) site with nav search, per-page tables of
  contents and copy-to-clipboard code blocks. `.github/workflows/docs.yml`
  builds and deploys it to GitHub Pages on merge to `main`; CI verifies the
  build on every PR.
- **New check modules:** `ntp`, `license`, `diskspace`, `ha`, plus
  `docs/MODULES.md` cataloguing them and a roadmap of proposed modules.
- **CLI safety & UX:** `--list-checks`, `--yes/-y`, `--no-color`,
  "did you mean…?" suggestions for mistyped checks, a Bash version guard, a
  diagnostic `ERR` trap, and a colour-coded end-of-run summary.
- **Confirmation gate** for high-impact runs (real execution against `prod` or
  ≥ 50 devices); refuses to proceed unattended unless `--yes` is given.
- **Bash tab-completion** (`completions/check_multi.bash`) for options, checks,
  environments and file paths.
- New wiki-style docs pages: `USAGE`, `CONFIGURATION`, `TROUBLESHOOTING`, `FAQ`.
- **Expanded tests** (17 → 44): CLI integration, argument validation, check
  discovery/registry, module contract, and validation helpers.
- `lib/registry.sh` for check discovery and name validation; `make docs`,
  `make docs-serve` targets.

### Fixed
- **CLI options were overridden by YAML.** `load_config`/profiles ran after
  argument parsing and clobbered flags such as `-t/--threads`; CLI values are
  now captured and re-applied last so an explicit flag always wins.
- **Silent bad `--threads`.** Non-integer or zero thread counts are now rejected
  with a clear message instead of being ignored.
- **Options missing their value** (e.g. a trailing `-t`) now produce a friendly
  error instead of tripping `set -u`.

### Changed
- Inventory whitespace trimming uses Bash parameter expansion (no `echo | sed`)
  and supports inline `#` comments.
- `Makefile` `smoke` target and the CI smoke job discover checks dynamically, so
  new modules are covered automatically.

---

### (Earlier, merged in #1)

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
