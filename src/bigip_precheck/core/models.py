"""Core result model shared by every checker, reporter and the GO/NO-GO gate.

Design bias: *false negatives are worse than false positives*. A check that
cannot positively confirm health must degrade to ``WARN`` or ``FAIL`` — never a
silent ``PASS``. The :class:`Status`/:class:`Severity` split lets us express
both "how bad is this" (severity) and "what did we observe" (status).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    """Observed outcome of a single check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    INFO = "INFO"
    SKIP = "SKIP"


class Severity(StrEnum):
    """How much a non-PASS outcome matters for upgrade readiness."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def rank(self) -> int:
        """Numeric ordering so severities can be compared / sorted."""
        return _SEVERITY_ORDER[self]


_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class Role(StrEnum):
    """Device role a checker applies to. ``ANY`` matches every device."""

    ANY = "ANY"
    LTM = "LTM"
    GTM = "GTM"
    HA = "HA"


class Source(StrEnum):
    """Where a result's evidence came from — key for the SNMP cross-check phase."""

    REST = "rest"
    SNMP = "snmp"
    TMSH = "tmsh"
    CROSS = "cross"
    INTERNAL = "internal"


@dataclass(frozen=True)
class CheckResult:
    """Immutable record of one observation made by a checker.

    A single checker may emit several results (e.g. one per non-green pool).
    ``evidence`` holds already-redacted raw data used to reach the verdict so a
    reviewer can audit *why* without re-running the tool.
    """

    check: str
    status: Status
    severity: Severity
    summary: str
    device: str
    source: Source = Source.REST
    remediation: str | None = None
    reference: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    duration_s: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_blocking(self) -> bool:
        """True when this result should block an upgrade under the default gate."""
        return self.status is Status.FAIL

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable representation for the machine-readable report."""
        return {
            "check": self.check,
            "status": self.status.value,
            "severity": self.severity.value,
            "summary": self.summary,
            "device": self.device,
            "source": self.source.value,
            "remediation": self.remediation,
            "reference": self.reference,
            "evidence": self.evidence,
            "duration_s": round(self.duration_s, 4),
            "timestamp": self.timestamp.isoformat(),
        }


__all__ = ["Status", "Severity", "Role", "Source", "CheckResult"]
