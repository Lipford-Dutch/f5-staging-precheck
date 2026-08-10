"""Capture sanitized iControl REST payloads from a live BIG-IP.

Purpose: turn a real device's responses into fixtures that replace the
hand-synthesized ones under ``tests/python/fixtures``. Every payload is scrubbed
before it touches disk — secrets via the central redactor, plus host/IP/serial
identifiers via caller-supplied replacements — so a capture is safe to commit.

This is read-only: it only issues GETs. It is used by the ``capture`` CLI
command and is unit-testable against a fake client (no device required to test
the sanitization path).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .clients.rest import RestClient
from .core.exceptions import ClientError
from .redaction import redact

# The union of every endpoint the built-in checkers read. Kept here so a capture
# always yields exactly the payloads the offline fixtures need.
ENDPOINTS: tuple[str, ...] = (
    "/mgmt/tm/sys/version",
    "/mgmt/tm/sys/license",
    "/mgmt/tm/sys/provision",
    "/mgmt/tm/sys/software/volume",
    "/mgmt/tm/cm/failover-status",
    "/mgmt/tm/cm/sync-status",
    "/mgmt/tm/ltm/virtual/stats",
    "/mgmt/tm/ltm/pool/stats",
    "/mgmt/tm/ltm/node/stats",
    "/mgmt/tm/gtm/wideip/a/stats",
    "/mgmt/tm/gtm/wideip/aaaa/stats",
    "/mgmt/tm/gtm/wideip/cname/stats",
    "/mgmt/tm/gtm/pool/a/stats",
    "/mgmt/tm/gtm/pool/aaaa/stats",
    "/mgmt/tm/gtm/pool/cname/stats",
    "/mgmt/tm/gtm/server/stats",
    "/mgmt/tm/gtm/datacenter/stats",
)


def _slug(path: str) -> str:
    """Turn a REST path into a safe filename stem."""
    return path.strip("/").replace("/", "_")


def sanitize(payload: Any, replacements: dict[str, str]) -> Any:
    """Redact secrets, then substring-replace caller-supplied identifiers.

    ``replacements`` maps a raw value (e.g. the device host or mgmt IP) to a
    placeholder (e.g. ``bigip.example.com``). Longer keys are applied first so a
    hostname is replaced before a bare domain fragment inside it.
    """
    redacted = redact(payload)
    if not replacements:
        return redacted
    ordered = sorted((k for k in replacements if k), key=len, reverse=True)

    def walk(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, str):
            out = value
            for raw in ordered:
                out = out.replace(raw, replacements[raw])
            return out
        return value

    return walk(redacted)


def capture_device(
    client: RestClient,
    out_dir: str | Path,
    *,
    replacements: dict[str, str] | None = None,
    endpoints: tuple[str, ...] = ENDPOINTS,
) -> dict[str, str]:
    """GET each endpoint, sanitize, and write one JSON file per success.

    Returns a mapping of endpoint -> outcome ("captured" or an error string), so
    the caller can report which record types were absent (common on a fresh VE).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    replacements = replacements or {}
    results: dict[str, str] = {}
    for path in endpoints:
        try:
            payload = client.get(path)
        except ClientError as exc:
            results[path] = f"skipped: {exc}"
            continue
        safe = sanitize(payload, replacements)
        (out / f"{_slug(path)}.json").write_text(
            json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        results[path] = "captured"
    _assert_scrubbed(out, replacements)
    return results


def _assert_scrubbed(out_dir: Path, replacements: dict[str, str]) -> None:
    """Defensive re-scan: fail loudly if any raw identifier survived to disk."""
    raw_values = [re.escape(k) for k in replacements if k]
    if not raw_values:
        return
    pattern = re.compile("|".join(raw_values))
    for f in out_dir.glob("*.json"):
        if pattern.search(f.read_text(encoding="utf-8")):
            raise RuntimeError(
                f"sanitization leak: a raw identifier survived into {f.name}; "
                "aborting so nothing sensitive is committed"
            )


__all__ = ["ENDPOINTS", "sanitize", "capture_device"]
