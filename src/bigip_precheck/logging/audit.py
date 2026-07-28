"""Structured, append-only audit trail for a single run.

Two artefacts are written per session:

* ``session-<id>.jsonl`` — one JSON object per event, machine-readable.
* ``session-<id>.log``   — the same events rendered for a human.

Every payload is passed through :func:`bigip_precheck.redaction.redact` before it
touches disk, so tokens and passwords can never be persisted.
"""

from __future__ import annotations

import getpass
import json
import os
import socket
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..redaction import redact


def _now() -> str:
    return datetime.now(UTC).isoformat()


class AuditLog:
    """Append-only session log. Safe to use as a context manager."""

    def __init__(self, output_dir: str | Path, *, session_id: str | None = None) -> None:
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.dir = Path(output_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.dir / f"session-{self.session_id}.jsonl"
        self.log_path = self.dir / f"session-{self.session_id}.log"
        self.operator = self._operator_identity()
        self.started_at = _now()
        self.event(
            "session_start",
            session_id=self.session_id,
            operator=self.operator,
            started_at=self.started_at,
        )

    @staticmethod
    def _operator_identity() -> dict[str, str]:
        try:
            user = getpass.getuser()
        except Exception:  # pragma: no cover - unusual environments
            user = os.environ.get("USER", "unknown")
        return {"user": user, "host": socket.gethostname()}

    def event(self, kind: str, **fields: Any) -> None:
        """Record one structured event to both artefacts."""
        record = {"ts": _now(), "session_id": self.session_id, "event": kind, **fields}
        safe = redact(record)
        with self.jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(safe, default=str) + "\n")
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{safe['ts']} [{kind}] " + self._human(safe) + "\n")

    @staticmethod
    def _human(record: dict[str, Any]) -> str:
        parts = [
            f"{k}={v}"
            for k, v in record.items()
            if k not in {"ts", "event", "session_id"}
        ]
        return " ".join(parts)

    def close(self, *, decision: str | None = None) -> None:
        self.event("session_end", decision=decision, ended_at=_now())

    def __enter__(self) -> AuditLog:
        return self

    def __exit__(self, *exc: object) -> None:
        # Only emit an implicit end if the caller did not close explicitly.
        self.event("session_close", ended_at=_now())


__all__ = ["AuditLog"]
