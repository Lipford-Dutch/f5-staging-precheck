"""Tests for the audit trail and report integrity helpers."""

from __future__ import annotations

import json
from pathlib import Path

from bigip_precheck.logging.audit import AuditLog
from bigip_precheck.logging.integrity import verify_digest, write_digest
from bigip_precheck.redaction import REDACTED


def test_audit_writes_redacted_jsonl(tmp_path: Path):
    audit = AuditLog(tmp_path)
    audit.event("run_config", password="hunter2", note="ok")
    audit.close(decision="GO")

    lines = audit.jsonl_path.read_text().strip().splitlines()
    records = [json.loads(line) for line in lines]
    kinds = [r["event"] for r in records]
    assert "session_start" in kinds and "run_config" in kinds and "session_end" in kinds

    run_config = next(r for r in records if r["event"] == "run_config")
    assert run_config["password"] == REDACTED
    assert run_config["note"] == "ok"
    assert audit.log_path.is_file()  # human log also written


def test_integrity_roundtrip(tmp_path: Path):
    report = tmp_path / "report.json"
    report.write_text('{"decision": "GO"}\n', encoding="utf-8")
    sidecar = write_digest(report)
    assert sidecar.is_file()
    assert verify_digest(report) is True

    report.write_text('{"decision": "NO-GO"}\n', encoding="utf-8")  # tamper
    assert verify_digest(report) is False


def test_verify_digest_missing_sidecar(tmp_path: Path):
    report = tmp_path / "r.json"
    report.write_text("{}", encoding="utf-8")
    assert verify_digest(report) is False
