"""Object-availability snapshots for pre/post-change comparison.

An LTM/GTM checker records each object's state in ``evidence["objects"]``. This
module harvests those into a compact, schema-versioned snapshot that can be
written before a change and diffed against a snapshot taken after it — so an
operator can prove nothing that was available beforehand went offline.

Regression = an object that was *available* before is no longer available, or an
object that was *enabled* before is now disabled. Regressions are what make a
post-change diff fail; recoveries/additions/removals are reported but benign.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__
from .core.gate import RunVerdict

SNAPSHOT_SCHEMA_VERSION = "1.0"


def build_snapshot(verdict: RunVerdict, *, session_id: str) -> dict[str, Any]:
    """Harvest object states from a run into a serialisable snapshot document."""
    devices: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
    for dv in verdict.devices:
        objects_by_check: dict[str, dict[str, dict[str, str]]] = {}
        for r in dv.results:
            objs = r.evidence.get("objects") if isinstance(r.evidence, dict) else None
            if not isinstance(objs, list):
                continue
            bucket = objects_by_check.setdefault(r.check, {})
            for obj in objs:
                if isinstance(obj, dict) and obj.get("name"):
                    bucket[str(obj["name"])] = {
                        "availability": str(obj.get("availability", "unknown")),
                        "enabled": str(obj.get("enabled", "unknown")),
                        "reason": str(obj.get("reason", "")),
                    }
        if objects_by_check:
            devices[dv.device] = objects_by_check
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "tool_version": __version__,
        "session_id": session_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "devices": devices,
    }


def write_snapshot(snapshot: dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return p


def load_snapshot(path: str | Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


@dataclass
class ObjectChange:
    device: str
    check: str
    name: str
    kind: str  # regression | recovery | added | removed | changed
    before: dict[str, str] | None
    after: dict[str, str] | None
    detail: str


@dataclass
class SnapshotDiff:
    changes: list[ObjectChange] = field(default_factory=list)

    @property
    def regressions(self) -> list[ObjectChange]:
        return [c for c in self.changes if c.kind == "regression"]

    @property
    def has_regressions(self) -> bool:
        return bool(self.regressions)

    def by_kind(self, kind: str) -> list[ObjectChange]:
        return [c for c in self.changes if c.kind == kind]


def _available(state: dict[str, str]) -> bool:
    return state.get("availability", "").lower() == "available"


def _enabled(state: dict[str, str]) -> bool:
    return state.get("enabled", "").lower().startswith("enabled")


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> SnapshotDiff:
    """Compare two snapshots and classify every per-object change."""
    diff = SnapshotDiff()
    before_devices = before.get("devices", {})
    after_devices = after.get("devices", {})
    for device in sorted(set(before_devices) | set(after_devices)):
        b_checks = before_devices.get(device, {})
        a_checks = after_devices.get(device, {})
        for check in sorted(set(b_checks) | set(a_checks)):
            b_objs = b_checks.get(check, {})
            a_objs = a_checks.get(check, {})
            for name in sorted(set(b_objs) | set(a_objs)):
                b = b_objs.get(name)
                a = a_objs.get(name)
                _classify(diff, device, check, name, b, a)
    return diff


def _classify(
    diff: SnapshotDiff,
    device: str,
    check: str,
    name: str,
    b: dict[str, str] | None,
    a: dict[str, str] | None,
) -> None:
    if b is None and a is not None:
        diff.changes.append(
            ObjectChange(device, check, name, "added", None, a, "new object since baseline")
        )
        return
    if a is None and b is not None:
        diff.changes.append(
            ObjectChange(device, check, name, "removed", b, None, "object gone since baseline")
        )
        return
    if b is None or a is None:
        return
    was_ok = _available(b) and _enabled(b)
    now_ok = _available(a) and _enabled(a)
    if was_ok and not now_ok:
        detail = f"{b['availability']}/{b['enabled']} -> {a['availability']}/{a['enabled']}"
        diff.changes.append(ObjectChange(device, check, name, "regression", b, a, detail))
    elif not was_ok and now_ok:
        diff.changes.append(
            ObjectChange(device, check, name, "recovery", b, a, "recovered since baseline")
        )
    elif b != a:
        detail = f"{b['availability']}/{b['enabled']} -> {a['availability']}/{a['enabled']}"
        diff.changes.append(ObjectChange(device, check, name, "changed", b, a, detail))


__all__ = [
    "SNAPSHOT_SCHEMA_VERSION",
    "ObjectChange",
    "SnapshotDiff",
    "build_snapshot",
    "write_snapshot",
    "load_snapshot",
    "diff_snapshots",
]
