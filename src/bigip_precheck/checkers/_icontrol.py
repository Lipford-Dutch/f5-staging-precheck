"""Helpers for the two shapes iControl REST returns: collections and stats.

* A *collection* has an ``items`` list of resource objects.
* A *stats* resource nests values under ``entries -> <selfLink> -> nestedStats
  -> entries -> <field> -> description``.

Keeping the digging here means checkers stay readable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the ``items`` list of a collection payload (empty if absent)."""
    value = payload.get("items")
    return value if isinstance(value, list) else []


def stats_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return each nestedStats ``entries`` dict from a stats payload.

    A stats payload may hold several top-level entries (one per object); we
    return the inner field-maps so a checker can read ``description`` values.
    """
    out: list[dict[str, Any]] = []
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return out
    for entry in entries.values():
        nested = entry.get("nestedStats", {}).get("entries")
        if isinstance(nested, dict):
            out.append(nested)
    return out


def description(fields: dict[str, Any], key: str, default: str = "") -> str:
    """Read ``fields[key].description`` as a string, with a default."""
    field = fields.get(key)
    if isinstance(field, dict) and "description" in field:
        return str(field["description"])
    return default


@dataclass(frozen=True)
class ObjectState:
    """Availability snapshot for one LTM/GTM object, from a ``/stats`` payload."""

    name: str
    availability: str  # available | offline | unknown | disabled …
    enabled: str  # enabled | disabled | disabled-by-parent …
    reason: str

    @property
    def is_available(self) -> bool:
        return self.availability.lower() == "available"

    @property
    def is_enabled(self) -> bool:
        return self.enabled.lower().startswith("enabled")

    @property
    def is_down_while_enabled(self) -> bool:
        """Offline but administratively enabled — the traffic-impacting case."""
        return self.is_enabled and self.availability.lower() in {"offline", "red"}

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "availability": self.availability,
            "enabled": self.enabled,
            "reason": self.reason,
        }


def object_states(payload: dict[str, Any], *, name_key: str = "tmName") -> list[ObjectState]:
    """Extract per-object availability from an LTM/GTM ``/stats`` payload.

    Reads the conventional ``status.availabilityState`` / ``status.enabledState``
    / ``status.statusReason`` fields plus a name field (``tmName`` for most
    objects). Objects missing a name are skipped.
    """
    out: list[ObjectState] = []
    for fields in stats_entries(payload):
        name = description(fields, name_key) or description(fields, "name")
        if not name:
            continue
        out.append(
            ObjectState(
                name=name,
                availability=description(fields, "status.availabilityState", "unknown"),
                enabled=description(fields, "status.enabledState", "unknown"),
                reason=description(fields, "status.statusReason"),
            )
        )
    return out


__all__ = ["items", "stats_entries", "description", "ObjectState", "object_states"]
