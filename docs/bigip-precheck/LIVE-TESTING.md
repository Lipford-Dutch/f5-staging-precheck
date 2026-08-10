# bigip-precheck — Live testing against a real BIG-IP

The default test suite is fully offline (synthesized fixtures). This guide covers
running **live** against a real device — validating the tool end-to-end and
capturing real payloads to harden the offline fixtures.

> **Where to run it.** `bigip-precheck` must reach the BIG-IP management interface
> over HTTPS (TCP/443). Run these commands from a machine that can route to your
> lab — the hypervisor host itself, or any workstation on the lab network. A
> cloud CI runner or sandbox on a different network cannot reach a private VE.

## 1. Prerequisites

- A reachable BIG-IP (this guide assumes a **standalone VE**, e.g. TMOS 17.x).
- An account with iControl REST access (admin, or a role that can GET the
  `/mgmt/tm/**` endpoints).
- Python 3.11+.

Install the tool in a virtualenv:

```bash
git clone https://github.com/willyd61/f5-staging-precheck.git
cd f5-staging-precheck
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
```

## 2. TLS note

A lab VE ships a **self-signed** management certificate. The example inventory
sets `verify_tls: false` so the client won't reject it. This disables certificate
verification for the management connection only — acceptable on a trusted lab
network, but install a trusted cert and set `verify_tls: true` for anything real.

## 3. Smoke it with the CLI

```bash
export BIGIP_DEFAULT_USERNAME=admin
export BIGIP_DEFAULT_PASSWORD='...'        # or: export BIGIP_DEFAULT_TOKEN=...

# Edit examples/bigip-precheck/lab-standalone.yaml → set `host` to your VE IP.
bigip-precheck validate-config examples/bigip-precheck/lab-standalone.yaml
bigip-precheck run examples/bigip-precheck/lab-standalone.yaml --profile standalone
```

You'll get a per-device table and a GO / NO-GO dashboard, plus a JSON report,
an object snapshot, and an audit log under `./results/bigip-precheck/`.

## 4. Run the live integration suite

The live pytest suite (`tests/live/`) authenticates to the device and asserts the
whole pipeline runs without any checker crashing. It is **skipped unless
`BIGIP_LIVE_HOST` is set**, so it never runs in normal CI.

```bash
export BIGIP_LIVE_HOST=192.168.1.245       # your VE mgmt IP
export BIGIP_LIVE_PORT=443                  # optional (default 443)
export BIGIP_LIVE_USERNAME=admin
export BIGIP_LIVE_PASSWORD='...'            # or BIGIP_LIVE_TOKEN=...
export BIGIP_LIVE_VERIFY_TLS=false          # self-signed VE

pytest tests/live -v -s
```

What it checks:

| Test | Asserts |
|------|---------|
| `test_connect_and_version` | Token login works; `/sys/version` returns a real TMOS version. |
| `test_role_autodetection_returns_ltm` | Roles are inferred from `/sys/provision` (LTM present). |
| `test_all_checkers_run_without_crashing` | Every applicable checker returns results — never a `Source.INTERNAL` crash. |
| `test_ha_sync_status_is_sane_on_standalone` | `ha.sync-status` reports `Standalone` (INFO) on a solo VE. |
| `test_full_orchestrator_run_reaches_decision` | Real credential resolution + client + orchestration → a GO/NO-GO verdict and on-disk artifacts. |

`-s` prints the live version, detected roles, and each check's verdict so you can
eyeball the device state.

## 5. Capture real payloads as fixtures

Turn your device's real responses into sanitized fixtures. The `capture` command
issues only GETs, then scrubs secrets (passwords, tokens, `registrationKey`) and
your device's host/IP before writing anything to disk — and aborts if any raw
identifier would survive.

```bash
bigip-precheck capture examples/bigip-precheck/lab-standalone.yaml -o ./captures
```

This writes one JSON file per endpoint under `./captures/`. Review them, then, to
replace a synthesized fixture with real data, copy the relevant payload into
`tests/python/fixtures/icontrol.py` under the same constant name. The offline
tests that consume it keep passing unchanged.

## Pre-verified

Before shipping, the live harness and `capture` command were validated end-to-end
against a local self-signed HTTPS iControl emulator (token login, version probe,
all system/HA/LTM/GTM checkers, the full orchestrator run, and sanitized capture
of all 17 endpoints). Your first real run is exercising verified code paths.
