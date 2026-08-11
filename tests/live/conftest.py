"""Fixtures for the live integration suite.

These tests talk to a REAL BIG-IP over iControl REST. They are skipped entirely
unless ``BIGIP_LIVE_HOST`` is set, so the default offline suite and CI never try
to reach a device.

Configure via environment (see docs/bigip-precheck/LIVE-TESTING.md):

    BIGIP_LIVE_HOST          mgmt IP / DNS of the BIG-IP (required to run)
    BIGIP_LIVE_PORT          mgmt port (default 443)
    BIGIP_LIVE_USERNAME      admin username           (or BIGIP_LIVE_TOKEN)
    BIGIP_LIVE_PASSWORD      admin password
    BIGIP_LIVE_TOKEN         pre-minted auth token    (alternative to user/pass)
    BIGIP_LIVE_VERIFY_TLS    "true" to verify TLS; default "false" for a self-signed VE
    BIGIP_LIVE_ROLES         comma list, e.g. "LTM" or "LTM,GTM" (default: auto-detect)
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from bigip_precheck.clients.rest import IControlRestClient
from bigip_precheck.config.loader import Credential
from bigip_precheck.config.models import Device, Settings, Thresholds
from bigip_precheck.core.context import RunContext

_HOST = os.environ.get("BIGIP_LIVE_HOST")


@pytest.fixture(autouse=True)
def _require_live_host() -> None:
    """Skip every live test unless a real target is configured.

    An autouse fixture is used (rather than a module ``pytestmark``) because a
    mark defined in ``conftest`` does not propagate to sibling test modules; this
    reliably guards the whole package and runs before any client is built.

    When live, mirror ``BIGIP_LIVE_*`` into the standard credential variables the
    orchestrator and CLI resolve, so the end-to-end test exercises the real
    production path (``resolve_credential`` + the default client factory) rather
    than an injected shortcut.
    """
    if not _HOST:
        pytest.skip("live tests require BIGIP_LIVE_HOST (see LIVE-TESTING.md)")
    if os.environ.get("BIGIP_LIVE_USERNAME"):
        os.environ.setdefault("BIGIP_USERNAME", os.environ["BIGIP_LIVE_USERNAME"])
    if os.environ.get("BIGIP_LIVE_PASSWORD"):
        os.environ.setdefault("BIGIP_PASSWORD", os.environ["BIGIP_LIVE_PASSWORD"])
    if os.environ.get("BIGIP_LIVE_TOKEN"):
        os.environ.setdefault("BIGIP_DEFAULT_TOKEN", os.environ["BIGIP_LIVE_TOKEN"])


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="session")
def live_settings() -> Settings:
    return Settings(verify_tls=_env_bool("BIGIP_LIVE_VERIFY_TLS", False))


@pytest.fixture(scope="session")
def live_device() -> Device:
    roles_env = os.environ.get("BIGIP_LIVE_ROLES", "")
    roles = [r.strip().upper() for r in roles_env.split(",") if r.strip()]
    return Device(
        name=os.environ.get("BIGIP_LIVE_NAME", _HOST or "live-bigip"),
        host=_HOST or "unset",
        port=int(os.environ.get("BIGIP_LIVE_PORT", "443")),
        roles=roles,  # type: ignore[arg-type]  # pydantic coerces to Role
        verify_tls=_env_bool("BIGIP_LIVE_VERIFY_TLS", False),
    )


@pytest.fixture(scope="session")
def live_credential() -> Credential:
    return Credential(
        username=os.environ.get("BIGIP_LIVE_USERNAME", ""),
        password=os.environ.get("BIGIP_LIVE_PASSWORD", ""),
        token=os.environ.get("BIGIP_LIVE_TOKEN"),
    )


@pytest.fixture(scope="session")
def live_client(
    live_device: Device, live_credential: Credential, live_settings: Settings
) -> Iterator[IControlRestClient]:
    client = IControlRestClient(live_device, live_credential, live_settings)
    yield client
    client.close()


@pytest.fixture
def live_ctx(live_device: Device, live_client: IControlRestClient) -> RunContext:
    """Context using the device's REAL detected roles, matching production.

    Earlier this hard-coded ``{"LTM", "GTM"}`` to force every checker to run,
    which made a device without GTM provisioned look like it had four failing
    GTM checks. Using the true roles keeps live output faithful to what an
    operator would actually see.
    """
    from bigip_precheck.core.orchestrator import detect_roles

    return RunContext(
        device=live_device,
        client=live_client,
        thresholds=Thresholds(),
        session_id="live-test",
        detected_roles=detect_roles(live_device, live_client),
    )
