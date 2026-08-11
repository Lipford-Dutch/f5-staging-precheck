# bigip-precheck — Testing strategy

The suite runs entirely offline: no BIG-IP, no network. It lives under
`tests/python/` and is driven by `pytest`.

```bash
pip install -e '.[dev]'
pytest                               # run the suite
pytest --cov=bigip_precheck          # with coverage
ruff check src tests                 # lint
mypy                                 # strict type check
```

## Layers under test

| Layer | How it is tested |
|-------|------------------|
| Checkers (`system`, `ha`) | Unit tests with a `FakeRestClient` fed synthesized iControl payloads. |
| REST client | `httpx.MockTransport` scripts login / 401-refresh / 5xx-retry / version probe — no sockets. |
| Registry / gate / orchestrator | Dependency ordering, GO/NO-GO policy, standby-first grouping, dependent-skip. |
| Config | Inventory validation, duplicate/unknown-field rejection, credential resolution. |
| Logging | Audit JSONL redaction; report SHA-256 round-trip and tamper detection. |
| CLI | `typer.testing.CliRunner`: exit codes, report + digest artefacts, JSON output. |

## The "never a silent PASS" bias, tested explicitly

`test_checkers_system.py::test_version_client_error_fails_not_passes` asserts that
an unreadable device produces a `FAIL`, not a `PASS`. New checkers should add the
equivalent negative test: when the device cannot be read, the result must not be
`PASS`.

## Fixtures

`tests/python/fixtures/icontrol.py` holds hand-built payloads that mirror the
shapes TMOS 15.1–17.x return (collections with `items`, stats with the
`entries → nestedStats → entries → description` envelope). They are synthesized
from public F5 schemas so the suite needs no lab.

**Replacing fixtures with real captures:** sanitize a real
`GET /mgmt/tm/...` response (scrub hostnames, keys, tokens), drop it into
`icontrol.py` under the same constant name, and the consuming tests continue to
pass unchanged. Keep one healthy and one unhealthy variant per check so both the
GO and NO-GO paths stay covered.

## Scenario matrix

Phase A: standalone (sync = Standalone → INFO), HA standby, HA active, expired
license, config-sync changes-pending, single boot volume, install-in-progress,
unreadable/timed-out REST.

Phase B: virtual servers/pools/nodes all-available vs offline-while-enabled vs
disabled; pool with zero active members; wide IPs/pools across A/AAAA/CNAME with
some record types absent (tolerated) vs all endpoints erroring (fails); role
auto-detection from `/sys/provision` and its LTM fallback; snapshot build,
on-disk round-trip, and regression/recovery/added/removed diffing including the
`run --baseline` and `diff` CLI paths.

Unprovisioned modules: every GTM endpoint returning HTTP 404 on an LTM-only
device must read as `INFO` (absent), while a genuine read error (auth, timeout,
5xx) on the same endpoint must still `FAIL` — see `test_not_provisioned.py`.

The SNMP-down and mixed-version cases arrive with PR C.

## Fixtures verified against real hardware

`VERSION`, `PROVISION_LTM_ONLY`, `NODE_STATS_UNKNOWN` and `STANDALONE_LTM_ONLY`
mirror a real BIG-IP VE running **TMOS 17.5.1.8** (LTM-only, standalone). The
`STANDALONE_LTM_ONLY` map deliberately omits every `/mgmt/tm/gtm/**` path so the
fake client 404s on them, reproducing that device exactly.
