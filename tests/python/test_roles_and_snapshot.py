"""Tests for REST role auto-detection and the pre/post snapshot mechanism."""

from __future__ import annotations

from bigip_precheck.config.models import Device
from bigip_precheck.core.gate import Gate
from bigip_precheck.core.models import CheckResult, Role, Severity, Status
from bigip_precheck.core.orchestrator import detect_roles
from bigip_precheck.snapshot import (
    build_snapshot,
    diff_snapshots,
    load_snapshot,
    write_snapshot,
)

from .conftest import FakeRestClient
from .fixtures import icontrol as fx


# -- role detection --------------------------------------------------------
def test_configured_roles_win():
    dev = Device(name="d", host="1", roles=[Role.GTM])
    client = FakeRestClient(dev, {"/mgmt/tm/sys/provision": fx.PROVISION})
    assert detect_roles(dev, client) == frozenset({"GTM"})


def test_detect_from_provision():
    dev = Device(name="d", host="1")  # no roles configured
    client = FakeRestClient(dev, {"/mgmt/tm/sys/provision": fx.PROVISION})
    roles = detect_roles(dev, client)
    assert roles == frozenset({"LTM", "GTM"})  # PROVISION has ltm+gtm nominal


def test_detect_falls_back_to_ltm_on_error():
    dev = Device(name="d", host="1")
    client = FakeRestClient(dev, {})  # provision path missing → probe fails
    assert detect_roles(dev, client) == frozenset({"LTM"})


def test_detect_without_client_defaults_ltm():
    dev = Device(name="d", host="1")
    assert detect_roles(dev, None) == frozenset({"LTM"})


# -- snapshot build + diff -------------------------------------------------
def _obj_result(check: str, objects: list[dict[str, str]]) -> CheckResult:
    return CheckResult(
        check=check,
        status=Status.PASS,
        severity=Severity.INFO,
        summary="",
        device="d1",
        evidence={"objects": objects},
    )


def _verdict(results: list[CheckResult]):
    return Gate().evaluate({"d1": results})


def test_build_snapshot_harvests_objects():
    v = _verdict(
        [
            _obj_result(
                "ltm.virtual-servers",
                [{"name": "/Common/vs_web", "availability": "available", "enabled": "enabled",
                  "reason": ""}],
            )
        ]
    )
    snap = build_snapshot(v, session_id="s1")
    assert snap["devices"]["d1"]["ltm.virtual-servers"]["/Common/vs_web"]["availability"] == "available"


def test_diff_detects_regression_and_recovery():
    before = build_snapshot(
        _verdict(
            [
                _obj_result(
                    "ltm.virtual-servers",
                    [
                        {"name": "vs_a", "availability": "available", "enabled": "enabled", "reason": ""},
                        {"name": "vs_b", "availability": "offline", "enabled": "enabled", "reason": ""},
                    ],
                )
            ]
        ),
        session_id="pre",
    )
    after = build_snapshot(
        _verdict(
            [
                _obj_result(
                    "ltm.virtual-servers",
                    [
                        # vs_a regressed (available -> offline); vs_b recovered.
                        {"name": "vs_a", "availability": "offline", "enabled": "enabled", "reason": ""},
                        {"name": "vs_b", "availability": "available", "enabled": "enabled", "reason": ""},
                        {"name": "vs_c", "availability": "available", "enabled": "enabled", "reason": ""},
                    ],
                )
            ]
        ),
        session_id="post",
    )
    diff = diff_snapshots(before, after)
    assert diff.has_regressions
    assert [c.name for c in diff.regressions] == ["vs_a"]
    assert {c.name for c in diff.by_kind("recovery")} == {"vs_b"}
    assert {c.name for c in diff.by_kind("added")} == {"vs_c"}


def test_snapshot_roundtrip_on_disk(tmp_path):
    v = _verdict(
        [_obj_result("ltm.nodes", [{"name": "n1", "availability": "available", "enabled": "enabled", "reason": ""}])]
    )
    snap = build_snapshot(v, session_id="s")
    path = write_snapshot(snap, tmp_path / "snap.json")
    assert load_snapshot(path)["devices"]["d1"]["ltm.nodes"]["n1"]["availability"] == "available"


def test_diff_no_changes_when_identical():
    v = _verdict(
        [_obj_result("ltm.nodes", [{"name": "n1", "availability": "available", "enabled": "enabled", "reason": ""}])]
    )
    snap = build_snapshot(v, session_id="s")
    assert not diff_snapshots(snap, snap).has_regressions
    assert diff_snapshots(snap, snap).changes == []
