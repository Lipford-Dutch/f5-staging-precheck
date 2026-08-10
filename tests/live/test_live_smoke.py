"""Live smoke tests against a real BIG-IP (skipped unless BIGIP_LIVE_HOST is set).

These assert the *contract*, not specific device state: the tool must connect,
parse real payloads, and reach a GO/NO-GO decision without any checker crashing
(a crash surfaces as Source.INTERNAL — the one thing that must never happen).
The actual PASS/WARN/FAIL mix depends on the lab and is printed for the operator.
"""

from __future__ import annotations

import pytest

from bigip_precheck.checkers import build_default_registry
from bigip_precheck.checkers.base import timed
from bigip_precheck.config.models import Inventory
from bigip_precheck.core.gate import Gate
from bigip_precheck.core.models import Source, Status
from bigip_precheck.core.orchestrator import Orchestrator, detect_roles

pytestmark = pytest.mark.live


def test_connect_and_version(live_client):
    version = live_client.tmos_version
    assert version, "expected a non-empty TMOS version from /sys/version"
    assert version[0].isdigit(), f"unexpected version string: {version!r}"
    print(f"\nLive device TMOS version: {version}")


def test_role_autodetection_returns_ltm(live_device, live_client):
    roles = detect_roles(live_device, live_client)
    assert roles, "role detection returned nothing"
    # A standalone LTM VE always has ltm provisioned.
    assert "LTM" in roles, f"expected LTM in detected roles, got {sorted(roles)}"
    print(f"\nDetected roles: {sorted(roles)}")


def test_all_checkers_run_without_crashing(live_ctx):
    """Every applicable checker must return results, never raise (no Source.INTERNAL)."""
    registry = build_default_registry()
    internal_failures = []
    summary = []
    for checker in registry.all():
        if not checker.applies(live_ctx.detected_roles):
            continue
        for r in timed(checker, live_ctx):
            summary.append(f"{r.check}: {r.status.value} ({r.severity.value}) — {r.summary}")
            if r.source is Source.INTERNAL and r.status is Status.FAIL:
                internal_failures.append(r)
    print("\n".join(["", *summary]))
    assert not internal_failures, (
        "checker(s) crashed instead of reporting: "
        + ", ".join(f"{r.check}: {r.summary}" for r in internal_failures)
    )


def test_ha_sync_status_is_sane_on_standalone(live_ctx):
    from bigip_precheck.checkers.ha import SyncStatusChecker

    (res,) = SyncStatusChecker().run(live_ctx)
    assert res.source is Source.REST
    # On a standalone VE this is INFO (Standalone); in an HA lab it's PASS/FAIL.
    assert res.status in {Status.INFO, Status.PASS, Status.WARN, Status.FAIL}
    print(f"\nha.sync-status → {res.status.value}: {res.summary}")


def test_full_orchestrator_run_reaches_decision(live_device, live_settings, tmp_path):
    """End-to-end via the real production path: credential resolution + default
    client factory + orchestration → GO/NO-GO verdict and on-disk artifacts."""
    from bigip_precheck.reporting import build_report, write_report
    from bigip_precheck.snapshot import build_snapshot, write_snapshot

    inv = Inventory(settings=live_settings, devices=[live_device])
    registry = build_default_registry()

    # No injected factory: this uses IControlRestClient + resolve_credential
    # (credentials mirrored from BIGIP_LIVE_* by the autouse fixture).
    orch = Orchestrator(inv, registry.all(), allow_prompt=False)
    results = orch.run("live-e2e")
    verdict = Gate().evaluate(results)

    device_results = results[live_device.name]
    assert device_results, "no results produced for the live device"
    assert all(r.status in set(Status) for r in device_results)
    # No checker may crash on real data.
    assert not [r for r in device_results if r.source is Source.INTERNAL and r.status is Status.FAIL]

    report = build_report(verdict, session_id="live-e2e", profile="(all)", inventory_path="live")
    report_path = write_report(report, tmp_path / "live-report.json")
    snap_path = write_snapshot(build_snapshot(verdict, session_id="live-e2e"), tmp_path / "live-snap.json")
    print(f"\nDecision: {verdict.decision.value}")
    print(f"Report:   {report_path}")
    print(f"Snapshot: {snap_path}")
