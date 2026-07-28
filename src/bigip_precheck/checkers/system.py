"""System / platform readiness checks (LTM + GTM, any role)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from ..core.context import RunContext
from ..core.exceptions import ClientError
from ..core.models import CheckResult, Role, Severity, Status
from . import _icontrol as ic
from .base import Checker


class VersionChecker(Checker):
    name = "system.version"
    description = "Report running TMOS software version and build."
    severity = Severity.HIGH
    applies_to = frozenset({Role.ANY})

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/sys/version")
        except ClientError as exc:
            return [
                self._result(
                    ctx,
                    Status.FAIL,
                    f"could not read software version: {exc}",
                    remediation="Verify iControl REST reachability and credentials.",
                )
            ]
        entries = ic.stats_entries(data)
        if not entries:
            return [self._result(ctx, Status.WARN, "version response was empty or unpar‑able")]
        fields = entries[0]
        version = ic.description(fields, "Version")
        build = ic.description(fields, "Build")
        product = ic.description(fields, "Product")
        return [
            self._result(
                ctx,
                Status.PASS if version else Status.WARN,
                f"{product or 'BIG-IP'} {version or 'unknown'} (build {build or 'unknown'})",
                severity=Severity.INFO,
                evidence={"version": version, "build": build, "product": product},
            )
        ]


class LicenseChecker(Checker):
    name = "system.license"
    description = "Verify the device is licensed and not past its service-check/expiry date."
    severity = Severity.CRITICAL
    applies_to = frozenset({Role.ANY})
    reference = "K7727"

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/sys/license")
        except ClientError as exc:
            return [
                self._result(
                    ctx,
                    Status.FAIL,
                    f"could not read license: {exc}",
                    reference="K7727",
                )
            ]
        entries = ic.stats_entries(data)
        if not entries:
            return [
                self._result(
                    ctx,
                    Status.FAIL,
                    "license status could not be determined",
                    reference="K7727",
                )
            ]
        fields = entries[0]
        # Nested license registration entries live under a child map; the
        # top-level fields carry the licensed date and status we need.
        licensed_on = ic.description(fields, "licensedOn") or ic.description(
            fields, "licensedVersion"
        )
        service_date = ic.description(fields, "serviceCheckDate")
        results: list[CheckResult] = []

        if not licensed_on and not service_date:
            results.append(
                self._result(
                    ctx,
                    Status.FAIL,
                    "device does not appear to be licensed",
                    remediation="Re-activate the license before upgrading.",
                    reference="K7727",
                )
            )
            return results

        status, summary = self._service_check(service_date, ctx)
        results.append(
            self._result(
                ctx,
                status,
                summary,
                severity=Severity.CRITICAL if status is Status.FAIL else Severity.MEDIUM,
                remediation=(
                    "Re-activate the license so its service-check date covers the "
                    "target software's release date."
                )
                if status is not Status.PASS
                else None,
                reference="K7727",
                evidence={"serviceCheckDate": service_date, "licensedOn": licensed_on},
            )
        )
        return results

    def _service_check(self, service_date: str, ctx: RunContext) -> tuple[Status, str]:
        parsed = _parse_bigip_date(service_date)
        if parsed is None:
            return Status.WARN, f"service-check date present but unpar‑able ({service_date!r})"
        days = (parsed - datetime.now(UTC)).days
        if days < 0:
            return (
                Status.FAIL,
                f"service-check date has passed ({service_date}); a new install may be blocked",
            )
        if days <= ctx.thresholds.license_expiry_warn_days:
            return Status.WARN, f"service-check date is near ({days} days: {service_date})"
        return Status.PASS, f"licensed; service-check date valid ({service_date})"


class ProvisioningChecker(Checker):
    name = "system.provisioning"
    description = "Report provisioned modules (LTM/GTM/etc.) and their provisioning level."
    severity = Severity.MEDIUM
    applies_to = frozenset({Role.ANY})

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/sys/provision")
        except ClientError as exc:
            return [self._result(ctx, Status.WARN, f"could not read provisioning: {exc}")]
        provisioned = {
            m["name"]: m.get("level", "none")
            for m in ic.items(data)
            if m.get("level", "none") != "none"
        }
        if not provisioned:
            return [
                self._result(
                    ctx,
                    Status.WARN,
                    "no modules appear provisioned",
                    evidence={"provisioned": {}},
                )
            ]
        listing = ", ".join(f"{k}={v}" for k, v in sorted(provisioned.items()))
        return [
            self._result(
                ctx,
                Status.PASS,
                f"provisioned modules: {listing}",
                severity=Severity.INFO,
                evidence={"provisioned": provisioned},
            )
        ]


class BootVolumeChecker(Checker):
    name = "system.boot-volumes"
    description = "Confirm a target boot volume is available and none is mid-install."
    severity = Severity.HIGH
    applies_to = frozenset({Role.ANY})

    def run(self, ctx: RunContext) -> Sequence[CheckResult]:
        try:
            data = ctx.client.get("/mgmt/tm/sys/software/volume")
        except ClientError as exc:
            return [self._result(ctx, Status.WARN, f"could not read boot volumes: {exc}")]
        volumes = ic.items(data)
        if not volumes:
            return [self._result(ctx, Status.WARN, "no boot volumes reported")]

        installing = [
            v["name"] for v in volumes if str(v.get("status", "")).lower() == "installing"
        ]
        if installing:
            return [
                self._result(
                    ctx,
                    Status.FAIL,
                    f"a software install is in progress on {', '.join(installing)}",
                    remediation="Wait for the in-progress install to finish before proceeding.",
                    evidence={"installing": installing},
                )
            ]
        inactive = [v["name"] for v in volumes if not v.get("active", False)]
        names = [v["name"] for v in volumes]
        if not inactive:
            return [
                self._result(
                    ctx,
                    Status.WARN,
                    f"only one boot volume present ({', '.join(names)}); no free install target",
                    remediation="Free or create an additional boot volume for the new image.",
                    evidence={"volumes": names},
                )
            ]
        return [
            self._result(
                ctx,
                Status.PASS,
                f"{len(inactive)} inactive boot volume(s) available: {', '.join(inactive)}",
                severity=Severity.INFO,
                evidence={"volumes": names, "inactive": inactive},
            )
        ]


def _parse_bigip_date(value: str) -> datetime | None:
    """Parse the date formats BIG-IP uses for license fields, as UTC."""
    if not value:
        return None
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%b %d, %Y", "%a %b %d %H:%M:%S %Y"):
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def checkers() -> list[Checker]:
    """Factory returning fresh instances of every system checker."""
    return [VersionChecker(), LicenseChecker(), ProvisioningChecker(), BootVolumeChecker()]


__all__ = [
    "VersionChecker",
    "LicenseChecker",
    "ProvisioningChecker",
    "BootVolumeChecker",
    "checkers",
]
