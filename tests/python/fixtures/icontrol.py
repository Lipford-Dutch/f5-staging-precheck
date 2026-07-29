"""Synthesized iControl REST payloads.

These mirror the shapes real TMOS 15.1–17.x devices return. They are hand-built
from public F5 schemas so the suite runs with no lab. Real sanitized captures
can drop into this module later without touching the tests that consume it.
"""

from __future__ import annotations

from typing import Any


def _stats(fields: dict[str, str], self_link: str = "https://localhost/mgmt/tm/x/0") -> dict[str, Any]:
    """Wrap a flat {field: value} map in the nestedStats envelope."""
    return {
        "kind": "tm:x:xstats",
        "entries": {
            self_link: {
                "nestedStats": {
                    "entries": {k: {"description": v} for k, v in fields.items()}
                }
            }
        },
    }


VERSION = _stats(
    {
        "Product": "BIG-IP",
        "Version": "16.1.3.3",
        "Build": "0.0.4",
        "Edition": "Point Release 3",
    }
)

LICENSE_OK = _stats(
    {
        "licensedOn": "2025/01/15",
        "licensedVersion": "16.1.3",
        "serviceCheckDate": "2027/01/15",
        "registrationKey": "AAAAA-BBBBB-CCCCC-DDDDD-EEEEEEE",
    }
)

LICENSE_EXPIRED = _stats(
    {
        "licensedOn": "2019/01/15",
        "serviceCheckDate": "2020/01/15",
    }
)

LICENSE_UNLICENSED: dict[str, Any] = {"kind": "tm:sys:license:licensestats", "entries": {}}

PROVISION = {
    "kind": "tm:sys:provision:provisioncollectionstate",
    "items": [
        {"name": "ltm", "level": "nominal"},
        {"name": "gtm", "level": "nominal"},
        {"name": "afm", "level": "none"},
        {"name": "asm", "level": "none"},
    ],
}

BOOT_VOLUMES = {
    "kind": "tm:sys:software:volume:volumecollectionstate",
    "items": [
        {"name": "HD1.1", "active": True, "version": "16.1.3.3", "status": "complete"},
        {"name": "HD1.2", "active": False, "version": "15.1.5", "status": "complete"},
    ],
}

BOOT_VOLUMES_SINGLE = {
    "kind": "tm:sys:software:volume:volumecollectionstate",
    "items": [
        {"name": "HD1.1", "active": True, "version": "16.1.3.3", "status": "complete"},
    ],
}

BOOT_VOLUMES_INSTALLING = {
    "kind": "tm:sys:software:volume:volumecollectionstate",
    "items": [
        {"name": "HD1.1", "active": True, "version": "16.1.3.3", "status": "complete"},
        {"name": "HD1.2", "active": False, "version": "17.1.0", "status": "installing"},
    ],
}

FAILOVER_STANDBY = _stats({"color": "green", "status": "STANDBY", "summary": "1/1 active"})
FAILOVER_ACTIVE = _stats({"color": "green", "status": "ACTIVE", "summary": "1/1 active"})
FAILOVER_YELLOW = _stats({"color": "yellow", "status": "ACTIVE", "summary": "0/1 active"})

SYNC_IN_SYNC = _stats(
    {"color": "green", "mode": "high-availability", "status": "In Sync", "summary": "All devices in sync"}
)
SYNC_CHANGES_PENDING = _stats(
    {
        "color": "yellow",
        "mode": "high-availability",
        "status": "Changes Pending",
        "summary": "There is a possible change conflict",
    }
)
SYNC_STANDALONE = _stats({"color": "green", "mode": "standalone", "status": "Standalone", "summary": ""})


# A healthy device answers every path the phase-A checkers query.
HEALTHY_HA_STANDBY: dict[str, dict[str, Any]] = {
    "/mgmt/tm/sys/version": VERSION,
    "/mgmt/tm/sys/license": LICENSE_OK,
    "/mgmt/tm/sys/provision": PROVISION,
    "/mgmt/tm/sys/software/volume": BOOT_VOLUMES,
    "/mgmt/tm/cm/failover-status": FAILOVER_STANDBY,
    "/mgmt/tm/cm/sync-status": SYNC_IN_SYNC,
}

# An unhealthy device: expired license and config-sync not in sync.
UNHEALTHY: dict[str, dict[str, Any]] = {
    "/mgmt/tm/sys/version": VERSION,
    "/mgmt/tm/sys/license": LICENSE_EXPIRED,
    "/mgmt/tm/sys/provision": PROVISION,
    "/mgmt/tm/sys/software/volume": BOOT_VOLUMES_SINGLE,
    "/mgmt/tm/cm/failover-status": FAILOVER_ACTIVE,
    "/mgmt/tm/cm/sync-status": SYNC_CHANGES_PENDING,
}
