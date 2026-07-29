"""Audit trail and report-integrity helpers.

Note: this subpackage is named ``logging`` for domain clarity. It does not
shadow the standard library — absolute imports of ``logging`` elsewhere still
resolve to the stdlib module under Python 3's absolute-import rules.
"""

from __future__ import annotations

from .audit import AuditLog
from .integrity import sha256_hex, verify_digest, write_digest

__all__ = ["AuditLog", "sha256_hex", "write_digest", "verify_digest"]
