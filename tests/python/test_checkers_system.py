"""Unit tests for the system checkers."""

from __future__ import annotations

from bigip_precheck.checkers.system import (
    BootVolumeChecker,
    LicenseChecker,
    ProvisioningChecker,
    VersionChecker,
)
from bigip_precheck.core.exceptions import ConnectionFailed
from bigip_precheck.core.models import Status

from .fixtures import icontrol as fx


def test_version_pass(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/version": fx.VERSION})
    (res,) = VersionChecker().run(ctx)
    assert res.status is Status.PASS
    assert "17.5.1.8" in res.summary  # fixture mirrors a real TMOS 17.5.1.8 device


def test_version_client_error_fails_not_passes(make_ctx):
    # Bias check: an unreadable version must FAIL, never silently PASS.
    ctx = make_ctx({"/mgmt/tm/sys/version": ConnectionFailed("boom")})
    (res,) = VersionChecker().run(ctx)
    assert res.status is Status.FAIL


def test_license_ok(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/license": fx.LICENSE_OK})
    (res,) = LicenseChecker().run(ctx)
    assert res.status is Status.PASS


def test_license_expired_fails(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/license": fx.LICENSE_EXPIRED})
    (res,) = LicenseChecker().run(ctx)
    assert res.status is Status.FAIL
    assert res.reference == "K7727"


def test_license_unlicensed_fails(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/license": fx.LICENSE_UNLICENSED})
    (res,) = LicenseChecker().run(ctx)
    assert res.status is Status.FAIL


def test_provisioning_lists_modules(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/provision": fx.PROVISION})
    (res,) = ProvisioningChecker().run(ctx)
    assert res.status is Status.PASS
    assert "ltm" in res.summary and "gtm" in res.summary
    assert "afm" not in res.evidence["provisioned"]  # level none excluded


def test_boot_volumes_ok(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/software/volume": fx.BOOT_VOLUMES})
    (res,) = BootVolumeChecker().run(ctx)
    assert res.status is Status.PASS
    assert "HD1.2" in res.summary


def test_boot_volumes_single_warns(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/software/volume": fx.BOOT_VOLUMES_SINGLE})
    (res,) = BootVolumeChecker().run(ctx)
    assert res.status is Status.WARN


def test_boot_volumes_installing_fails(make_ctx):
    ctx = make_ctx({"/mgmt/tm/sys/software/volume": fx.BOOT_VOLUMES_INSTALLING})
    (res,) = BootVolumeChecker().run(ctx)
    assert res.status is Status.FAIL
    assert "install" in res.summary.lower()
