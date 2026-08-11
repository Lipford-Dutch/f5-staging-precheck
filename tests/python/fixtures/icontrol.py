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
    # Shape and values confirmed against a real BIG-IP VE running TMOS 17.5.1.8.
    {
        "Product": "BIG-IP",
        "Version": "17.5.1.8",
        "Build": "0.0.19",
        "Edition": "Point Release 1",
    }
)

# A standalone VE with only LTM provisioned — the common lab shape. Confirmed
# against a real 17.5.1.8 device.
PROVISION_LTM_ONLY = {
    "kind": "tm:sys:provision:provisioncollectionstate",
    "items": [
        {"name": "ltm", "level": "nominal"},
        {"name": "gtm", "level": "none"},
        {"name": "afm", "level": "none"},
        {"name": "asm", "level": "none"},
    ],
}

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


def _obj_stats(objects: list[dict[str, str]], self_prefix: str = "obj") -> dict[str, Any]:
    """Build a multi-object /stats payload from a list of {name, avail, enabled, reason}."""
    entries: dict[str, Any] = {}
    for i, o in enumerate(objects):
        fields = {
            "tmName": o["name"],
            "status.availabilityState": o.get("avail", "available"),
            "status.enabledState": o.get("enabled", "enabled"),
            "status.statusReason": o.get("reason", ""),
        }
        if "activeMemberCnt" in o:
            fields["activeMemberCnt"] = o["activeMemberCnt"]
        entries[f"https://localhost/mgmt/tm/{self_prefix}/{i}"] = {
            "nestedStats": {"entries": {k: {"description": v} for k, v in fields.items()}}
        }
    return {"kind": "tm:stats", "entries": entries}


# --- LTM object stats -----------------------------------------------------
VS_STATS_HEALTHY = _obj_stats(
    [
        {"name": "/Common/vs_web", "avail": "available", "enabled": "enabled",
         "reason": "The virtual server is available"},
        {"name": "/Common/vs_api", "avail": "available", "enabled": "enabled"},
    ],
    "ltm/virtual",
)
VS_STATS_DOWN = _obj_stats(
    [
        {"name": "/Common/vs_web", "avail": "available", "enabled": "enabled"},
        {"name": "/Common/vs_api", "avail": "offline", "enabled": "enabled",
         "reason": "The children pool member(s) are down"},
        {"name": "/Common/vs_old", "avail": "offline", "enabled": "disabled",
         "reason": "administratively disabled"},
    ],
    "ltm/virtual",
)
POOL_STATS_HEALTHY = _obj_stats(
    [
        {"name": "/Common/pool_web", "avail": "available", "enabled": "enabled",
         "activeMemberCnt": "3"},
        {"name": "/Common/pool_api", "avail": "available", "enabled": "enabled",
         "activeMemberCnt": "2"},
    ],
    "ltm/pool",
)
POOL_STATS_NO_MEMBERS = _obj_stats(
    [
        {"name": "/Common/pool_web", "avail": "available", "enabled": "enabled",
         "activeMemberCnt": "3"},
        {"name": "/Common/pool_empty", "avail": "offline", "enabled": "enabled",
         "activeMemberCnt": "0", "reason": "No members available"},
    ],
    "ltm/pool",
)
# Seen on the real 17.5.1.8 VE: a configured node whose monitors have not yet
# reported, so availability is "unknown" while the node is still enabled.
NODE_STATS_UNKNOWN = _obj_stats(
    [
        {"name": "/Common/192.0.2.50", "avail": "unknown", "enabled": "enabled",
         "reason": "Node address does not have service checking enabled"},
    ],
    "ltm/node",
)
NODE_STATS_HEALTHY = _obj_stats(
    [
        {"name": "/Common/10.0.1.10", "avail": "available", "enabled": "enabled"},
        {"name": "/Common/10.0.1.11", "avail": "available", "enabled": "enabled"},
    ],
    "ltm/node",
)

# --- GTM object stats -----------------------------------------------------
WIDEIP_A_HEALTHY = _obj_stats(
    [{"name": "/Common/app.example.com", "avail": "available", "enabled": "enabled"}],
    "gtm/wideip/a",
)
WIDEIP_A_DOWN = _obj_stats(
    [{"name": "/Common/app.example.com", "avail": "offline", "enabled": "enabled",
      "reason": "No enabled pools available"}],
    "gtm/wideip/a",
)
EMPTY_STATS: dict[str, Any] = {"kind": "tm:stats", "entries": {}}
GTM_POOL_A_HEALTHY = _obj_stats(
    [{"name": "/Common/pool_gslb", "avail": "available", "enabled": "enabled"}],
    "gtm/pool/a",
)
GTM_SERVER_HEALTHY = _obj_stats(
    [
        {"name": "/Common/dc1-bigip", "avail": "available", "enabled": "enabled"},
        {"name": "/Common/dc2-bigip", "avail": "available", "enabled": "enabled"},
    ],
    "gtm/server",
)
DATACENTER_HEALTHY = _obj_stats(
    [
        {"name": "/Common/DC1", "avail": "available", "enabled": "enabled"},
        {"name": "/Common/DC2", "avail": "available", "enabled": "enabled"},
    ],
    "gtm/datacenter",
)


# A healthy device answers every path the phase-A checkers query.
HEALTHY_HA_STANDBY: dict[str, dict[str, Any]] = {
    "/mgmt/tm/sys/version": VERSION,
    "/mgmt/tm/sys/license": LICENSE_OK,
    "/mgmt/tm/sys/provision": PROVISION,
    "/mgmt/tm/sys/software/volume": BOOT_VOLUMES,
    "/mgmt/tm/cm/failover-status": FAILOVER_STANDBY,
    "/mgmt/tm/cm/sync-status": SYNC_IN_SYNC,
    "/mgmt/tm/ltm/virtual/stats": VS_STATS_HEALTHY,
    "/mgmt/tm/ltm/pool/stats": POOL_STATS_HEALTHY,
    "/mgmt/tm/ltm/node/stats": NODE_STATS_HEALTHY,
    "/mgmt/tm/gtm/wideip/a/stats": WIDEIP_A_HEALTHY,
    "/mgmt/tm/gtm/wideip/aaaa/stats": EMPTY_STATS,
    "/mgmt/tm/gtm/wideip/cname/stats": EMPTY_STATS,
    "/mgmt/tm/gtm/pool/a/stats": GTM_POOL_A_HEALTHY,
    "/mgmt/tm/gtm/pool/aaaa/stats": EMPTY_STATS,
    "/mgmt/tm/gtm/pool/cname/stats": EMPTY_STATS,
    "/mgmt/tm/gtm/server/stats": GTM_SERVER_HEALTHY,
    "/mgmt/tm/gtm/datacenter/stats": DATACENTER_HEALTHY,
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

# A standalone VE with ONLY LTM provisioned, mirroring a real 17.5.1.8 lab box:
# every GTM endpoint 404s. Modelled after an actual device — the GTM paths are
# absent from this map, and FakeRestClient raises NotFound for them.
STANDALONE_LTM_ONLY: dict[str, dict[str, Any]] = {
    "/mgmt/tm/sys/version": VERSION,
    "/mgmt/tm/sys/license": LICENSE_OK,
    "/mgmt/tm/sys/provision": PROVISION_LTM_ONLY,
    "/mgmt/tm/sys/software/volume": BOOT_VOLUMES_SINGLE,
    "/mgmt/tm/cm/failover-status": FAILOVER_ACTIVE,
    "/mgmt/tm/cm/sync-status": SYNC_STANDALONE,
    "/mgmt/tm/ltm/virtual/stats": EMPTY_STATS,
    "/mgmt/tm/ltm/pool/stats": EMPTY_STATS,
    "/mgmt/tm/ltm/node/stats": NODE_STATS_HEALTHY,
}
