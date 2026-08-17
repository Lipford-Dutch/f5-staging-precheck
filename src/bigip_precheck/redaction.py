"""Central secret scrubbing.

Every string bound for a log, an audit record, or a result's ``evidence`` passes
through here first. Redaction is deny-by-default for a small set of well-known
secret-bearing keys, plus regex sweeps for tokens that leak into free text
(iControl auth tokens, ``Set-Cookie`` values, basic-auth headers).
"""

from __future__ import annotations

import re
from typing import Any

REDACTED = "***REDACTED***"

# Dict keys whose values are always secrets, matched case-insensitively.
_SECRET_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "x-f5-auth-token",
        "authorization",
        "auth",
        "community",
        "snmp_community",
        "cookie",
        "set-cookie",
        "credential",
        "credentials",
        "registrationkey",
    }
)

# Free-text patterns. Ordered; each replaces the sensitive span with REDACTED.
_TEXT_PATTERNS: tuple[re.Pattern[str], ...] = (
    # iControl REST auth tokens look like long base32-ish blobs.
    re.compile(r"(X-F5-Auth-Token\s*[:=]\s*)\S+", re.IGNORECASE),
    # Capture the ENTIRE header value (scheme + credentials), not just the
    # first token: "Authorization: Basic <base64>" must not leak the base64.
    re.compile(r"(Authorization\s*[:=]\s*).+", re.IGNORECASE),
    re.compile(r"(Basic\s+)[A-Za-z0-9+/=]{8,}", re.IGNORECASE),
    re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+", re.IGNORECASE),
)


def redact_text(text: str) -> str:
    """Return ``text`` with any recognised secret spans replaced."""
    out = text
    for pat in _TEXT_PATTERNS:
        out = pat.sub(lambda m: f"{m.group(1)}{REDACTED}", out)
    return out


def redact(value: Any) -> Any:
    """Recursively redact secrets from an arbitrary JSON-like structure.

    * ``dict`` — any key in :data:`_SECRET_KEYS` has its value replaced wholesale;
      other values are recursed into.
    * ``list``/``tuple`` — each element is redacted.
    * ``str`` — swept for inline secret patterns.
    * everything else is returned unchanged.
    """
    if isinstance(value, dict):
        result: dict[Any, Any] = {}
        for key, val in value.items():
            if isinstance(key, str) and key.lower() in _SECRET_KEYS:
                result[key] = REDACTED
            else:
                result[key] = redact(val)
        return result
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


__all__ = ["redact", "redact_text", "REDACTED"]
