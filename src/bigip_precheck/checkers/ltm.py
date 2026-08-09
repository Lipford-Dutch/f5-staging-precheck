"""LTM object-state checks (virtual servers, pools, nodes).

Each checker snapshots the availability of a class of objects so a pre-upgrade
run and a post-upgrade run can be diffed. Objects that are offline while still
enabled are treated as traffic-impacting failures.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..core.context import RunContext
from ..core.exceptions import ClientError
from ..core.models import CheckResult, Role, Severity, Status
from . import _icontrol as ic
from ._objectcheck import evaluate_object_stats
from .base import Checker

_LTM = frozenset({Role.LTM})


class VirtualServerChecker(Checker):
    name = "ltm.virtual-servers"
    description = "Snapshot virtual-server availability; flag any offline while enabled."
    severity = Severity.HIGH
    applies_to = _LTM

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/ltm/virtual/stats")
        except ClientError as exc:
            return [self._result(ctx, Status.FAIL, f"could not read virtual servers: {exc}")]
        return evaluate_object_stats(self, ctx, ic.object_states(data), kind="virtual-servers")


class PoolChecker(Checker):
    name = "ltm.pools"
    description = "Snapshot pool availability and active member counts."
    severity = Severity.HIGH
    applies_to = _LTM

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/ltm/pool/stats")
        except ClientError as exc:
            return [self._result(ctx, Status.FAIL, f"could not read pools: {exc}")]
        results = list(
            evaluate_object_stats(self, ctx, ic.object_states(data), kind="pools")
        )
        # Additionally flag pools with zero active members that are still enabled.
        for fields in ic.stats_entries(data):
            name = ic.description(fields, "tmName")
            if not name:
                continue
            enabled = ic.description(fields, "status.enabledState", "unknown").lower()
            active = ic.description(fields, "activeMemberCnt", "")
            if enabled.startswith("enabled") and active == "0":
                results.append(
                    self._result(
                        ctx,
                        Status.FAIL,
                        f"pool {name} has 0 active members",
                        severity=Severity.HIGH,
                        remediation="Confirm members/monitors before upgrading.",
                        evidence={"pool": name, "activeMemberCnt": active},
                    )
                )
        return results


class NodeChecker(Checker):
    name = "ltm.nodes"
    description = "Snapshot node availability; flag any offline while enabled."
    severity = Severity.MEDIUM
    applies_to = _LTM

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/ltm/node/stats")
        except ClientError as exc:
            return [self._result(ctx, Status.FAIL, f"could not read nodes: {exc}")]
        return evaluate_object_stats(self, ctx, ic.object_states(data), kind="nodes")


def checkers() -> list[Checker]:
    """Factory returning fresh instances of every LTM checker."""
    return [VirtualServerChecker(), PoolChecker(), NodeChecker()]


__all__ = ["VirtualServerChecker", "PoolChecker", "NodeChecker", "checkers"]
