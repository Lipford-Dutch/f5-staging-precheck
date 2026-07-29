"""Run selected checkers across an inventory, safely and in the right order.

Two ordering guarantees matter for a *pre-upgrade* tool:

* **Within an HA group, evaluate the standby before the active member.** Devices
  are grouped by an ``ha:<group>`` tag; members of a group run sequentially,
  standby first (tag ``standby`` < untagged < ``active``). Distinct groups and
  standalone devices run concurrently up to ``max_workers``.
* **Within a device, a checker whose dependency FAILed is skipped**, recorded as
  an explicit ``SKIP`` result — never dropped silently.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from ..checkers.base import Checker, timed
from ..clients.rest import RestClient
from ..config.loader import Credential, resolve_credential
from ..config.models import Device, Inventory, Thresholds
from .context import RunContext
from .models import CheckResult, Role, Severity, Source, Status

ClientFactory = Callable[[Device, Credential], RestClient]


@dataclass
class _Group:
    key: str
    devices: list[Device]


def _standby_rank(device: Device) -> int:
    tags = {t.lower() for t in device.tags}
    if "standby" in tags:
        return 0
    if "active" in tags:
        return 2
    return 1


def _group_key(device: Device) -> str:
    for tag in device.tags:
        if tag.lower().startswith("ha:"):
            return tag.lower()
    return f"__standalone__:{device.name}"


def group_devices(devices: list[Device]) -> list[_Group]:
    """Group by HA membership; order members standby-first."""
    groups: dict[str, list[Device]] = {}
    for d in devices:
        groups.setdefault(_group_key(d), []).append(d)
    ordered: list[_Group] = []
    for key in sorted(groups):
        members = sorted(groups[key], key=lambda d: (_standby_rank(d), d.name))
        ordered.append(_Group(key=key, devices=members))
    return ordered


def _detect_roles(device: Device) -> frozenset[str]:
    """Best-effort role detection from configured hints (REST auto-detect: PR B)."""
    roles = {r.value for r in device.roles}
    if not roles:
        roles = {Role.LTM.value}  # LTM is the safe default; GTM is opt-in via config.
    return frozenset(roles)


class Orchestrator:
    def __init__(
        self,
        inventory: Inventory,
        registry_checkers: list[Checker],
        *,
        client_factory: ClientFactory | None = None,
        allow_prompt: bool = False,
        on_event: Callable[[str, dict[str, object]], None] | None = None,
    ) -> None:
        self._inv = inventory
        self._checkers = registry_checkers
        self._factory = client_factory or self._default_factory
        self._allow_prompt = allow_prompt
        self._on_event = on_event or (lambda *_: None)

    def _default_factory(self, device: Device, cred: Credential) -> RestClient:
        from ..clients.rest import IControlRestClient

        return IControlRestClient(device, cred, self._inv.settings)

    def _thresholds_for(self, device: Device) -> Thresholds:
        return self._inv.thresholds

    def run(self, session_id: str) -> dict[str, list[CheckResult]]:
        results: dict[str, list[CheckResult]] = {}
        groups = group_devices(self._inv.devices)
        max_workers = min(self._inv.settings.max_workers, max(1, len(groups)))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._run_group, g, session_id): g for g in groups
            }
            for fut in futures:
                for name, res in fut.result().items():
                    results[name] = res
        return results

    def _run_group(self, group: _Group, session_id: str) -> dict[str, list[CheckResult]]:
        out: dict[str, list[CheckResult]] = {}
        for device in group.devices:  # sequential: standby before active
            out[device.name] = self._run_device(device, session_id)
        return out

    def _run_device(self, device: Device, session_id: str) -> list[CheckResult]:
        self._on_event("device_start", {"device": device.name})
        try:
            cred = resolve_credential(device.credential, allow_prompt=self._allow_prompt)
        except Exception as exc:  # noqa: BLE001 - surface as a FAIL, never silent
            return [self._fatal(device.name, f"credential resolution failed: {exc}")]

        roles = _detect_roles(device)
        thresholds = self._thresholds_for(device)
        client = self._factory(device, cred)
        results: list[CheckResult] = []
        failed_checks: set[str] = set()
        try:
            ctx = RunContext(
                device=device,
                client=client,
                thresholds=thresholds,
                session_id=session_id,
                detected_roles=roles,
            )
            for checker in self._checkers:
                if not checker.applies(roles):
                    continue
                skipped_by = [d for d in checker.depends_on if d in failed_checks]
                if skipped_by:
                    results.append(
                        CheckResult(
                            check=checker.name,
                            status=Status.SKIP,
                            severity=Severity.INFO,
                            summary=f"skipped: dependency failed ({', '.join(skipped_by)})",
                            device=device.name,
                            source=Source.INTERNAL,
                        )
                    )
                    continue
                res = timed(checker, ctx)
                if any(r.status is Status.FAIL for r in res):
                    failed_checks.add(checker.name)
                results.extend(res)
                for r in res:
                    self._on_event(
                        "check_result",
                        {
                            "device": device.name,
                            "check": r.check,
                            "status": r.status.value,
                            "severity": r.severity.value,
                            "summary": r.summary,
                        },
                    )
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                with contextlib.suppress(Exception):  # best-effort cleanup
                    close()
            self._on_event("device_end", {"device": device.name})
        return results

    @staticmethod
    def _fatal(device: str, summary: str) -> CheckResult:
        return CheckResult(
            check="device.connect",
            status=Status.FAIL,
            severity=Severity.CRITICAL,
            summary=summary,
            device=device,
            source=Source.INTERNAL,
        )


__all__ = ["Orchestrator", "group_devices", "ClientFactory"]
