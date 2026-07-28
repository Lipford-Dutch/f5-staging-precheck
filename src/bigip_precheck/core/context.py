"""Per-device run context handed to each checker's ``run()``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..config.models import Device, Thresholds

if TYPE_CHECKING:  # avoid a clients<->core import cycle; only needed for typing
    from ..clients.rest import RestClient


@dataclass
class RunContext:
    """Everything a checker needs to evaluate one device.

    Checkers receive a fully-constructed context and must not reach outside it
    (no global state), which keeps them unit-testable with a fake client.
    """

    device: Device
    client: RestClient
    thresholds: Thresholds
    session_id: str
    detected_roles: frozenset[str] = frozenset()


__all__ = ["RunContext"]
