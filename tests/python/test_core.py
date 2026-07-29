"""Tests for registry ordering, the gate, orchestration and redaction."""

from __future__ import annotations

import pytest

from bigip_precheck.checkers import build_default_registry
from bigip_precheck.checkers.base import Checker
from bigip_precheck.config.models import Device, Inventory, Settings, Thresholds
from bigip_precheck.core.exceptions import ConfigError
from bigip_precheck.core.gate import Decision, Gate
from bigip_precheck.core.models import CheckResult, Role, Severity, Status
from bigip_precheck.core.orchestrator import Orchestrator, group_devices
from bigip_precheck.core.registry import Registry
from bigip_precheck.redaction import REDACTED, redact

from .conftest import FakeRestClient
from .fixtures import icontrol as fx


# -- registry --------------------------------------------------------------
def test_registry_orders_dependencies_first():
    reg = build_default_registry()
    ordered = [c.name for c in reg.select(["ha.sync-status"])]
    # sync-status depends on failover-status, which must be pulled in and precede it.
    assert ordered.index("ha.failover-status") < ordered.index("ha.sync-status")


def test_registry_unknown_check_raises():
    reg = build_default_registry()
    with pytest.raises(ConfigError):
        reg.select(["does.not.exist"])


def test_registry_detects_cycle():
    class A(Checker):
        name = "a"
        depends_on = ("b",)

        def run(self, ctx):  # pragma: no cover - never run
            return []

    class B(Checker):
        name = "b"
        depends_on = ("a",)

        def run(self, ctx):  # pragma: no cover - never run
            return []

    reg = Registry()
    reg.register(A())
    reg.register(B())
    with pytest.raises(ConfigError, match="cycle"):
        reg.select(None)


# -- gate ------------------------------------------------------------------
def _r(status: Status, sev: Severity = Severity.HIGH) -> CheckResult:
    return CheckResult(check="x", status=status, severity=sev, summary="", device="d")


def test_gate_go_when_all_pass():
    v = Gate().evaluate({"d": [_r(Status.PASS), _r(Status.WARN)]})
    assert v.decision is Decision.GO


def test_gate_no_go_on_fail():
    v = Gate().evaluate({"d": [_r(Status.PASS), _r(Status.FAIL)]})
    assert v.decision is Decision.NO_GO


def test_gate_strict_blocks_high_warn():
    v = Gate(warn_is_blocking=True).evaluate({"d": [_r(Status.WARN, Severity.HIGH)]})
    assert v.decision is Decision.NO_GO
    v2 = Gate(warn_is_blocking=True).evaluate({"d": [_r(Status.WARN, Severity.LOW)]})
    assert v2.decision is Decision.GO


# -- ordering --------------------------------------------------------------
def test_group_devices_standby_before_active():
    a = Device(name="a", host="1", tags=["ha:p1", "active"])
    b = Device(name="b", host="2", tags=["ha:p1", "standby"])
    groups = group_devices([a, b])
    assert len(groups) == 1
    assert [d.name for d in groups[0].devices] == ["b", "a"]  # standby first


# -- orchestrator ----------------------------------------------------------
def _inv(devices: list[Device]) -> Inventory:
    return Inventory(settings=Settings(max_workers=4), thresholds=Thresholds(), devices=devices)


def test_orchestrator_runs_and_skips_dependents(make_ctx):
    dev = Device(name="d1", host="1")
    inv = _inv([dev])
    reg = build_default_registry()
    # sync-status query raises -> failover fine, but simulate failover failing so
    # sync-status is SKIPPED (dependency failed).
    responses = dict(fx.HEALTHY_HA_STANDBY)
    responses["/mgmt/tm/cm/failover-status"] = fx.FAILOVER_YELLOW  # WARN, not FAIL

    def factory(device, cred):
        return FakeRestClient(device, responses)

    orch = Orchestrator(inv, reg.select(None), client_factory=factory, allow_prompt=False)
    # Provide creds via env-free token path: monkeypatch resolve via a token cred.
    import os

    os.environ["BIGIP_DEFAULT_TOKEN"] = "tok"
    try:
        results = orch.run("sess")
    finally:
        del os.environ["BIGIP_DEFAULT_TOKEN"]
    names = {r.check: r.status for r in results["d1"]}
    assert names["system.version"] is Status.PASS
    assert names["ha.sync-status"] is Status.PASS  # failover WARN does not block dependents


def test_orchestrator_missing_credential_is_fatal_fail():
    dev = Device(name="d1", host="1", credential="nope")
    inv = _inv([dev])
    reg = build_default_registry()

    def factory(device, cred):  # pragma: no cover - never reached
        return FakeRestClient(device, {})

    orch = Orchestrator(inv, reg.select(None), client_factory=factory, allow_prompt=False)
    results = orch.run("sess")
    assert results["d1"][0].status is Status.FAIL
    assert results["d1"][0].check == "device.connect"


# -- redaction -------------------------------------------------------------
def test_redaction_scrubs_keys_and_text():
    data = {
        "password": "hunter2",
        "nested": {"token": "abc", "ok": "value"},
        "line": "X-F5-Auth-Token: SECRETTOKEN",
        "list": [{"community": "public"}],
    }
    out = redact(data)
    assert out["password"] == REDACTED
    assert out["nested"]["token"] == REDACTED
    assert out["nested"]["ok"] == "value"
    assert "SECRETTOKEN" not in out["line"]
    assert out["list"][0]["community"] == REDACTED


def test_checker_applies_role_filter():
    class GtmOnly(Checker):
        name = "g"
        applies_to = frozenset({Role.GTM})

        def run(self, ctx):  # pragma: no cover
            return []

    c = GtmOnly()
    assert c.applies(frozenset({"GTM"}))
    assert not c.applies(frozenset({"LTM"}))
