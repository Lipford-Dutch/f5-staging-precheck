"""Load and validate inventory YAML, and resolve secrets *outside* the model.

Precedence for a device credential (highest first):

1. Environment variables ``BIGIP_<CRED>_USERNAME`` / ``BIGIP_<CRED>_PASSWORD``
   (``<CRED>`` upper-cased, non-alphanumerics -> ``_``).
2. Generic ``BIGIP_USERNAME`` / ``BIGIP_PASSWORD`` fallback.
3. Interactive prompt (only when ``allow_prompt`` and attached to a TTY).

Secrets are returned as a separate :class:`Credential` object and never stored
on the :class:`~bigip_precheck.config.models.Inventory`.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from ..core.exceptions import ConfigError
from .models import Inventory


@dataclass(frozen=True)
class Credential:
    """A resolved secret set for one credential reference. Never logged raw."""

    username: str
    password: str
    token: str | None = None


def _env_key(cred: str, field: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]", "_", cred).upper()
    return f"BIGIP_{slug}_{field}"


def load_inventory(path: str | Path) -> Inventory:
    """Parse and validate an inventory YAML file into an :class:`Inventory`."""
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"inventory file not found: {p}")
    try:
        raw: Any = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - passthrough
        raise ConfigError(f"invalid YAML in {p}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"inventory root must be a mapping, got {type(raw).__name__}")
    try:
        return Inventory.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"inventory validation failed:\n{exc}") from exc


def resolve_credential(ref: str, *, allow_prompt: bool = False) -> Credential:
    """Resolve a credential reference from env vars (or an interactive prompt).

    Raises :class:`ConfigError` when nothing supplies a username/password and
    prompting is disabled — we never fall through to an empty credential, which
    would produce a misleading auth failure downstream.
    """
    username = os.environ.get(_env_key(ref, "USERNAME")) or os.environ.get("BIGIP_USERNAME")
    password = os.environ.get(_env_key(ref, "PASSWORD")) or os.environ.get("BIGIP_PASSWORD")
    token = os.environ.get(_env_key(ref, "TOKEN"))

    if token and not (username and password):
        # Token-only auth is valid: a pre-minted token skips password login.
        return Credential(username=username or "", password="", token=token)

    if not username or not password:
        if allow_prompt:
            username = username or input(f"Username for credential '{ref}': ").strip()
            password = password or getpass(f"Password for credential '{ref}': ")
        else:
            missing = "username" if not username else "password"
            raise ConfigError(
                f"missing {missing} for credential '{ref}'. "
                f"Set {_env_key(ref, missing.upper())} (or BIGIP_{missing.upper()})."
            )
    return Credential(username=username, password=password, token=token)


__all__ = ["Credential", "load_inventory", "resolve_credential"]
