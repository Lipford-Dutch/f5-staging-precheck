"""Unit tests for the LTM object-state checkers."""

from __future__ import annotations

from bigip_precheck.checkers.ltm import NodeChecker, PoolChecker, VirtualServerChecker
from bigip_precheck.core.exceptions import ConnectionFailed
from bigip_precheck.core.models import Status

from .fixtures import icontrol as fx


def _statuses(results):
    return [r.status for r in results]


def test_virtual_servers_all_available(make_ctx):
    ctx = make_ctx({"/mgmt/tm/ltm/virtual/stats": fx.VS_STATS_HEALTHY})
    results = VirtualServerChecker().run(ctx)
    assert results[0].status is Status.PASS
    assert results[0].evidence["objects"]  # snapshot recorded for pre/post diff


def test_virtual_servers_offline_while_enabled_fails(make_ctx):
    ctx = make_ctx({"/mgmt/tm/ltm/virtual/stats": fx.VS_STATS_DOWN})
    results = VirtualServerChecker().run(ctx)
    assert results[0].status is Status.FAIL  # aggregate
    # A per-object FAIL names the offending VS; the disabled one is not a FAIL.
    fails = [r for r in results if r.status is Status.FAIL]
    assert any("vs_api" in r.summary for r in fails)
    assert not any("vs_old" in r.summary for r in fails)


def test_virtual_servers_read_error_fails(make_ctx):
    ctx = make_ctx({"/mgmt/tm/ltm/virtual/stats": ConnectionFailed("boom")})
    results = VirtualServerChecker().run(ctx)
    assert results[0].status is Status.FAIL


def test_pool_zero_active_members_fails(make_ctx):
    ctx = make_ctx({"/mgmt/tm/ltm/pool/stats": fx.POOL_STATS_NO_MEMBERS})
    results = PoolChecker().run(ctx)
    assert any(r.status is Status.FAIL and "0 active members" in r.summary for r in results)


def test_pool_healthy_pass(make_ctx):
    ctx = make_ctx({"/mgmt/tm/ltm/pool/stats": fx.POOL_STATS_HEALTHY})
    results = PoolChecker().run(ctx)
    assert results[0].status is Status.PASS
    assert not any(r.status is Status.FAIL for r in results)


def test_nodes_healthy_pass(make_ctx):
    ctx = make_ctx({"/mgmt/tm/ltm/node/stats": fx.NODE_STATS_HEALTHY})
    results = NodeChecker().run(ctx)
    assert results[0].status is Status.PASS
