"""Regression tests: an unprovisioned module must read as absent, not failed.

Found on a real BIG-IP VE running TMOS 17.5.1.8 with only `ltm` provisioned:
every GTM endpoint returned HTTP 404 and the GTM checkers reported four HIGH
failures ("could not read wide IPs..."). A 404 means the collection does not
exist on the device — an absence to report, not a read failure that should
block an upgrade. Genuine read errors (auth, timeout, 5xx) must still FAIL.
"""

from __future__ import annotations

import httpx
import pytest

from bigip_precheck.checkers import gtm, ltm
from bigip_precheck.clients.rest import IControlRestClient
from bigip_precheck.config.loader import Credential
from bigip_precheck.config.models import Device, Settings
from bigip_precheck.core.exceptions import ConnectionFailed, NotFound, UnexpectedResponse
from bigip_precheck.core.models import Status

from .fixtures import icontrol as fx


# -- REST client: 404 is NotFound, other 4xx stay UnexpectedResponse ---------
def _client(status: int) -> IControlRestClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        return httpx.Response(status, json={})

    return IControlRestClient(
        Device(name="d", host="10.0.0.1", verify_tls=False),
        Credential(username="u", password="p"),
        Settings(retries=0, backoff_base_s=0.001),
        transport=httpx.MockTransport(handler),
    )


def test_404_raises_not_found():
    with pytest.raises(NotFound):
        _client(404).get("/mgmt/tm/gtm/server/stats")


def test_other_4xx_still_unexpected_response():
    with pytest.raises(UnexpectedResponse):
        _client(422).get("/mgmt/tm/ltm/virtual/stats")


def test_not_found_is_a_client_error():
    # Callers that catch ClientError broadly must still catch NotFound.
    from bigip_precheck.core.exceptions import ClientError

    assert issubclass(NotFound, ClientError)


# -- GTM checkers on a device without GTM provisioned -----------------------
@pytest.mark.parametrize("checker", gtm.checkers(), ids=lambda c: c.name)
def test_gtm_absent_reports_info_not_fail(make_ctx, checker):
    # STANDALONE_LTM_ONLY omits every GTM path → FakeRestClient raises NotFound.
    ctx = make_ctx(fx.STANDALONE_LTM_ONLY)
    results = checker.run(ctx)
    assert results, f"{checker.name} returned no results"
    statuses = {r.status for r in results}
    assert Status.FAIL not in statuses, f"{checker.name} failed on an unprovisioned module"
    assert statuses == {Status.INFO}
    assert "not provisioned" in results[0].summary


# -- but a genuine read failure must still FAIL -----------------------------
def test_gtm_real_error_still_fails(make_ctx):
    ctx = make_ctx(
        {
            "/mgmt/tm/gtm/server/stats": ConnectionFailed("connection timed out"),
        }
    )
    (res,) = gtm.GtmServerChecker().run(ctx)
    assert res.status is Status.FAIL


def test_gtm_partial_absence_still_evaluates(make_ctx):
    # aaaa/cname absent (404) but a-records present and healthy → PASS, not INFO.
    ctx = make_ctx({"/mgmt/tm/gtm/wideip/a/stats": fx.WIDEIP_A_HEALTHY})
    results = gtm.WideIpChecker().run(ctx)
    assert results[0].status is Status.PASS


# -- LTM gets the same treatment --------------------------------------------
@pytest.mark.parametrize("checker", ltm.checkers(), ids=lambda c: c.name)
def test_ltm_absent_reports_info_not_fail(make_ctx, checker):
    ctx = make_ctx({})  # nothing served → every LTM path 404s
    results = checker.run(ctx)
    assert results[0].status is Status.INFO
    assert "not provisioned" in results[0].summary


def test_ltm_real_error_still_fails(make_ctx):
    ctx = make_ctx({"/mgmt/tm/ltm/virtual/stats": ConnectionFailed("timeout")})
    (res,) = ltm.VirtualServerChecker().run(ctx)
    assert res.status is Status.FAIL


# -- end-to-end: the real device's shape must not be NO-GO because of GTM ---
def test_ltm_only_device_gtm_does_not_block(make_ctx):
    """The live 17.5.1.8 box: LTM-only, healthy license. No GTM-driven FAIL."""
    ctx = make_ctx(fx.STANDALONE_LTM_ONLY)
    gtm_results = [r for c in gtm.checkers() for r in c.run(ctx)]
    assert not [r for r in gtm_results if r.status is Status.FAIL]
