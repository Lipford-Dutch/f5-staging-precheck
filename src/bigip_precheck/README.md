# bigip-precheck

**Read-only pre-upgrade / change-window readiness validator for F5 BIG-IP (LTM & GTM).**

`bigip-precheck` is the Python companion to the Bash `check_multi` tool in this
repository. Where `check_multi` runs fast SSH/tmsh sweeps, `bigip-precheck` is a
deeper, **iControl REST**–driven validator that answers one question before a
maintenance window: **is this device safe to upgrade — GO or NO-GO?**

It is **read-only**: it never mutates a device. Every run is fully audit-logged,
and the design bias is that a check which cannot confirm health degrades to
`WARN`/`FAIL` — never a silent `PASS`.

> Status: **phase A (alpha)** — System + HA checks over iControl REST. LTM/GTM
> checks and the SNMP cross-check layer land in later phases (see the roadmap).

## Install

```bash
pip install -e '.[dev]'      # from the repository root
```

## Quick start

```bash
# Validate an inventory file offline (no device contact):
bigip-precheck validate-config examples/bigip-precheck/inventory.yaml

# List the available checks:
bigip-precheck list-checks

# Supply credentials via the environment (never stored in the inventory):
export BIGIP_DEFAULT_USERNAME=admin
export BIGIP_DEFAULT_PASSWORD='...'

# Run the "full" profile and print a GO/NO-GO dashboard:
bigip-precheck run examples/bigip-precheck/inventory.yaml --profile full

# CI mode: non-interactive, JSON report to stdout, non-zero exit on NO-GO:
bigip-precheck run inventory.yaml --profile full --ci --json
```

## Exit codes

| Code | Meaning                                             |
|------|-----------------------------------------------------|
| `0`  | GO — every device is clear to proceed.              |
| `2`  | NO-GO — at least one device has a blocking result.  |
| `3`  | Config error — the run could not start.             |

## Checks (phase A)

| Check | Severity | Source | Purpose |
|-------|----------|--------|---------|
| `system.version`        | HIGH     | REST | Report running TMOS version/build. |
| `system.license`        | CRITICAL | REST | Licensed + service-check date valid (K7727). |
| `system.provisioning`   | MEDIUM   | REST | Provisioned modules and levels. |
| `system.boot-volumes`   | HIGH     | REST | A free install target exists; nothing mid-install. |
| `ha.failover-status`    | HIGH     | REST | Failover role (Active/Standby) + traffic-group health. |
| `ha.sync-status`        | HIGH     | REST | Config-sync is In Sync (depends on failover-status). |

## Configuration

See [`examples/bigip-precheck/inventory.yaml`](../../examples/bigip-precheck/inventory.yaml).
Devices reference a `credential` by name; the secret is resolved at runtime from
`BIGIP_<CRED>_USERNAME` / `BIGIP_<CRED>_PASSWORD` (or `BIGIP_<CRED>_TOKEN`), with
`BIGIP_USERNAME` / `BIGIP_PASSWORD` as a fallback. HA members that share an
`ha:<group>` tag are evaluated **standby before active**.

## Roadmap

* **PR B** — LTM + GTM object-state checks with pre/post snapshots.
* **PR C** — SNMP layer and REST↔SNMP cross-checks (catch single-source blind spots).
* **PR D** — HTML/Markdown reports, report signing, TMSH `load sys config verify`.

See [`docs/bigip-precheck/TESTING.md`](../../docs/bigip-precheck/TESTING.md) for the
test strategy and how synthesized fixtures are replaced with real captures.
