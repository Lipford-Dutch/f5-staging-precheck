# Production-Readiness Audit — `f5-staging-precheck` (check_multi 2.0 + bigip-precheck)

**Auditor:** automated QA pass (Test Architect role)
**Date:** 2026-08-10
**Scope:** entire repository — Python package `bigip_precheck` (iControl REST validator) and the Bash `check_multi` framework (SSH/tmsh sweeps), plus tests, CI, and packaging.
**Environment:** Ubuntu 22.04 sandbox; CPython 3.11.15 (provisioned to match the project's declared floor); pytest 9.1, coverage 7.15 (branch), ruff 0.16, mypy 1.14 (strict), shellcheck 0.11, bats 1.14.

---

## 1. Executive summary

**Verdict: GO for a lab/internal release, with three fixes now applied. The codebase is in strong shape** — clean static analysis, a real (not decorative) test suite, disciplined error handling ("never a silent PASS"), and centralized secret redaction. It is well above the median for an internal tool.

The audit nonetheless found **three genuine bugs**, all now fixed with regression tests, and one packaging/portability gap now closed:

| # | Severity | One-line |
|---|----------|----------|
| BUG-2 | **High (security)** | Free-text redaction leaked the base64 credential in `Authorization: Basic …` — only the word "Basic" was scrubbed. |
| FIND-4 | **Medium** | No `.gitattributes`; a Windows checkout silently produced CRLF that breaks *every* shell script on Linux. |
| BUG-1 | **Medium** | `retries: 0` + a first-attempt HTTP 401 raised an uncaught `AssertionError` instead of the typed `AuthError`. |
| BUG-3 | **Low** | Version probe raised an uncaught `AttributeError` on a malformed payload instead of degrading to `""`. |

Top residual risks (not fixed — recommendations below): the Bash `-p` password mode is non-functional (`BatchMode=yes` is unconditional), and there are no integration/live-device tests (by design — the tool is pre-lab).

---

## 2. Baseline vs. final metrics

| Gate | Baseline | Final | Δ |
|------|----------|-------|---|
| Python unit tests | 50 passed | **87 passed** | +37 |
| Python coverage (line+branch) | 88% | **94%** | +6 pts |
| ruff | clean | clean | — |
| mypy `--strict` | clean (26 files) | clean (26 files) | — |
| Bash `bats` | 44 passed | 44 passed | — |
| shellcheck | clean (22 files) | clean (22 files) | — |
| Bash syntax (`bash -n`) | OK | OK | — |
| Smoke (11 dry-run checks) | 11/11 | 11/11 | — |
| CLI `validate-config` | OK | OK | — |
| Confirmed bugs open | — | **0** (3 found, 3 fixed) | — |

All 50 original Python tests and all 44 original bats tests still pass — no regressions introduced.

Per-module coverage after the pass (high-value modules): `redaction.py` 100%, `core/gate.py` 100%, `core/registry.py` 99%, `checkers/system.py` 98%, `core/orchestrator.py` 94%, `clients/rest.py` 93% (was 76%). Lowest remaining: `cli.py` 80% (Typer wiring), `checkers/ha.py` 86%.

---

## 3. Findings

Severity key: **High** = security/data-loss or crash on a valid config; **Medium** = wrong behaviour on a plausible path; **Low** = robustness/edge; **Info** = advisory.

| ID | Sev | Location | Description | Evidence | Fix status |
|----|-----|----------|-------------|----------|-----------|
| BUG-2 | High | `src/bigip_precheck/redaction.py` `_TEXT_PATTERNS` | The `Authorization` rule `(...)\S+` stops at the first space, so `Authorization: Basic <base64>` redacted only "Basic" and **leaked the base64 credentials**. The dedicated `Basic …` rule couldn't recover it because the earlier rule had already consumed the "Basic" prefix. Structured dict payloads were safe (key-based redaction); free-text log/error/evidence strings were not. | New test `test_redact_text_scrubs_inline_secrets` failed pre-fix with `Authorization: ***REDACTED*** dGVzdDp0ZXN0`. | **FIXED** — pattern now captures the whole header value. Regression test added. |
| FIND-4 | Medium | repo root (missing `.gitattributes`) | LF policy lived only in `.editorconfig` (editor-advisory). A Windows clone with `core.autocrlf` produced a CRLF working tree; on Linux every `.sh` and `bin/check_multi` failed to parse (`$'\r': command not found`, `syntax error near $'{\r'`). Committed blobs are LF (`git ls-files --eol` → `i/lf w/crlf`), so CI passed and the risk was invisible — a Windows contributor could still commit CRLF and break Linux/macOS. | `bash -n lib/*.sh` failed on the working tree; passed on a clean `git archive` export. | **FIXED** — added `.gitattributes` enforcing `eol=lf` for `*.sh`, `*.bats`, `*.py`, and `bin/check_multi`. |
| BUG-1 | Medium | `src/bigip_precheck/clients/rest.py` `get()` | With `retries: 0` (a valid `Settings` value, `ge=0`) and a first-attempt HTTP 401 on password auth, the one-shot token-refresh branch does `continue`; the single-iteration loop then exhausts and hits `assert last_exc is not None` with `last_exc` still `None` → `AssertionError`. Callers expect `AuthError`; instead a checker sees a generic "unexpected error" FAIL. | New test `test_retries_zero_first_attempt_401_raises_autherror_not_assertion`. | **FIXED** — the exhausted-loop tail now raises a typed `AuthError` when `last_exc is None`. Regression test added. |
| BUG-3 | Low | `src/bigip_precheck/clients/rest.py` `_probe_version()` | The graceful-degradation `except (KeyError, StopIteration, TypeError)` omitted `AttributeError`; a malformed-but-valid payload where `entries` is not a dict raised `AttributeError` from `.values()` and escaped the property, defeating the intended "return ''" fallback. | New test `test_version_probe_degrades_to_empty_string_on_bad_shape`. | **FIXED** — added `AttributeError` to the caught tuple. |
| FIND-5 | Medium | `lib/ssh.sh` `_ssh_build_opts()` | `BatchMode=yes` is set unconditionally (line 22), which disables password/keyboard-interactive auth. The documented `-p` password mode (`sshpass -e ssh …`, line 78) therefore can never authenticate — `sshpass` has no prompt to answer. `-p` is effectively dead. | Code read; `grep -n BatchMode lib/ssh.sh`. | **Open — recommendation.** Only add `BatchMode=yes` when `USE_PASSWORD != true` (see §5). Left unfixed: no bats coverage exists for the password branch, so the change can't be proven green here without adding harness. |
| FIND-6 | Low | `src/bigip_precheck/core/orchestrator.py` `_run_device()` | `client = self._factory(device, cred)` is constructed *before* the `try/finally`. A factory that raises (a custom `client_factory`, or `httpx.Client` init on pathological config) propagates out of `_run_device` → `_run_group` → `fut.result()` and **aborts the entire run** rather than failing just that device. The default httpx factory rarely raises, so impact is low. | Code read. | **Open — recommendation.** Move the factory call inside the `try`, mapping failure to a `device.connect` FAIL like the credential path already does. |
| FIND-7 | Info | `src/bigip_precheck/checkers/system.py` `_service_check()` | `days = (parsed - datetime.now(UTC)).days` uses `timedelta.days` (floor). A service-check date of *today* (parsed at 00:00 UTC) reads as `-1` by mid-day → reported "has passed". Acceptable for a conservative pre-upgrade gate (errs toward WARN/FAIL, never a false GO), but technically an off-by-one at the day boundary. | Code read; covered by new date-parsing tests. | **Open — advisory.** Compare calendar dates if exactness matters. |
| FIND-8 | Low | `lib/ssh.sh` | No `-i` / `IdentityFile` support; a non-default key name is invisible to the tool. Users must rely on `~/.ssh/config` or the default key. | `grep -n IdentityFile lib/ssh.sh` → none. | **Open — enhancement.** |
| FIND-9 | Info | `pyproject.toml` | `requires-python = ">=3.11"` is a hard floor enforced at runtime by `from datetime import UTC` (3.11+). Correct and intentional, but there is no 3.9/3.10 fallback; the suite cannot even import on 3.10. | `ImportError: cannot import name 'UTC'` on 3.10. | **No action** (matches declared support). If broader support is ever wanted, use `datetime.timezone.utc`. |

Positives worth recording: `timed()` correctly converts any checker exception into a FAIL (no silent drops); the registry has real topological-sort cycle detection; the GO/NO-GO gate is total over `Status`; redaction is deny-by-default by key **and** regex; the audit log has an integrity digest. These are mature choices.

---

## 4. Test suite — summary & how to run

**Python** (`tests/python/`, pytest): 87 tests. Original files unchanged; three new files added, same style, fixtures, and location:
- `test_rest_client_edge.py` — retry exhaustion, transient-error recovery, the `retries=0`/401 regression, non-JSON / non-object bodies, 4xx, `close()` logout semantics (mints vs. pre-supplied token), context-manager, version-probe degradation.
- `test_system_checkers_edge.py` — license WARN (near-expiry), PASS (far future), unparseable date, client-error FAIL; `_parse_bigip_date` format matrix; version/provisioning/boot-volume WARN branches.
- `test_registry_redaction_edge.py` — registry error paths (empty/duplicate name, unknown get, unknown dependency), `core` lazy-import surface, and **adversarial redaction** (secrets in nested lists, mixed-case keys, inline free-text, non-string keys, tuple→list, bytes passthrough).

All tests are isolated, deterministic (no network/clock/random — `httpx.MockTransport` and a `FakeRestClient` fixture), and fast (<3 s total).

```bash
# From the repo root, on Python >= 3.11:
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
python -m pytest --cov=bigip_precheck --cov-branch --cov-report=term-missing
python -m ruff check src tests
python -m mypy
python -m bigip_precheck.cli validate-config examples/bigip-precheck/inventory.yaml

# Bash side (run on Linux/macOS with an LF checkout; requires bats + shellcheck):
make check          # = lint + syntax + bats + smoke
```

---

## 5. Residual risks & recommended next steps

1. **Fix the `-p` password mode (FIND-5).** Minimal patch in `lib/ssh.sh::_ssh_build_opts`:
   ```bash
   # add BatchMode only when NOT using password auth
   if [[ "${USE_PASSWORD}" != "true" ]]; then
     opts+=(-o "BatchMode=yes")
   fi
   ```
   Add a bats test that asserts `BatchMode=yes` is absent when `USE_PASSWORD=true`.
2. **Harden orchestrator device isolation (FIND-6):** move client construction inside the per-device `try` so one device's factory failure can't abort the run.
3. **Integration / live-device tests:** the suite is entirely unit-level (correct for now). Before production use against real BIG-IPs, add a thin integration layer (recorded-cassette or a lab device behind a flag) covering auth, a real stats payload, and an HA pair.
4. **Coverage top-ups:** `cli.py` (80%) — the `run` command's happy path and the `--json` branch are unexercised; a Typer `CliRunner` test would close most of it. `checkers/ha.py` (86%) — the non-green traffic-group WARN branch.
5. **Property-based tests (high value, pure functions):** `redaction.redact` and `_parse_bigip_date` are ideal Hypothesis targets — e.g., "no known secret token survives `redact_text`" over generated header strings.
6. **Repo hygiene:** the working folder currently holds unrelated scratch files from a parallel infrastructure task (`*.ps1`, `*-result.txt`, `lab-devices.txt`) and stray `.coverage*` data. These are not part of the audit and can be deleted; consider a `.gitignore` entry for `.coverage*` and `results/`.

---

## 6. Exact commands (reproducibility)

```bash
# Toolchain (sandbox had none; 3.11 provisioned via uv to match requires-python)
uv python install 3.11
uv venv --python 3.11 ~/venv311 && . ~/venv311/bin/activate
uv pip install pytest pytest-cov ruff mypy types-PyYAML typer rich pydantic httpx pyyaml openpyxl
uv pip install --no-deps -e .

# Python gates (coverage data redirected off the mounted FS)
export COVERAGE_FILE=~/cov/.coverage
python -m pytest --cov=bigip_precheck --cov-branch --cov-report=term-missing
python -m ruff check src tests
python -m mypy --cache-dir ~/.mypy_cache      # stable mypy 1.14 (2.3.0 had an internal crash)

# Bash gates — run against a clean LF export (working tree was a CRLF Windows checkout)
git archive HEAD | tar -x -C ~/lfcheckout && cd ~/lfcheckout
find . -name '*.sh' -not -path './results/*' -print0 | xargs -0 -n1 bash -n && bash -n bin/check_multi
bats tests/
./scripts/shellcheck_all.sh
for c in preflight platform umm certs keys syncgroup network ntp license diskspace ha; do
  ./bin/check_multi --dry-run "$c" examples/devices.txt >/dev/null; done
```

**Environment notes for reproducers:** (a) the project targets Python ≥3.11 — 3.10 cannot import it; (b) run coverage with `COVERAGE_FILE` on a local (non-mounted) path or its temp-file cleanup fails with `PermissionError`; (c) run the Bash suite from an LF checkout (or after applying the new `.gitattributes` and re-normalizing) — a CRLF working tree fails `bash -n`.
