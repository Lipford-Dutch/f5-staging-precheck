"""Typed configuration models.

Secrets are *never* stored in these models. A device references a credential by
name; the actual username/password/token is resolved at runtime from the
environment or an interactive prompt (see :mod:`bigip_precheck.config.loader`).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ..core.models import Role


class Thresholds(BaseModel):
    """Tunable pass/warn/fail boundaries, overridable per profile."""

    model_config = {"extra": "forbid"}

    min_free_disk_pct: float = Field(default=20.0, ge=0, le=100)
    cert_expiry_warn_days: int = Field(default=30, ge=0)
    cert_expiry_fail_days: int = Field(default=7, ge=0)
    max_cpu_pct: float = Field(default=85.0, ge=0, le=100)
    license_expiry_warn_days: int = Field(default=30, ge=0)

    @field_validator("cert_expiry_fail_days")
    @classmethod
    def _fail_le_warn(cls, v: int, info: object) -> int:  # noqa: ARG003
        return v


class Device(BaseModel):
    """A single BIG-IP management endpoint.

    ``credential`` names a credential set resolved at runtime; it is not the
    secret itself. ``roles`` may be left empty and auto-detected at run time.
    """

    model_config = {"extra": "forbid"}

    name: str
    host: str
    port: int = Field(default=443, ge=1, le=65535)
    roles: list[Role] = Field(default_factory=list)
    credential: str = "default"
    tags: list[str] = Field(default_factory=list)
    snmp_community_ref: str | None = None
    verify_tls: bool = True

    @field_validator("name", "host")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()


class Profile(BaseModel):
    """A named set of checks plus threshold overrides (quick / full / gtm-only …)."""

    model_config = {"extra": "forbid"}

    name: str
    description: str = ""
    checks: list[str] = Field(default_factory=list)
    thresholds: Thresholds = Field(default_factory=Thresholds)


class Settings(BaseModel):
    """Run-wide settings independent of any single device."""

    model_config = {"extra": "forbid"}

    max_workers: int = Field(default=8, ge=1, le=128)
    connect_timeout_s: float = Field(default=10.0, gt=0)
    request_timeout_s: float = Field(default=30.0, gt=0)
    retries: int = Field(default=2, ge=0, le=10)
    backoff_base_s: float = Field(default=1.0, gt=0)
    verify_tls: bool = True
    output_dir: str = "./results/bigip-precheck"


class Inventory(BaseModel):
    """Top-level configuration document loaded from YAML."""

    model_config = {"extra": "forbid"}

    settings: Settings = Field(default_factory=Settings)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    devices: list[Device] = Field(default_factory=list)
    profiles: dict[str, Profile] = Field(default_factory=dict)

    @field_validator("devices")
    @classmethod
    def _unique_names(cls, v: list[Device]) -> list[Device]:
        names = [d.name for d in v]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            raise ValueError(f"duplicate device names: {sorted(dupes)}")
        return v


__all__ = ["Thresholds", "Device", "Profile", "Settings", "Inventory"]
