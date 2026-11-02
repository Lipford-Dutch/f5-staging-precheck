# Session Handoff — f5-staging-precheck

| Field | Value |
|---|---|
| **Date** | 2026-11-02 |
| **Repository** | `Lipford-Dutch/f5-staging-precheck` (moved from the `willyd61` account; old URLs redirect) |
| **Visibility** | Public |
| **Default branch / HEAD** | `main` @ `ed6585e` (PR #12) |
| **Status** | Code complete for `1.0.0-alpha`. **Release not yet published** (see P0 below). |
| **Live site** | https://lipford-dutch.github.io/f5-staging-precheck/ (hero at `/`, guide at `/docs/`) |
| **Audience** | The next human or AI agent picking this up cold |

> **Security note for readers:** this file intentionally contains no lab IP addresses,
> hostnames, usernames or credentials. The repo is public. Ask the operator for lab
> access details out-of-band. Never commit them (see §11).

---

## 1. TL;DR

- The repo ships **two tools**: the Bash `check_multi` (`2.0.0-alpha`) and the Python
  `bigip-precheck` (`1.0.0a0`) — a **read-only** pre-upgrade / change-window readiness
  validator for F5 BIG-IP that produces an auditable **GO / NO-GO** verdict.
- `main` is green (pytest 129, ruff, mypy `--strict`, bats 44, ShellCheck, docs build).
- The docs site is **live and verified**. Pages source is **GitHub Actions**; `docs.yml`
  is the *only* deployer.
- **Two things need a human:** publish the `v1.0.0-alpha` release in the GitHub UI, and
  rotate a lab credential that was pasted into a chat session.

## 2. Immediate actions (priority order)

| Pri | Item | Owner | Detail |
|---|---|---|---|
| **P0** | Publish the release | Human | Tag pushes are refused by the agent's git proxy and no release-editing tool exists. See §9. |
| **P0** | Rotate the lab-host credential | Human | A password for the lab scripting host was pasted in plaintext in a chat. Treat as exposed. Never write it anywhere. |
| P1 | Decide fate of stale tag `ALPHA` | Human | Points at `0ceba32` (9+ commits behind). **Contains the `Authorization` base64 redaction leak.** Delete it, or leave it unreleased. Do not publish a release from it. |
| P1 | Replace synthesized fixtures with real captures | Agent + human | Run `bigip-precheck capture` on the lab host; the sanitized output is already in a `captures/` dir in the checkout there. Commit sanitized payloads only. |
| P2 | **PR C** — SNMP layer + REST↔SNMP cross-checks | Agent | `Source.SNMP` / `Source.CROSS` enum members exist but are unused. |
| P2 | **PR D** — HTML/Markdown reports, report signing, TMSH `load sys config verify` | Agent | `Source.TMSH` exists but is unused. `logging/integrity.py` already writes/verifies sidecar digests. |
| P3 | Docs home title still reads "Home · check_multi" | Agent | Cosmetic; set in `scripts/build_docs.py`. |
| P3 | Install the Claude GitHub App on the repo | Human | Without it, PR events do not wake an agent; use scheduled check-ins instead. |

## 3. What was accomplished (PR history)

| PR | Outcome |
|---|---|
| #1 | Polished/hardened `check_multi` for alpha. |
| #2 | Audit, expanded tests, first published docs site. |
| #3 | **bigip-precheck phase A**: Python REST validator (config, REST client, system/HA checkers, gate, redaction, audit log). |
| #4 | **Phase B**: LTM/GTM object checkers, role auto-detection, pre/post snapshots + `diff`. |
| #5 | Live-device integration suite (`tests/live/`) + `capture` command. |
| #6 | **Bug fix found on real hardware:** unprovisioned module (HTTP 404) now reads as *absent* (`INFO`), not as four HIGH failures. |
| #7 | Official alpha: QA hardening, **security fix** (`Authorization` header redaction leaked the base64 payload), housekeeping, branding. |
| #8 | Merged `development` → `main`. |
| #9 | Fixed duplicate Pages deploy: one site, hero `/`, guide `/docs/`. |
| #10 | Sanitized remaining customer branding → Generals of Chaos. |
| #11 | Removed `jekyll-gh-pages.yml` again (it had been re-added and reintroduced the race). |
| #12 | Bumped package version `0.1.0` → `1.0.0a0`. |

Verified this session: Docs workflow build **and** deploy succeed; live hero shows `1.0.0a0`;
`/docs/` and sub-pages return 200; 162 local links resolve; no stale customer branding.

## 4. Architecture & key design decisions

**Bias: never a silent PASS.** A check that cannot confirm health degrades to WARN/FAIL.
An unexpected checker exception becomes `FAIL` with `Source.INTERNAL`.

| Decision | Rationale |
|---|---|
| **Read-only by construction** | Only GETs (plus token login/logout). Nothing may mutate a BIG-IP. Preserve this. |
| **404 = `NotFound` = absence, not failure** | A 404 on a module collection means "not provisioned". `GET`s retry order in `clients/rest.py`: 401-refresh-once → 401/403 `AuthError` → ≥500 retry → **404 `NotFound`** → other ≥400 `UnexpectedResponse`. Genuine errors (auth, timeout, 5xx) still `FAIL`; partial absence still evaluates. |
| **`RestClient` Protocol + `FakeRestClient`** | The whole suite runs offline. Real-device tests are env-gated. |
| **Central redaction (`redaction.py`)** | Secrets never enter config models; resolved from env at runtime. Authorization regex captures the *entire* header value (`.+`), not first token. |
| **Coexistence with `check_multi`** | The Bash tool is untouched in behavior; Python tool lives in `src/bigip_precheck/`. |
| **Exit codes** | `0` GO · `2` NO-GO · `3` config error. |
| **Snapshots** | Schema-versioned pre/post object availability; `run --baseline` forces NO-GO on regression; `diff` exits `2` on regression. |
| **GO/NO-GO hinges on explicit blockers** | Verified by replay: LTM-only + valid license → GO; expired license → NO-GO (`system.license`). |

## 5. Repo map

```
bin/check_multi              Bash tool entrypoint          lib/  completions/  config/
src/bigip_precheck/
  cli.py                     Typer CLI (run, diff, capture, ...)
  checkers/                  system, ha, ltm, gtm (+ base, _icontrol, _objectcheck)
  clients/rest.py            httpx iControl REST client (token auth, retry, NotFound)
  core/                      context, gate, models, orchestrator, registry, exceptions
  config/                    loader (credential resolution), models (pydantic v2)
  logging/                   audit JSONL + integrity digests      reporting/  snapshot.py
  redaction.py  capture.py
tests/python/                129 offline tests; fixtures in tests/python/fixtures/icontrol.py
tests/live/                  env-gated real-device suite (skips unless BIGIP_LIVE_HOST set)
tests/*.bats                 44 Bash unit tests (tests/run_tests.sh)
scripts/                     build_docs.py (guide) · build_hero.py (landing) · shellcheck_all.sh
docs/                        Markdown sources for the guide (+ docs/bigip-precheck/)
.github/workflows/           ci.yml · docs.yml            qa-report/  demo-assets/  examples/
```

## 6. Run & test

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q tests/python          # 129 passed
python3 -m ruff check src tests/python     # clean
python3 -m mypy --strict src               # clean, 31 files
./tests/run_tests.sh                       # 44 bats tests
./scripts/shellcheck_all.sh                # ShellCheck
make docs                                  # builds ./site (gitignored)
```

Python ≥ 3.11 (`StrEnum`, `datetime.UTC`). Docs build needs `pip install -r requirements-docs.txt`
**with the same interpreter you run** (`python3 -m pip ...`).

**Live testing** (real BIG-IP): runs only from a machine that can route to the lab; the
cloud agent sandbox cannot (§8). Set `BIGIP_LIVE_HOST` and `BIGIP_LIVE_*` credentials, then
`pytest tests/live`. Runbook: `docs/bigip-precheck/LIVE-TESTING.md`. The operator's wrapper
script (`run-live-f5.sh`) is **not committed**; it exists only on the lab host.

## 7. CI/CD & GitHub Pages topology

- **A repository has exactly one Pages site.** One artifact, two sections:
  `/` ← `scripts/build_hero.py`, `/docs/` ← `scripts/build_docs.py`.
- `docs.yml` is the **sole deployer** (`environment: github-pages`, `concurrency: pages`).
  It is **path-filtered** (docs, README, build scripts, branding, workflow). A change that
  touches only `src/` does **not** redeploy; trigger it with `workflow_dispatch` (the hero
  reads versions from source).
- **Never re-add `jekyll-gh-pages.yml`.** It races `docs.yml` for the same site, runs on every
  push, and would publish a Jekyll render of the repo root over the hero page. This happened
  once already (re-added in `2dae283`, removed in #11).
- **Pages source must be "GitHub Actions"**, not "Deploy from a branch". (A run named
  "pages build and deployment" means branch mode is on.)
- `ci.yml` asserts the built layout and that every hero link resolves to a built file.
- `site/` is gitignored; do not commit build output.

## 8. Environment & access facts

- **Repo moved** from the `willyd61` user to the `Lipford-Dutch` org. GitHub tooling scoped to
  the old owner still works through redirects; cross-owner `add_repo` is blocked by the platform.
- **Cloud sandbox cannot reach the private lab.** The agent proxy returns `403 ... private/reserved
  range` for RFC1918 destinations. A TCP/TLS connect can *appear* to succeed — **always verify
  with a real HTTP request**, never a port probe.
- **Git tag pushes are refused** by the agent git proxy (`unexpected disconnect`) even though
  branch pushes work; the relay-failure log stays empty. Don't retry-loop; create tags in the UI.
- **No release tooling** in the agent: GitHub MCP has no release create/edit; `gh` API paths are
  blocked. Releases are a human step.
- Without the Claude GitHub App installed, PR webhooks don't wake an agent — schedule check-ins.
- Conventions: **squash-merge**, title `Title (#N)`, PRs opened as **draft**, commits end with the
  attribution footer the session specifies. Historically merges required an explicit request.

## 9. Publishing the release (human steps, ~1 minute)

1. GitHub → **Releases** → open the existing **draft** ("First Production Release v2.1").
2. **Choose a tag** → type `v1.0.0-alpha` → *Create new tag on publish*; **Target: `main`**.
   (Do **not** reuse `ALPHA`.)
3. **Title:** `bigip-precheck + check_multi 1.0.0-alpha`
4. Paste the notes below; tick **Set as a pre-release**; ensure *draft* is off → **Publish**.

```markdown
First pre-release of the combined toolkit: Python **bigip-precheck 1.0.0a0** and Bash
**check_multi 2.0.0-alpha** — read-only BIG-IP pre-upgrade readiness with an auditable
GO / NO-GO verdict.

### Highlights
- LTM + GTM + HA + system checks over iControl REST, role auto-detection, pre/post snapshots
  with regression diffing (`run --baseline`, `diff`).
- Live-device test suite and a sanitizing `capture` command.
- **Security:** `Authorization` header redaction no longer leaks the base64 credential payload.
- **Fix:** an unprovisioned module (HTTP 404) is reported as absent, not as a failure.
- Published docs: https://lipford-dutch.github.io/f5-staging-precheck/

See CHANGELOG.md for the full list. 129 Python tests, 44 Bash tests; ruff and mypy --strict clean.
```

## 10. Gotchas & lessons learned

- `pytestmark` in a `conftest.py` does **not** propagate to tests — use an **autouse fixture** to
  gate live tests (the original attempt made them try real connections).
- `Settings.backoff_base_s` must be `> 0` (pydantic `gt=0`); tests use `0.001`.
- Circular import `clients` ↔ `core` is avoided with a `TYPE_CHECKING` guard in `core/context.py`
  and a lazy `__getattr__` in `core/__init__.py`. Don't "simplify" those away.
- PEP 440: the package version is `1.0.0a0`; the human-facing release/tag is `1.0.0-alpha`
  (equivalent).
- Typer's `Option(...)` defaults trip ruff B008 — ignored per-file by design.
- The first live run against real hardware found the 404 bug that 129 offline tests could not.
  Real-device captures are worth more than synthesized fixtures.
- `README.md` fence balance matters for the docs build; check fence count is even after edits.

## 11. Security constraints (non-negotiable)

- **Read-only.** No code path may modify a BIG-IP.
- **No real lab IPs, hostnames, usernames, or credentials in the repo** — fixtures use RFC 5737
  (`192.0.2.x`) and `example.com`. The repo is public.
- Secrets are resolved from environment variables at runtime; never stored in config models.
- `capture` scrubs secrets, `registrationKey`, and host/IP and **aborts on any detected leak**.
- No customer branding (the repo was sanitized to Generals of Chaos in #10).

## 12. Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-07 | Coexist with `check_multi`; phased PRs; synthesized fixtures; package `bigip-precheck` | Lowest risk; incremental review. |
| 2026-08-11 | 404 → `NotFound` → INFO | Found on a real LTM-only VE; GTM 404s wrongly produced NO-GO. |
| 2026-08-11 | Redact entire `Authorization` value | `\S+` matched only the scheme, leaking base64. |
| 2026-09-02 | One Pages site, two sections | Two workflows were racing one site. |
| 2026-11-02 | Removed Jekyll workflow again (#11) | Re-added by mistake; reintroduced the race. |
| 2026-11-02 | Version `1.0.0a0` ↔ tag `v1.0.0-alpha`; do not reuse tag `ALPHA` | `ALPHA` is stale and contains the redaction leak. |

## 13. First actions for the next agent

1. `git fetch && git checkout main && git log --oneline -5` — confirm HEAD ≥ `ed6585e`.
2. Run the §6 checks; all must be green before any change.
3. Ask the operator whether the release (§9) is published and the credential is rotated.
4. Pick **P1 real captures** or **PR C (SNMP)**. Open work as a draft PR from a `claude/*` branch.
5. Before touching Pages: read §7. Before touching REST error handling: read the 404 row in §4.
