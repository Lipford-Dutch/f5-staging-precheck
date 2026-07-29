"""Schema-versioned, machine-readable JSON report.

Consumed by CI and downstream tooling, so the shape is stable and versioned.
All evidence has already been redacted by the checkers/audit path, but we redact
once more here as defence in depth before writing to disk.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import __version__
from ..core.gate import RunVerdict
from ..redaction import redact

SCHEMA_VERSION = "1.0"


def build_report(
    verdict: RunVerdict,
    *,
    session_id: str,
    profile: str,
    inventory_path: str,
) -> dict[str, Any]:
    """Assemble the report document from a :class:`RunVerdict`."""
    report = {
        "schema_version": SCHEMA_VERSION,
        "tool": "bigip-precheck",
        "tool_version": __version__,
        "session_id": session_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "profile": profile,
        "inventory": inventory_path,
        "decision": verdict.decision.value,
        "totals": verdict.counts,
        "devices": [
            {
                "device": d.device,
                "decision": d.decision.value,
                "counts": d.counts,
                "results": [r.to_dict() for r in d.results],
            }
            for d in verdict.devices
        ],
    }
    redacted: dict[str, Any] = redact(report)
    return redacted


def write_report(report: dict[str, Any], path: str | Path) -> Path:
    """Write the report as pretty JSON and return the path."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return p


__all__ = ["SCHEMA_VERSION", "build_report", "write_report"]
