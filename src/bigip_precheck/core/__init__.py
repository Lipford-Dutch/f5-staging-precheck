"""Core: result model, registry, orchestration, GO/NO-GO gate.

Only lightweight, cycle-free modules are imported eagerly here. ``Registry`` and
``Orchestrator`` live in submodules that pull in ``checkers`` / ``clients``;
import them directly (``from bigip_precheck.core.orchestrator import Orchestrator``)
or via the lazy accessor below to avoid an import cycle at package load.
"""

from __future__ import annotations

from typing import Any

from .context import RunContext
from .gate import Decision, DeviceVerdict, Gate, RunVerdict
from .models import CheckResult, Role, Severity, Source, Status

__all__ = [
    "CheckResult",
    "Role",
    "Severity",
    "Source",
    "Status",
    "RunContext",
    "Gate",
    "Decision",
    "DeviceVerdict",
    "RunVerdict",
    "Registry",
    "Orchestrator",
]


def __getattr__(name: str) -> Any:
    if name == "Registry":
        from .registry import Registry

        return Registry
    if name == "Orchestrator":
        from .orchestrator import Orchestrator

        return Orchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
