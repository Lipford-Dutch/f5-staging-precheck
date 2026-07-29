"""Unit tests for the HA checkers."""

from __future__ import annotations

from bigip_precheck.checkers.ha import FailoverStatusChecker, SyncStatusChecker
from bigip_precheck.core.models import Status

from .fixtures import icontrol as fx


def test_failover_standby_pass(make_ctx):
    ctx = make_ctx({"/mgmt/tm/cm/failover-status": fx.FAILOVER_STANDBY})
    (res,) = FailoverStatusChecker().run(ctx)
    assert res.status is Status.PASS
    assert "STANDBY" in res.summary


def test_failover_yellow_warns(make_ctx):
    ctx = make_ctx({"/mgmt/tm/cm/failover-status": fx.FAILOVER_YELLOW})
    (res,) = FailoverStatusChecker().run(ctx)
    assert res.status is Status.WARN


def test_sync_in_sync_pass(make_ctx):
    ctx = make_ctx({"/mgmt/tm/cm/sync-status": fx.SYNC_IN_SYNC})
    (res,) = SyncStatusChecker().run(ctx)
    assert res.status is Status.PASS


def test_sync_changes_pending_fails(make_ctx):
    ctx = make_ctx({"/mgmt/tm/cm/sync-status": fx.SYNC_CHANGES_PENDING})
    (res,) = SyncStatusChecker().run(ctx)
    assert res.status is Status.FAIL


def test_sync_standalone_is_info(make_ctx):
    ctx = make_ctx({"/mgmt/tm/cm/sync-status": fx.SYNC_STANDALONE})
    (res,) = SyncStatusChecker().run(ctx)
    assert res.status is Status.INFO
