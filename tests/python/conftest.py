"""Shared fixtures: a fake REST client and a context builder."""

from __future__ import annotations

from typing import Any

import pytest

from bigip_precheck.clients.rest import RestClient
from bigip_precheck.config.models import Device, Thresholds
from bigip_precheck.core.context import RunContext
from bigip_precheck.core.exceptions import NotFound


class FakeRestClient:
    """A :class:`RestClient` backed by a dict of path -> payload.

    A payload may be an ``Exception`` instance, in which case ``get`` raises it —
    letting tests exercise the "cannot confirm -> not a silent PASS" paths.
    """

    def __init__(
        self, device: Device, responses: dict[str, Any], version: str = "16.1.3.3"
    ) -> None:
        self.device = device
        self._responses = responses
        self._version = version
        self.calls: list[str] = []

    def get(self, path: str) -> dict[str, Any]:
        self.calls.append(path)
        if path not in self._responses:
            # Mirror the real client: an endpoint the device doesn't serve is a
            # 404 -> NotFound (absent), not a transport failure.
            raise NotFound(f"no fixture for {path} (simulated HTTP 404)")
        payload = self._responses[path]
        if isinstance(payload, Exception):
            raise payload
        return payload

    @property
    def tmos_version(self) -> str:
        return self._version


@pytest.fixture
def device() -> Device:
    return Device(name="bigip-test.example.com", host="10.0.0.1", tags=["ha:pair1", "standby"])


@pytest.fixture
def make_ctx(device: Device):
    def _make(responses: dict[str, Any], *, dev: Device | None = None) -> RunContext:
        d = dev or device
        client: RestClient = FakeRestClient(d, responses)
        return RunContext(
            device=d,
            client=client,
            thresholds=Thresholds(),
            session_id="test-session",
            detected_roles=frozenset({"LTM", "HA"}),
        )

    return _make
