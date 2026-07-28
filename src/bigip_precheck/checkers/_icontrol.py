"""Helpers for the two shapes iControl REST returns: collections and stats.

* A *collection* has an ``items`` list of resource objects.
* A *stats* resource nests values under ``entries -> <selfLink> -> nestedStats
  -> entries -> <field> -> description``.

Keeping the digging here means checkers stay readable.
"""

from __future__ import annotations

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


__all__ = ["items", "stats_entries", "description"]
