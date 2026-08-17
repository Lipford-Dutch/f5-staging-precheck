<div align="center">

<img src="branding/bofa-logo.png" alt="Bank of America" width="200"><br>
<sub><b>Bank of America</b> — Demo Run-of-Show</sub>

</div>

---

# Demo Run-of-Show — `f5-staging-precheck`

A tight, rehearsable talk track for a live or recorded demo. **~8–10 minutes.** Every command below is real and reproducible (see `README.md` for the one-time mock-server setup that lets the Python checks run with no live BIG-IP).

**Framing (say this first):** *"This is a read-only pre-upgrade readiness tool for F5 BIG-IP. Two components share one repo: `check_multi`, a fast Bash SSH/tmsh sweep for large fleets, and `bigip-precheck`, a deeper Python/iControl-REST validator that emits a GO / NO-GO verdict with a signed audit trail. The whole point is to answer one question before a change window — 'is it safe to upgrade?' — and never give a false 'yes'."*

> On the check count: `check_multi` ships **11 check modules**; `bigip-precheck` ships **6 checkers** — **17 distinct checks** in total. (If you counted ~13, you were likely blending the two lists.) The exact catalogs are shown live in scenes 2 and 7.

---

## Act 1 — The Python validator (the flagship). ~5 min

| # | Say | Run | Show / expected | Screenshot |
|---|-----|-----|-----------------|-----------|
| 1 | "Here's the command surface — read-only by design." | `bigip-precheck --help` | Four commands; no mutate flag exists. | `08_help.png` |
| 2 | "Six checkers, each with a severity and the role it applies to." | `bigip-precheck list-checks` | Table: version, license, provisioning, boot-volumes, failover, sync. | `09_list_checks.png` |
| 3 | "Profiles bundle checks for a scenario." | `bigip-precheck list-checks --profile full --inventory demo-assets/inventories/lab-go.yaml` | Filtered list. | `10_list_checks_profile.png` |
| 4 | "It validates config offline before touching anything…" | `bigip-precheck validate-config demo-assets/inventories/lab-go.yaml` | `OK — 1 device, 2 profiles`. | `11a_validate_ok.png` |
| 5 | "…and it refuses bad config early — duplicate host, unknown check." | `bigip-precheck validate-config demo-assets/inventories/lab-invalid.yaml` | Clear rejection, exit 3. | `11b_validate_fail.png` |
| 6 | **"The money shot: a healthy device."** | `bigip-precheck run demo-assets/inventories/lab-go.yaml --ci` | Green table, **verdict GO**, exit 0. | `12_run_go.png` |
| 7 | **"Now a device that's NOT ready — expired license and config drift."** | `bigip-precheck run demo-assets/inventories/lab-mixed.yaml --ci` | Per-device verdicts, **overall NO-GO**, blocking issues listed, exit 2. | `13_run_nogo.png` |
| 8 | "Policy is tunable — strict mode blocks HIGH-severity warnings too." | `bigip-precheck run demo-assets/inventories/lab-warn.yaml --strict` | A WARN device flips to NO-GO. | `14_run_strict.png` |
| 9 | "For pipelines, machine-readable output." | `bigip-precheck run demo-assets/inventories/lab-go.yaml --json` | JSON verdict to stdout. | `15_run_json.png` |
| 10 | "Every run leaves a structured, **hash-sealed** report…" | `cat demo-assets/artifacts/go_report.json` | Structured report + `.sha256`. | `16_json_report.png` |
| 11 | "…and a tamper-evident audit trail. Here's the digest verifying." | (integrity check) | `INTEGRITY: VERIFIED ✓` | `17_audit_integrity.png` |

**Act 1 close:** *"Green means go, red means stop, and there's a signed record of exactly why — that's what makes it safe to put in a change-control process."*

---

## Act 2 — The Bash fleet sweep. ~3 min

| # | Say | Run | Show / expected | Screenshot |
|---|-----|-----|-----------------|-----------|
| 12 | "For breadth across a big fleet, the Bash tool. Eleven check modules." | `./bin/check_multi --list-checks` | The 11 modules. | `01_cm_list_checks.png` |
| 13 | "All eleven execute cleanly." | (dry-run matrix) | 11/11 ✓. | `05_cm_all_checks.png` |
| 14 | "It's safe-by-default — dry-run makes zero device connections while proving the full pipeline, with an audit log." | `./bin/check_multi --dry-run -e lab platform examples/devices.txt` | Orchestration + audit, no SSH. | `02_cm_dryrun_platform.png` |
| 15 | "Operator-friendly: fuzzy 'did-you-mean'…" | `./bin/check_multi cert examples/devices.txt` | Suggests `certs`. | `03_cm_didyoumean.png` |
| 16 | "…and it validates its own inputs." | `./bin/check_multi -t abc platform examples/devices.txt` | Rejects bad thread count. | `04_cm_validation.png` |

---

## Act 3 — The executive artifact. ~1 min

| # | Say | Run | Show | Screenshot |
|---|-----|-----|------|-----------|
| 17 | "And a one-click executive report for the change ticket — per-device pass/fail, ready to attach." | `python scripts/generate_excel_report.py <summary.json> report.xlsx` | Styled `.xlsx` (in `files/`). | `18_excel_report.png` |

**Demo close:** *"Fast Bash sweep for breadth, deep Python validator for the go/no-go call, a signed audit trail for compliance, and an executive report for the change record. Read-only end to end — it can tell you not to upgrade, but it can never break anything."*

---

## Presenter tips (industry-standard demo hygiene)

- **Rehearse the failure first.** Scene 7 (NO-GO) is the most persuasive; make sure the mock's `degraded` server is up before you start.
- **Show exit codes.** In a terminal, `echo $?` after scenes 6/7 (0 vs 2) — it's what a pipeline actually keys on.
- **Pre-stage the mock** (README §Setup) and leave all three mock ports (18443/18444/18445) running for the whole demo.
- **Have the screenshots as backup.** If live output misbehaves, the `png/` contact sheet is your safety net — open `CONTACT_SHEET.html`.
- **Keep it read-only in the story.** The strongest selling point is that nothing here can change a device; lean on it.
- **Time-box Q&A on internals;** point deep questions at `qa-report/PRODUCTION_READINESS.md` (94% test coverage, static-analysis-clean).
