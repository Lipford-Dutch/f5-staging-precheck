"""GTM / DNS object-state checks (wide IPs, pools, servers, datacenters).

Wide IPs and pools are partitioned by DNS record type in iControl REST, so those
checkers sweep several type-specific endpoints and merge the results. Endpoints
that don't exist on a given device (record types not in use) are tolerated —
their absence is not a failure, but a genuine read error still surfaces.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..core.context import RunContext
from ..core.exceptions import ClientError
from ..core.models import CheckResult, Role, Severity, Status
from . import _icontrol as ic
from ._objectcheck import evaluate_object_stats
from .base import Checker

_GTM = frozenset({Role.GTM})

# Record types worth checking by default. Others (mx/naptr/srv) can be added later.
_WIDEIP_TYPES = ("a", "aaaa", "cname")
_POOL_TYPES = ("a", "aaaa", "cname")


def _gather(ctx: RunContext, paths: Sequence[str]) -> tuple[list[ic.ObjectState], list[str]]:
    """Collect object states across several stats endpoints.

    Returns ``(states, errors)``. A 404-style empty/error on one record type is
    swallowed (that type simply isn't configured); the caller decides how to
    treat a total wipeout where every endpoint errored.
    """
    states: list[ic.ObjectState] = []
    errors: list[str] = []
    for path in paths:
        try:
            data = ctx.client.get(path)
        except ClientError as exc:
            errors.append(f"{path}: {exc}")
            continue
        states.extend(ic.object_states(data))
    return states, errors


class WideIpChecker(Checker):
    name = "gtm.wide-ips"
    description = "Snapshot wide IP availability across A/AAAA/CNAME record types."
    severity = Severity.HIGH
    applies_to = _GTM

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        paths = [f"/mgmt/tm/gtm/wideip/{t}/stats" for t in _WIDEIP_TYPES]
        states, errors = _gather(ctx, paths)
        if errors and not states:
            return [self._result(ctx, Status.FAIL, f"could not read wide IPs: {errors[0]}")]
        return evaluate_object_stats(self, ctx, states, kind="wide-ips")


class GtmPoolChecker(Checker):
    name = "gtm.pools"
    description = "Snapshot GTM pool availability across A/AAAA/CNAME record types."
    severity = Severity.HIGH
    applies_to = _GTM

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        paths = [f"/mgmt/tm/gtm/pool/{t}/stats" for t in _POOL_TYPES]
        states, errors = _gather(ctx, paths)
        if errors and not states:
            return [self._result(ctx, Status.FAIL, f"could not read GTM pools: {errors[0]}")]
        return evaluate_object_stats(self, ctx, states, kind="gtm-pools")


class GtmServerChecker(Checker):
    name = "gtm.servers"
    description = "Snapshot GTM server availability (datacenter/BIG-IP/host servers)."
    severity = Severity.HIGH
    applies_to = _GTM

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/gtm/server/stats")
        except ClientError as exc:
            return [self._result(ctx, Status.FAIL, f"could not read GTM servers: {exc}")]
        return evaluate_object_stats(self, ctx, ic.object_states(data), kind="gtm-servers")


class DatacenterChecker(Checker):
    name = "gtm.datacenters"
    description = "Snapshot datacenter availability."
    severity = Severity.MEDIUM
    applies_to = _GTM

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/gtm/datacenter/stats")
        except ClientError as exc:
            return [self._result(ctx, Status.FAIL, f"could not read datacenters: {exc}")]
        return evaluate_object_stats(self, ctx, ic.object_states(data), kind="datacenters")


def checkers() -> list[Checker]:
    """Factory returning fresh instances of every GTM checker."""
    return [WideIpChecker(), GtmPoolChecker(), GtmServerChecker(), DatacenterChecker()]


__all__ = [
    "WideIpChecker",
    "GtmPoolChecker",
    "GtmServerChecker",
    "DatacenterChecker",
    "checkers",
]
