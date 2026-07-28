"""Aggregate check results into per-device and overall GO / NO-GO decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .models import CheckResult, Severity, Status


class Decision(StrEnum):
    GO = "GO"
    NO_GO = "NO-GO"


@dataclass
class DeviceVerdict:
    device: str
    decision: Decision
    results: list[CheckResult] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        c = {s.value: 0 for s in Status}
        for r in self.results:
            c[r.status.value] += 1
        return c

    @property
    def blocking(self) -> list[CheckResult]:
        return [r for r in self.results if r.status is Status.FAIL]


@dataclass
class RunVerdict:
    decision: Decision
    devices: list[DeviceVerdict] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        c = {s.value: 0 for s in Status}
        for d in self.devices:
            for k, v in d.counts.items():
                c[k] += v
        return c


class Gate:
    """Turns results into decisions.

    Default policy: any ``FAIL`` on a device is NO-GO for that device. With
    ``warn_is_blocking``, a ``WARN`` at or above ``warn_block_severity`` also
    blocks — supporting stricter change windows without code changes.
    """

    def __init__(
        self,
        *,
        warn_is_blocking: bool = False,
        warn_block_severity: Severity = Severity.HIGH,
    ) -> None:
        self.warn_is_blocking = warn_is_blocking
        self.warn_block_severity = warn_block_severity

    def _device_decision(self, results: list[CheckResult]) -> Decision:
        for r in results:
            if r.status is Status.FAIL:
                return Decision.NO_GO
            if (
                self.warn_is_blocking
                and r.status is Status.WARN
                and r.severity.rank >= self.warn_block_severity.rank
            ):
                return Decision.NO_GO
        return Decision.GO

    def evaluate(self, results_by_device: dict[str, list[CheckResult]]) -> RunVerdict:
        devices: list[DeviceVerdict] = []
        for name, results in results_by_device.items():
            decision = self._device_decision(results)
            devices.append(DeviceVerdict(device=name, decision=decision, results=results))
        overall = (
            Decision.NO_GO
            if any(d.decision is Decision.NO_GO for d in devices)
            else Decision.GO
        )
        return RunVerdict(decision=overall, devices=devices)


__all__ = ["Decision", "DeviceVerdict", "RunVerdict", "Gate"]
