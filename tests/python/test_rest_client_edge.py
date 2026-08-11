"""Edge-case and error-path tests for IControlRestClient.

Complements test_rest_client.py: covers retry-exhaustion on transient network
errors, the retries=0 first-attempt-401 regression, non-JSON / non-object
bodies, the 4xx (non-auth) path, close()/logout semantics, and the version
probe's graceful-degradation branch. All via httpx.MockTransport — no network.
"""

from __future__ import annotations

import httpx
import pytest

from bigip_precheck.clients.rest import IControlRestClient
from bigip_precheck.config.loader import Credential
from bigip_precheck.config.models import Device, Settings
from bigip_precheck.core.exceptions import AuthError, ConnectionFailed, NotFound, UnexpectedResponse

DEVICE = Device(name="d", host="10.0.0.1", verify_tls=False)


def _settings(**kw: object) -> Settings:
    base: dict[str, object] = {
        "retries": 2, "backoff_base_s": 0.001,
        "connect_timeout_s": 1, "request_timeout_s": 1,
    }
    base.update(kw)
    return Settings(**base)  # type: ignore[arg-type]


def _client(handler, *, credential: Credential | None = None, settings: Settings | None = None):
    cred = credential or Credential(username="admin", password="pw")
    return IControlRestClient(
        DEVICE, cred, settings or _settings(), transport=httpx.MockTransport(handler)
    )


def test_retries_zero_first_attempt_401_raises_autherror_not_assertion():
    """Regression: retries=0 + an immediate 401 on password auth must raise a
    typed AuthError, never an AssertionError from the exhausted-loop tail."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        return httpx.Response(401, json={})

    client = _client(handler, settings=_settings(retries=0))
    with pytest.raises(AuthError):
        client.get("/mgmt/tm/x")


def test_transient_network_error_exhausts_then_raises_connectionfailed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        raise httpx.ConnectError("boom")

    with pytest.raises(ConnectionFailed):
        _client(handler).get("/mgmt/tm/x")


def test_transient_error_then_success_recovers():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("slow")
        return httpx.Response(200, json={"ok": True})

    assert _client(handler).get("/mgmt/tm/x") == {"ok": True}
    assert calls["n"] == 2


def test_4xx_non_auth_raises_unexpected():
    # 404 has its own dedicated NotFound semantics (module-not-provisioned);
    # use a different non-auth 4xx here to exercise the generic fallback.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        return httpx.Response(409, text="conflict")

    with pytest.raises(UnexpectedResponse):
        _client(handler).get("/mgmt/tm/conflicted")


def test_404_raises_not_found():
    # A 404 means the collection doesn't exist on this device (module not
    # provisioned) — a distinct, non-error condition callers key off of.
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        return httpx.Response(404, text="nope")

    with pytest.raises(NotFound):
        _client(handler).get("/mgmt/tm/does-not-exist")


def test_non_json_body_raises_unexpected():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        return httpx.Response(200, text="<html>not json</html>")

    with pytest.raises(UnexpectedResponse):
        _client(handler).get("/mgmt/tm/x")


def test_json_array_body_rejected_as_non_object():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        return httpx.Response(200, json=[1, 2, 3])

    with pytest.raises(UnexpectedResponse):
        _client(handler).get("/mgmt/tm/x")


def test_malformed_login_response_raises_unexpected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"no": "token here"})

    with pytest.raises(UnexpectedResponse):
        _client(handler).get("/mgmt/tm/x")


def test_login_http_error_raises_connectionfailed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    with pytest.raises(ConnectionFailed):
        _client(handler).get("/mgmt/tm/x")


def test_close_logs_out_token_it_minted():
    seen = {"deleted": None}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "MINTED"}})
        if request.method == "DELETE":
            seen["deleted"] = request.url.path
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    client.get("/mgmt/tm/x")
    client.close()
    assert seen["deleted"] == "/mgmt/shared/authz/tokens/MINTED"


def test_close_does_not_logout_preminted_token():
    """A caller-supplied token is not ours to revoke; close() must not DELETE it."""
    calls = {"delete": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE":
            calls["delete"] += 1
        return httpx.Response(200, json={"ok": True})

    client = _client(handler, credential=Credential(username="", password="", token="PRESET"))
    client.get("/mgmt/tm/x")
    client.close()
    assert calls["delete"] == 0


def test_context_manager_closes():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        return httpx.Response(200, json={"ok": True})

    with _client(handler) as client:
        assert client.get("/mgmt/tm/x") == {"ok": True}


def test_version_probe_degrades_to_empty_string_on_bad_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        return httpx.Response(200, json={"entries": "not-a-dict"})

    assert _client(handler).tmos_version == ""
