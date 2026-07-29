"""Tests for inventory loading, validation and credential resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from bigip_precheck.config.loader import load_inventory, resolve_credential
from bigip_precheck.core.exceptions import ConfigError

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "bigip-precheck" / "inventory.yaml"


def test_example_inventory_is_valid():
    inv = load_inventory(EXAMPLE)
    assert len(inv.devices) == 3
    assert "full" in inv.profiles
    assert inv.profiles["full"].checks


def test_missing_file_raises():
    with pytest.raises(ConfigError, match="not found"):
        load_inventory("/no/such/inventory.yaml")


def test_duplicate_device_names_rejected(tmp_path: Path):
    p = tmp_path / "inv.yaml"
    p.write_text(
        "devices:\n"
        "  - {name: dup, host: 1.1.1.1}\n"
        "  - {name: dup, host: 2.2.2.2}\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="duplicate"):
        load_inventory(p)


def test_unknown_field_rejected(tmp_path: Path):
    p = tmp_path / "inv.yaml"
    p.write_text("settings:\n  bogus: 1\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_inventory(p)


def test_resolve_credential_from_env(monkeypatch):
    monkeypatch.setenv("BIGIP_DEFAULT_USERNAME", "admin")
    monkeypatch.setenv("BIGIP_DEFAULT_PASSWORD", "s3cret")
    cred = resolve_credential("default")
    assert cred.username == "admin"
    assert cred.password == "s3cret"


def test_resolve_credential_missing_raises(monkeypatch):
    monkeypatch.delenv("BIGIP_DEFAULT_USERNAME", raising=False)
    monkeypatch.delenv("BIGIP_DEFAULT_PASSWORD", raising=False)
    monkeypatch.delenv("BIGIP_USERNAME", raising=False)
    monkeypatch.delenv("BIGIP_PASSWORD", raising=False)
    with pytest.raises(ConfigError):
        resolve_credential("default", allow_prompt=False)


def test_resolve_credential_token_only(monkeypatch):
    monkeypatch.delenv("BIGIP_DEFAULT_USERNAME", raising=False)
    monkeypatch.delenv("BIGIP_DEFAULT_PASSWORD", raising=False)
    monkeypatch.setenv("BIGIP_DEFAULT_TOKEN", "tok123")
    cred = resolve_credential("default")
    assert cred.token == "tok123"
