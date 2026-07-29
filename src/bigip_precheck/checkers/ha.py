"""High-availability / device-group readiness checks."""

from __future__ import annotations

from collections.abc import Sequence

from ..core.context import RunContext
from ..core.exceptions import ClientError
from ..core.models import CheckResult, Role, Severity, Status
from . import _icontrol as ic
from .base import Checker

_GREEN = "green"


class FailoverStatusChecker(Checker):
    name = "ha.failover-status"
    description = "Report the device's failover role (Active/Standby) and traffic-group health."
    severity = Severity.HIGH
    applies_to = frozenset({Role.ANY})

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/cm/failover-status")
        except ClientError as exc:
            return [self._result(ctx, Status.FAIL, f"could not read failover status: {exc}")]
        entries = ic.stats_entries(data)
        if not entries:
            return [self._result(ctx, Status.WARN, "failover status was empty")]
        fields = entries[0]
        color = ic.description(fields, "color").lower()
        status = ic.description(fields, "status")
        summary = ic.description(fields, "summary")
        evidence = {"color": color, "status": status, "summary": summary}

        if not status:
            return [
                self._result(
                    ctx, Status.WARN, "failover role could not be determined", evidence=evidence
                )
            ]
        if color and color != _GREEN:
            return [
                self._result(
                    ctx,
                    Status.WARN,
                    f"failover role {status} but traffic-group color is {color}: {summary}",
                    remediation="Investigate the non-green traffic group before upgrading.",
                    evidence=evidence,
                )
            ]
        return [
            self._result(
                ctx,
                Status.PASS,
                f"failover role: {status} ({summary or 'healthy'})",
                severity=Severity.INFO,
                evidence=evidence,
            )
        ]


class SyncStatusChecker(Checker):
    name = "ha.sync-status"
    description = "Verify config-sync state is In Sync across the device group."
    severity = Severity.HIGH
    applies_to = frozenset({Role.ANY})
    depends_on = ("ha.failover-status",)

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/cm/sync-status")
        except ClientError as exc:
            return [self._result(ctx, Status.FAIL, f"could not read sync status: {exc}")]
        entries = ic.stats_entries(data)
        if not entries:
            return [self._result(ctx, Status.WARN, "sync status was empty")]
        fields = entries[0]
        color = ic.description(fields, "color").lower()
        status = ic.description(fields, "status")
        summary = ic.description(fields, "summary")
        mode = ic.description(fields, "mode")
        evidence = {"color": color, "status": status, "summary": summary, "mode": mode}

        # A standalone device legitimately reports "Standalone" — that is fine.
        if status.lower() == "standalone" or mode.lower() == "standalone":
            return [
                self._result(
                    ctx,
                    Status.INFO,
                    "device is standalone (no config-sync peer)",
                    severity=Severity.INFO,
                    evidence=evidence,
                )
            ]
        if color == _GREEN and status.lower() == "in sync":
            return [
                self._result(
                    ctx,
                    Status.PASS,
                    "config-sync is In Sync",
                    severity=Severity.INFO,
                    evidence=evidence,
                )
            ]
        return [
            self._result(
                ctx,
                Status.FAIL,
                f"config-sync not in sync: {status or 'unknown'} ({color or 'no color'})",
                remediation=(
                    "Resolve pending changes and sync the device group to a known-good "
                    "state before upgrading."
                ),
                evidence=evidence,
            )
        ]


def checkers() -> list[Checker]:
    """Factory returning fresh instances of every HA checker."""
    return [FailoverStatusChecker(), SyncStatusChecker()]


__all__ = ["FailoverStatusChecker", "SyncStatusChecker", "checkers"]
