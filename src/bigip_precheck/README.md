# bigip-precheck

**Read-only pre-upgrade / change-window readiness validator for F5 BIG-IP (LTM & GTM).**

`bigip-precheck` is the Python companion to the Bash `check_multi` tool in this
repository. Where `check_multi` runs fast SSH/tmsh sweeps, `bigip-precheck` is a
deeper, **iControl REST**–driven validator that answers one question before a
maintenance window: **is this device safe to upgrade — GO or NO-GO?**

It is **read-only**: it never mutates a device. Every run is fully audit-logged,
and the design bias is that a check which cannot confirm health degrades to
`WARN`/`FAIL` — never a silent `PASS`.

> Status: **phase B (alpha)** — System + HA + **LTM + GTM** object-state checks
> over iControl REST, with **REST role auto-detection** and **pre/post object
> snapshots**. The SNMP cross-check layer lands in phase C (see the roadmap).

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

## Checks

| Check | Severity | Role | Purpose |
|-------|----------|------|---------|
| `system.version`        | HIGH     | any | Report running TMOS version/build. |
| `system.license`        | CRITICAL | any | Licensed + service-check date valid (K7727). |
| `system.provisioning`   | MEDIUM   | any | Provisioned modules and levels. |
| `system.boot-volumes`   | HIGH     | any | A free install target exists; nothing mid-install. |
| `ha.failover-status`    | HIGH     | any | Failover role (Active/Standby) + traffic-group health. |
| `ha.sync-status`        | HIGH     | any | Config-sync is In Sync (depends on failover-status). |
| `ltm.virtual-servers`   | HIGH     | LTM | Snapshot VS availability; flag offline-while-enabled. |
| `ltm.pools`             | HIGH     | LTM | Pool availability + zero-active-member detection. |
| `ltm.nodes`             | MEDIUM   | LTM | Node availability snapshot. |
| `gtm.wide-ips`          | HIGH     | GTM | Wide IP availability across A/AAAA/CNAME. |
| `gtm.pools`             | HIGH     | GTM | GTM pool availability across A/AAAA/CNAME. |
| `gtm.servers`           | HIGH     | GTM | GTM server availability. |
| `gtm.datacenters`       | MEDIUM   | GTM | Datacenter availability. |

Checks are **role-filtered per device**. Roles come from the inventory when set,
otherwise they are **auto-detected** from `/sys/provision` (LTM/GTM), falling
back to LTM if the probe is unavailable.

## Pre/post object snapshots

Every `run` writes `snapshot-<session>.json` capturing each LTM/GTM object's
availability. Compare a post-change run against a pre-change baseline:

```bash
# Before the change:
bigip-precheck run inventory.yaml --profile full -o ./pre
# After the change — regressions vs the baseline force NO-GO:
bigip-precheck run inventory.yaml --profile full -o ./post \
    --baseline ./pre/snapshot-<id>.json

# Or compare two snapshots directly (exit 2 if anything regressed):
bigip-precheck diff ./pre/snapshot-A.json ./post/snapshot-B.json
```

A **regression** is an object that was available/enabled in the baseline and no
longer is; recoveries, additions and removals are reported but don't block.

## Configuration

See [`examples/bigip-precheck/inventory.yaml`](../../examples/bigip-precheck/inventory.yaml).
Devices reference a `credential` by name; the secret is resolved at runtime from
`BIGIP_<CRED>_USERNAME` / `BIGIP_<CRED>_PASSWORD` (or `BIGIP_<CRED>_TOKEN`), with
`BIGIP_USERNAME` / `BIGIP_PASSWORD` as a fallback. HA members that share an
`ha:<group>` tag are evaluated **standby before active**.

## Live testing against a real device

The default suite is offline. To validate against a real BIG-IP (e.g. a
standalone VE on a hypervisor) and capture real payloads as fixtures, see
[`docs/bigip-precheck/LIVE-TESTING.md`](../../docs/bigip-precheck/LIVE-TESTING.md):

```bash
# Run the env-gated live integration suite (skipped unless BIGIP_LIVE_HOST is set):
export BIGIP_LIVE_HOST=192.168.1.245 BIGIP_LIVE_USERNAME=admin BIGIP_LIVE_PASSWORD=... BIGIP_LIVE_VERIFY_TLS=false
pytest tests/live -v -s

# Capture sanitized payloads from the device for use as fixtures:
bigip-precheck capture examples/bigip-precheck/lab-standalone.yaml -o ./captures
```

Run these from a machine that can reach the device's management interface.

## Roadmap

* **PR A** ✅ — System + HA checks, REST client, gate, CLI, audit.
* **PR B** ✅ — LTM + GTM object-state checks, role auto-detection, pre/post snapshots.
* **PR C** — SNMP layer and REST↔SNMP cross-checks (catch single-source blind spots).
* **PR D** — HTML/Markdown reports, report signing, TMSH `load sys config verify`.

See [`docs/bigip-precheck/TESTING.md`](../../docs/bigip-precheck/TESTING.md) for the
test strategy and how synthesized fixtures are replaced with real captures.
