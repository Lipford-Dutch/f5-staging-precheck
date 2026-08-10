"""Offline tests for the capture/sanitization path (no live device needed)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bigip_precheck.capture import ENDPOINTS, capture_device, sanitize
from bigip_precheck.config.models import Device
from bigip_precheck.redaction import REDACTED

from .conftest import FakeRestClient
from .fixtures import icontrol as fx


def test_sanitize_redacts_secrets_and_replaces_host():
    payload = {
        "registrationKey": "AAAAA-BBBBB-CCCCC",
        "mgmtIp": "10.0.0.11",
        "note": "device bigip-a.lab.example.com is healthy",
    }
    out = sanitize(payload, {"10.0.0.11": "bigip.example.com",
                             "bigip-a.lab.example.com": "bigip.example.com"})
    assert out["registrationKey"] == REDACTED
    assert out["mgmtIp"] == "bigip.example.com"
    assert "10.0.0.11" not in json.dumps(out)
    assert "bigip-a.lab.example.com" not in json.dumps(out)


def test_capture_device_writes_available_endpoints(tmp_path: Path):
    dev = Device(name="d", host="10.0.0.11")
    client = FakeRestClient(dev, fx.HEALTHY_HA_STANDBY)
    # Include one endpoint the device does not answer to prove skips are tolerated.
    missing = "/mgmt/tm/gtm/topology/stats"
    results = capture_device(
        client, tmp_path,
        replacements={"10.0.0.11": "bigip.example.com"},
        endpoints=("/mgmt/tm/sys/version", missing),
    )
    assert results["/mgmt/tm/sys/version"] == "captured"
    assert (tmp_path / "mgmt_tm_sys_version.json").is_file()
    assert results[missing].startswith("skipped")  # absent endpoint → skipped, not fatal


def test_capture_covers_every_checker_endpoint():
    # The capture set must be a superset of what the checkers read, so a capture
    # always produces the fixtures the offline suite needs.
    assert "/mgmt/tm/sys/version" in ENDPOINTS
    assert "/mgmt/tm/gtm/datacenter/stats" in ENDPOINTS
    assert len(set(ENDPOINTS)) == len(ENDPOINTS)  # no duplicates


def test_capture_aborts_if_identifier_leaks(tmp_path: Path, monkeypatch):
    # If sanitize is bypassed and a raw IP survives, capture must refuse to finish.
    dev = Device(name="d", host="10.0.0.11")

    class LeakyClient(FakeRestClient):
        def get(self, path: str):
            return {"selfLink": "https://10.0.0.11/mgmt/tm/sys/version"}

    # Force sanitize to a no-op so the leak reaches disk and the guard trips.
    import bigip_precheck.capture as cap

    monkeypatch.setattr(cap, "sanitize", lambda payload, replacements: payload)
    with pytest.raises(RuntimeError, match="sanitization leak"):
        capture_device(
            LeakyClient(dev, {}), tmp_path,
            replacements={"10.0.0.11": "bigip.example.com"},
            endpoints=("/mgmt/tm/sys/version",),
        )
