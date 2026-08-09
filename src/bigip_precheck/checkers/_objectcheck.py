"""Shared evaluation of LTM/GTM object availability into check results.

Both the LTM and GTM checkers reduce a ``/stats`` payload to a list of
:class:`~bigip_precheck._icontrol.ObjectState` and then apply the same policy:

* an object that is **offline while still enabled** is traffic-impacting → FAIL;
* an object whose availability is **unknown** (monitors not yet reported) can't be
  confirmed healthy → WARN (never a silent PASS);
* administratively **disabled** objects are expected pre-change → INFO note only;
* everything else is available → PASS.

The aggregate result carries the full object snapshot in ``evidence["objects"]``
so the snapshot writer can persist it for a later pre/post diff.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..core.context import RunContext
from ..core.models import CheckResult, Severity, Status
from . import _icontrol as ic
from .base import Checker


def evaluate_object_stats(
    checker: Checker,
    ctx: RunContext,
    states: Sequence[ic.ObjectState],
    *,
    kind: str,
) -> list[CheckResult]:
    """Turn object states into an aggregate result plus one FAIL per down object."""
    if not states:
        return [
            checker._result(
                ctx,
                Status.INFO,
                f"no {kind} configured",
                severity=Severity.INFO,
                evidence={"objects": []},
            )
        ]

    snapshot = [s.to_dict() for s in states]
    down = [s for s in states if s.is_down_while_enabled]
    unknown = [
        s
        for s in states
        if s.availability.lower() == "unknown" and s.is_enabled and s not in down
    ]
    disabled = [s for s in states if not s.is_enabled]
    available = len(states) - len(down) - len(unknown) - len(disabled)

    counts = (
        f"{len(states)} {kind}: {available} available, {len(down)} down, "
        f"{len(unknown)} unknown, {len(disabled)} disabled"
    )

    if down:
        agg_status, agg_sev = Status.FAIL, Severity.HIGH
    elif unknown:
        agg_status, agg_sev = Status.WARN, Severity.MEDIUM
    else:
        agg_status, agg_sev = Status.PASS, Severity.INFO

    results: list[CheckResult] = [
        checker._result(
            ctx,
            agg_status,
            counts,
            severity=agg_sev,
            remediation=(
                f"Investigate the offline {kind} listed below before proceeding."
                if down
                else (
                    f"Some {kind} report unknown availability; verify monitors are up."
                    if unknown
                    else None
                )
            ),
            evidence={"objects": snapshot},
        )
    ]

    for s in down:
        results.append(
            checker._result(
                ctx,
                Status.FAIL,
                f"{kind[:-1] if kind.endswith('s') else kind} {s.name} is offline while enabled: "
                f"{s.reason or 'no reason reported'}",
                severity=Severity.HIGH,
                evidence=s.to_dict(),
            )
        )
    return results


__all__ = ["evaluate_object_stats"]
