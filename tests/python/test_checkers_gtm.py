"""Unit tests for the GTM object-state checkers."""

from __future__ import annotations

from bigip_precheck.checkers.gtm import (
    DatacenterChecker,
    GtmPoolChecker,
    GtmServerChecker,
    WideIpChecker,
)
from bigip_precheck.core.exceptions import ConnectionFailed
from bigip_precheck.core.models import Status

from .fixtures import icontrol as fx


def test_wide_ips_healthy_across_types(make_ctx):
    ctx = make_ctx(
        {
            "/mgmt/tm/gtm/wideip/a/stats": fx.WIDEIP_A_HEALTHY,
            "/mgmt/tm/gtm/wideip/aaaa/stats": fx.EMPTY_STATS,
            "/mgmt/tm/gtm/wideip/cname/stats": fx.EMPTY_STATS,
        }
    )
    results = WideIpChecker().run(ctx)
    assert results[0].status is Status.PASS


def test_wide_ips_offline_fails(make_ctx):
    ctx = make_ctx(
        {
            "/mgmt/tm/gtm/wideip/a/stats": fx.WIDEIP_A_DOWN,
            "/mgmt/tm/gtm/wideip/aaaa/stats": fx.EMPTY_STATS,
            "/mgmt/tm/gtm/wideip/cname/stats": fx.EMPTY_STATS,
        }
    )
    results = WideIpChecker().run(ctx)
    assert results[0].status is Status.FAIL
    assert any("app.example.com" in r.summary for r in results if r.status is Status.FAIL)


def test_wide_ips_all_endpoints_error_fails(make_ctx):
    ctx = make_ctx(
        {
            "/mgmt/tm/gtm/wideip/a/stats": ConnectionFailed("x"),
            "/mgmt/tm/gtm/wideip/aaaa/stats": ConnectionFailed("x"),
            "/mgmt/tm/gtm/wideip/cname/stats": ConnectionFailed("x"),
        }
    )
    results = WideIpChecker().run(ctx)
    assert results[0].status is Status.FAIL


def test_wide_ips_partial_missing_type_is_ok(make_ctx):
    # aaaa/cname simply not configured (error), but a-records are healthy → PASS.
    ctx = make_ctx(
        {
            "/mgmt/tm/gtm/wideip/a/stats": fx.WIDEIP_A_HEALTHY,
            "/mgmt/tm/gtm/wideip/aaaa/stats": ConnectionFailed("404"),
            "/mgmt/tm/gtm/wideip/cname/stats": ConnectionFailed("404"),
        }
    )
    results = WideIpChecker().run(ctx)
    assert results[0].status is Status.PASS


def test_gtm_pools_healthy(make_ctx):
    ctx = make_ctx(
        {
            "/mgmt/tm/gtm/pool/a/stats": fx.GTM_POOL_A_HEALTHY,
            "/mgmt/tm/gtm/pool/aaaa/stats": fx.EMPTY_STATS,
            "/mgmt/tm/gtm/pool/cname/stats": fx.EMPTY_STATS,
        }
    )
    assert GtmPoolChecker().run(ctx)[0].status is Status.PASS


def test_gtm_servers_and_datacenters_healthy(make_ctx):
    ctx = make_ctx(
        {
            "/mgmt/tm/gtm/server/stats": fx.GTM_SERVER_HEALTHY,
            "/mgmt/tm/gtm/datacenter/stats": fx.DATACENTER_HEALTHY,
        }
    )
    assert GtmServerChecker().run(ctx)[0].status is Status.PASS
    assert DatacenterChecker().run(ctx)[0].status is Status.PASS
