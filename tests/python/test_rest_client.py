"""Tests for the httpx-backed iControl REST client via a mock transport.

No network: an ``httpx.MockTransport`` answers requests from a scripted handler,
letting us exercise token login, 401 refresh, retry/backoff and the version probe.
"""

from __future__ import annotations

import httpx
import pytest

from bigip_precheck.clients.rest import IControlRestClient
from bigip_precheck.config.loader import Credential
from bigip_precheck.config.models import Device, Settings
from bigip_precheck.core.exceptions import AuthError, UnexpectedResponse

DEVICE = Device(name="d", host="10.0.0.1", verify_tls=False)
SETTINGS = Settings(retries=2, backoff_base_s=0.001, connect_timeout_s=1, request_timeout_s=1)


def _client(handler, credential: Credential | None = None) -> IControlRestClient:
    cred = credential or Credential(username="admin", password="pw")
    return IControlRestClient(
        DEVICE, cred, SETTINGS, transport=httpx.MockTransport(handler)
    )


def test_login_then_get_uses_token():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "TOK123"}})
        seen["auth"] = request.headers.get("X-F5-Auth-Token", "")
        return httpx.Response(200, json={"items": []})

    client = _client(handler)
    client.get("/mgmt/tm/sys/provision")
    assert seen["auth"] == "TOK123"


def test_auth_rejected_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={})

    with pytest.raises(AuthError):
        _client(handler).get("/mgmt/tm/sys/version")


def test_token_credential_skips_login():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path != "/mgmt/shared/authn/login"
        return httpx.Response(200, json={"ok": True})

    client = _client(handler, Credential(username="", password="", token="PRESET"))
    assert client.get("/mgmt/tm/sys/version") == {"ok": True}


def test_retry_then_success_on_500():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, json={"recovered": True})

    client = _client(handler)
    assert client.get("/mgmt/tm/x") == {"recovered": True}
    assert calls["n"] == 2


def test_persistent_500_raises_unexpected():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        return httpx.Response(500, text="down")

    with pytest.raises(UnexpectedResponse):
        _client(handler).get("/mgmt/tm/x")


def test_version_probe_parses_nested_stats():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            return httpx.Response(200, json={"token": {"token": "T"}})
        return httpx.Response(
            200,
            json={
                "entries": {
                    "https://localhost/mgmt/tm/sys/version/0": {
                        "nestedStats": {"entries": {"Version": {"description": "17.1.1"}}}
                    }
                }
            },
        )

    assert _client(handler).tmos_version == "17.1.1"


def test_401_after_login_triggers_reauth():
    state = {"logins": 0, "gets": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/mgmt/shared/authn/login":
            state["logins"] += 1
            return httpx.Response(200, json={"token": {"token": f"T{state['logins']}"}})
        state["gets"] += 1
        if state["gets"] == 1:
            return httpx.Response(401, json={})  # stale token
        return httpx.Response(200, json={"ok": True})

    client = _client(handler)
    assert client.get("/mgmt/tm/x") == {"ok": True}
    assert state["logins"] == 2  # re-authenticated after the 401
