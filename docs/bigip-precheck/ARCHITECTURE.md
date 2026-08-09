# bigip-precheck — Architecture

`bigip-precheck` is the Python, iControl REST–driven upgrade-readiness validator
that complements the Bash `check_multi` tool. This document describes the phase-A
design; later phases (SNMP cross-checks, LTM/GTM object checks, richer reports)
slot into the same seams.

## Design principles

1. **Read-only.** Nothing mutates a device. There is no flag that changes device
   state in this release.
2. **Never a silent PASS.** Any check that cannot *positively* confirm health
   degrades to `WARN`/`FAIL`. Unexpected exceptions in a checker become a `FAIL`,
   not a dropped result (`checkers.base.timed`).
3. **Auditable.** Every run has a session ID and an append-only, redacted audit
   trail; the JSON report gets a SHA-256 sidecar.
4. **Testable without a lab.** Checkers depend on a `RestClient` *protocol*, so
   the whole pipeline runs against synthesized fixtures.

## Layers

```
CLI (Typer)
  └─ load_inventory ──────────────► config/ (Pydantic models, secret-free)
  └─ build_default_registry ──────► checkers/ (system, ha, ltm, gtm; SNMP later)
  └─ Orchestrator
        ├─ group_devices ─────────► standby-before-active ordering per HA group
        ├─ RestClient (per device) ► clients/rest.py (token, retry, version probe)
        └─ Checker.run(RunContext) ► CheckResult[]
  └─ Gate ────────────────────────► per-device + overall GO / NO-GO
  └─ reporting/ ──────────────────► Rich console + schema-versioned JSON
  └─ logging/ ────────────────────► audit JSONL + human log + integrity hash
```

## Key abstractions

| Type | Responsibility |
|------|----------------|
| `CheckResult` | Immutable observation: status, severity, summary, redacted evidence, source. |
| `Checker` (ABC) | Declares metadata (`name`, `severity`, `applies_to`, `depends_on`) and `run()`. |
| `Registry` | Registration, profile filtering, and topological ordering by dependency. |
| `RunContext` | Per-device bundle: device, client, thresholds, detected roles, session id. |
| `Orchestrator` | Groups/orders devices, runs checkers, skips dependents of failed checks. |
| `Gate` | Aggregates results into GO / NO-GO (default: any FAIL blocks; `--strict` adds HIGH+ WARN). |

## Ordering guarantees

* **Standby before active.** Devices sharing an `ha:<group>` tag run sequentially,
  standby member first (`orchestrator.group_devices`). Distinct groups and
  standalone devices run concurrently up to `settings.max_workers`.
* **Dependency-aware skips.** A checker whose `depends_on` target FAILed on a
  device is recorded as an explicit `SKIP`, never silently omitted.

## Secrets

Secrets never enter the config models. A device names a `credential`; the value
is resolved at run time from `BIGIP_<CRED>_USERNAME` / `_PASSWORD` / `_TOKEN`
(with `BIGIP_USERNAME` / `BIGIP_PASSWORD` fallback). All log/report output passes
through `redaction.redact` first.

## Exit codes

`0` GO · `2` NO-GO · `3` config error. `--ci` makes runs non-interactive and
machine-readable; `--json` prints the report to stdout.

## Object snapshots (phase B)

LTM/GTM checkers record each object's availability in
`CheckResult.evidence["objects"]`. `snapshot.build_snapshot` harvests these into
a schema-versioned document written on every run; `snapshot.diff_snapshots`
classifies per-object changes (regression / recovery / added / removed / changed)
between a baseline and a later run. `run --baseline` forces NO-GO on any
regression, and the `diff` command compares two snapshots directly.

Role filtering: `orchestrator.detect_roles` keeps configured `device.roles`, else
probes `/sys/provision` to infer LTM/GTM, falling back to LTM.

## Roadmap seams

* **PR A** ✅ / **PR B** ✅ (this phase).
* **PR C** — `clients/snmp.py` + `checkers/snmp_crosscheck.py`; REST↔SNMP
  discrepancy gating.
* **PR D** — HTML/Markdown reports; report signing; TMSH `load sys config verify`
  escape hatch.
