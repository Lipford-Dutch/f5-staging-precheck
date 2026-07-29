"""Base class and helpers for pluggable checkers.

A checker declares metadata (name, severity, which roles it applies to, its
dependencies) and implements :meth:`run`. The declarative metadata is what lets
profiles, the GO/NO-GO gate and dependency-aware skipping all work generically.

``run()`` should never raise for an *expected* device condition — it converts
that into a ``WARN``/``FAIL`` result. Only genuinely unexpected exceptions
propagate, and the orchestrator turns those into a ``FAIL`` so nothing is ever
silently dropped.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from ..core.context import RunContext
from ..core.models import CheckResult, Role, Severity, Source, Status


class Checker(ABC):
    """Abstract base for every check."""

    #: Stable identifier, kebab or dotted (e.g. ``system.version``).
    name: str = ""
    #: One-line human description shown by ``list-checks``.
    description: str = ""
    #: Default severity for a non-PASS result from this checker.
    severity: Severity = Severity.MEDIUM
    #: Roles this checker applies to. ``{Role.ANY}`` runs everywhere.
    applies_to: frozenset[Role] = frozenset({Role.ANY})
    #: Names of checkers that must pass first; if any FAILed this one is skipped.
    depends_on: tuple[str, ...] = ()

    @abstractmethod
    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        """Evaluate the check against ``ctx.device`` and return one+ results."""

    # -- convenience result builders ---------------------------------------
    def _result(
        self,
        ctx: RunContext,
        status: Status,
        summary: str,
        *,
        severity: Severity | None = None,
        source: Source = Source.REST,
        remediation: str | None = None,
        reference: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> CheckResult:
        return CheckResult(
            check=self.name,
            status=status,
            severity=severity or self.severity,
            summary=summary,
            device=ctx.device.name,
            source=source,
            remediation=remediation,
            reference=reference,
            evidence=evidence or {},
        )

    def applies(self, roles: frozenset[str]) -> bool:
        """True if this checker should run given a device's detected roles."""
        if Role.ANY in self.applies_to:
            return True
        return any(r.value in roles for r in self.applies_to)


def timed(checker: Checker, ctx: RunContext) -> list[CheckResult]:
    """Run a checker, timing it and never letting an exception escape unrecorded.

    Any unexpected exception becomes a single ``FAIL`` result — upholding the
    "never a silent pass" bias even when a checker has a bug.
    """
    start = time.perf_counter()
    try:
        results = list(checker.run(ctx))
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all safety net
        elapsed = time.perf_counter() - start
        return [
            CheckResult(
                check=checker.name,
                status=Status.FAIL,
                severity=Severity.HIGH,
                summary=f"check raised an unexpected error: {type(exc).__name__}: {exc}",
                device=ctx.device.name,
                source=Source.INTERNAL,
                duration_s=elapsed,
            )
        ]
    elapsed = time.perf_counter() - start
    per = elapsed / len(results) if results else elapsed
    return [
        CheckResult(
            check=r.check,
            status=r.status,
            severity=r.severity,
            summary=r.summary,
            device=r.device,
            source=r.source,
            remediation=r.remediation,
            reference=r.reference,
            evidence=r.evidence,
            duration_s=per,
            timestamp=r.timestamp,
        )
        for r in results
    ]


__all__ = ["Checker", "timed"]
