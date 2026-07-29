"""iControl REST client.

Responsibilities:

* Token authentication (login once, refresh on 401, logout on close).
* Version-aware behaviour via a one-time probe of ``/mgmt/tm/sys/version``.
* Resilient GETs: bounded retries with exponential backoff + jitter on
  transient failures, but *no* retry on auth errors (those are fatal, not flaky).

The :class:`RestClient` protocol lets checkers depend on an interface that is
trivially faked in tests — no live device or ``httpx`` transport required.
"""

from __future__ import annotations

import contextlib
import random
import time
from typing import Any, Protocol, runtime_checkable

import httpx

from ..config.loader import Credential
from ..config.models import Device, Settings
from ..core.exceptions import AuthError, ConnectionFailed, UnexpectedResponse

_LOGIN_PATH = "/mgmt/shared/authn/login"
_TOKEN_HEADER = "X-F5-Auth-Token"
_VERSION_PATH = "/mgmt/tm/sys/version"


@runtime_checkable
class RestClient(Protocol):
    """Minimal surface the checkers rely on."""

    device: Device

    def get(self, path: str) -> dict[str, Any]:
        """GET an iControl REST collection/resource and return parsed JSON."""
        ...

    @property
    def tmos_version(self) -> str:
        """Detected TMOS version string (e.g. ``"16.1.3.3"``), or ``""``."""
        ...


class IControlRestClient:
    """Concrete :class:`RestClient` backed by ``httpx``."""

    def __init__(
        self,
        device: Device,
        credential: Credential,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.device = device
        self._cred = credential
        self._settings = settings
        self._token: str | None = credential.token
        self._version: str | None = None
        base = f"https://{device.host}:{device.port}"
        verify = device.verify_tls and settings.verify_tls
        self._client = httpx.Client(
            base_url=base,
            verify=verify,
            timeout=httpx.Timeout(
                settings.request_timeout_s, connect=settings.connect_timeout_s
            ),
            transport=transport,
        )

    # -- auth ---------------------------------------------------------------
    def _login(self) -> None:
        if self._cred.token:
            self._token = self._cred.token
            return
        try:
            resp = self._client.post(
                _LOGIN_PATH,
                json={
                    "username": self._cred.username,
                    "password": self._cred.password,
                    "loginProviderName": "tmos",
                },
            )
        except httpx.HTTPError as exc:
            raise ConnectionFailed(f"{self.device.name}: login request failed: {exc}") from exc
        if resp.status_code in (401, 403):
            raise AuthError(f"{self.device.name}: authentication rejected ({resp.status_code})")
        if resp.status_code >= 400:
            raise UnexpectedResponse(
                f"{self.device.name}: login returned HTTP {resp.status_code}"
            )
        try:
            token = resp.json()["token"]["token"]
        except (KeyError, TypeError, ValueError) as exc:
            raise UnexpectedResponse(f"{self.device.name}: malformed login response") from exc
        self._token = token

    def _headers(self) -> dict[str, str]:
        if not self._token:
            self._login()
        assert self._token is not None
        return {_TOKEN_HEADER: self._token, "Content-Type": "application/json"}

    # -- requests -----------------------------------------------------------
    def get(self, path: str) -> dict[str, Any]:
        """GET ``path`` with retries; refresh the token once on a 401."""
        attempts = self._settings.retries + 1
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                resp = self._client.get(path, headers=self._headers())
            except httpx.HTTPError as exc:
                last_exc = ConnectionFailed(f"{self.device.name}: GET {path} failed: {exc}")
                self._sleep_backoff(attempt)
                continue
            if resp.status_code == 401 and attempt == 0 and not self._cred.token:
                # Token likely expired: drop it and let the next loop re-login.
                self._token = None
                continue
            if resp.status_code in (401, 403):
                raise AuthError(f"{self.device.name}: GET {path} unauthorised")
            if resp.status_code >= 500:
                last_exc = UnexpectedResponse(
                    f"{self.device.name}: GET {path} -> HTTP {resp.status_code}"
                )
                self._sleep_backoff(attempt)
                continue
            if resp.status_code >= 400:
                raise UnexpectedResponse(
                    f"{self.device.name}: GET {path} -> HTTP {resp.status_code}"
                )
            try:
                data = resp.json()
            except ValueError as exc:
                raise UnexpectedResponse(
                    f"{self.device.name}: GET {path} returned non-JSON"
                ) from exc
            if not isinstance(data, dict):
                raise UnexpectedResponse(f"{self.device.name}: GET {path} returned non-object")
            return data
        assert last_exc is not None
        raise last_exc

    def _sleep_backoff(self, attempt: int) -> None:
        if attempt + 1 >= self._settings.retries + 1:
            return
        base = self._settings.backoff_base_s * (2**attempt)
        time.sleep(base + random.uniform(0, base * 0.25))

    # -- version probe ------------------------------------------------------
    @property
    def tmos_version(self) -> str:
        if self._version is None:
            self._version = self._probe_version()
        return self._version

    def _probe_version(self) -> str:
        try:
            data = self.get(_VERSION_PATH)
        except UnexpectedResponse:
            return ""
        # /sys/version is a nestedStats structure; dig out the Version field.
        try:
            entries = data["entries"]
            first = next(iter(entries.values()))
            nested = first["nestedStats"]["entries"]
            return str(nested["Version"]["description"])
        except (KeyError, StopIteration, TypeError):
            return ""

    def close(self) -> None:
        if self._token and not self._cred.token:
            with contextlib.suppress(httpx.HTTPError):
                self._client.delete(
                    f"/mgmt/shared/authz/tokens/{self._token}", headers=self._headers()
                )
        self._client.close()

    def __enter__(self) -> IControlRestClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


__all__ = ["RestClient", "IControlRestClient"]
