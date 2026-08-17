"""Edge-branch tests for the system checkers: WARN paths, date parsing, and the
'cannot confirm -> never a silent PASS' bias on unreadable responses."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from bigip_precheck.checkers.system import (
    BootVolumeChecker,
    LicenseChecker,
    ProvisioningChecker,
    VersionChecker,
    _parse_bigip_date,
)
from bigip_precheck.core.exceptions import ConnectionFailed
from bigip_precheck.core.models import Status

from .fixtures.icontrol import _stats


def _license_payload(service_date: str, licensed_on: str = "2025/01/15") -> dict:
    return _stats({"licensedOn": licensed_on, "serviceCheckDate": service_date})


def test_license_near_expiry_warns(make_ctx):
    # Within the default 30-day warn window but not past.
    soon = (datetime.now(UTC) + timedelta(days=5)).strftime("%Y/%m/%d")
    ctx = make_ctx({"/mgmt/tm/sys/license": _license_payload(soon)})
    (res,) = LicenseChecker().run(ctx)
    assert res.status is Status.WARN
    assert res.reference == "K7727"


def test_license_far_future_passes(make_ctx):
    far = (datetime.now(UTC) + timedelta(days=400)).strftime("%Y/%m/%d")
    ctx = make_ctx({"/mgmt/tm/sys/license": _license_payload(far)})
    (res,) = LicenseChecker().run(ctx)
    assert res.status is Status.PASS


def test_license_unparseable_service_date_warns(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/license": _license_payload("not-a-date")})
    (res,) = LicenseChecker().run(ctx)
    assert res.status is Status.WARN
    assert "unpar" in res.summary.lower()


def test_license_client_error_fails(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/license": ConnectionFailed("boom")})
    (res,) = LicenseChecker().run(ctx)
    assert res.status is Status.FAIL


def test_parse_bigip_date_supported_formats():
    assert _parse_bigip_date("2027/01/15") == datetime(2027, 1, 15, tzinfo=UTC)
    assert _parse_bigip_date("2027-01-15") == datetime(2027, 1, 15, tzinfo=UTC)
    assert _parse_bigip_date("Jan 15, 2027") == datetime(2027, 1, 15, tzinfo=UTC)
    assert _parse_bigip_date("Fri Jan 15 00:00:00 2027") == datetime(2027, 1, 15, tzinfo=UTC)


def test_parse_bigip_date_rejects_garbage_and_empty():
    assert _parse_bigip_date("") is None
    assert _parse_bigip_date("   ") is None
    assert _parse_bigip_date("15/01/2027") is None  # unsupported order


def test_version_empty_entries_warns(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/version": {"entries": {}}})
    (res,) = VersionChecker().run(ctx)
    assert res.status is Status.WARN


def test_provisioning_none_warns(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/provision": {"items": [{"name": "ltm", "level": "none"}]}})
    (res,) = ProvisioningChecker().run(ctx)
    assert res.status is Status.WARN
    assert res.evidence["provisioned"] == {}


def test_provisioning_client_error_warns_not_fail(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/provision": ConnectionFailed("x")})
    (res,) = ProvisioningChecker().run(ctx)
    assert res.status is Status.WARN


def test_boot_volumes_empty_warns(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/software/volume": {"items": []}})
    (res,) = BootVolumeChecker().run(ctx)
    assert res.status is Status.WARN


def test_boot_volumes_client_error_warns(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/software/volume": ConnectionFailed("x")})
    (res,) = BootVolumeChecker().run(ctx)
    assert res.status is Status.WARN
