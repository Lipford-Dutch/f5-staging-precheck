"""LTM object-state checks (virtual servers, pools, nodes).

Each checker snapshots the availability of a class of objects so a pre-upgrade
run and a post-upgrade run can be diffed. Objects that are offline while still
enabled are treated as traffic-impacting failures.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..core.context import RunContext
from ..core.exceptions import ClientError, NotFound
from ..core.models import CheckResult, Role, Severity, Status
from . import _icontrol as ic
from ._objectcheck import evaluate_object_stats
from .base import Checker

_LTM = frozenset({Role.LTM})


def _absent(checker: Checker, ctx: RunContext, what: str) -> CheckResult:
    """Uniform result for 'this LTM collection does not exist on the device'.

    A 404 means the collection is absent (LTM not provisioned), which is an
    absence to report — not a read failure that should block an upgrade.
    """
    return checker._result(
        ctx,
        Status.INFO,
        f"LTM not provisioned on this device; no {what} to check",
        severity=Severity.INFO,
        evidence={"objects": []},
    )


class VirtualServerChecker(Checker):
    name = "ltm.virtual-servers"
    description = "Snapshot virtual-server availability; flag any offline while enabled."
    severity = Severity.HIGH
    applies_to = _LTM

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/ltm/virtual/stats")
        except NotFound:
            return [_absent(self, ctx, "virtual servers")]
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
        except NotFound:
            return [_absent(self, ctx, "pools")]
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
        except NotFound:
            return [_absent(self, ctx, "nodes")]
        except ClientError as exc:
            return [self._result(ctx, Status.FAIL, f"could not read nodes: {exc}")]
        return evaluate_object_stats(self, ctx, ic.object_states(data), kind="nodes")


def checkers() -> list[Checker]:
    """Factory returning fresh instances of every LTM checker."""
    return [VirtualServerChecker(), PoolChecker(), NodeChecker()]


__all__ = ["VirtualServerChecker", "PoolChecker", "NodeChecker", "checkers"]
