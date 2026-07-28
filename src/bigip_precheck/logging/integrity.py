"""Report integrity: a SHA-256 sidecar so a stored report can be shown untampered.

This is deliberately a hook, not a full signing solution — it gives compliance a
verifiable digest today and a clear place to bolt on detached signatures later.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_hex(data: bytes) -> str:
    """Return the hex SHA-256 digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def write_digest(report_path: str | Path) -> Path:
    """Write ``<report>.sha256`` next to a report file and return its path."""
    p = Path(report_path)
    digest = sha256_hex(p.read_bytes())
    sidecar = p.with_suffix(p.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {p.name}\n", encoding="utf-8")
    return sidecar


def verify_digest(report_path: str | Path) -> bool:
    """Return True when a report still matches its ``.sha256`` sidecar."""
    p = Path(report_path)
    sidecar = p.with_suffix(p.suffix + ".sha256")
    if not sidecar.is_file():
        return False
    expected = sidecar.read_text(encoding="utf-8").split()[0]
    return expected == sha256_hex(p.read_bytes())


__all__ = ["sha256_hex", "write_digest", "verify_digest"]
