# Check Modules & Roadmap

`check_multi` is plugin-driven: every file in `lib/checks/<name>.sh` that defines
a `run_check()` function becomes a selectable check. This page lists the modules
that ship today and a prioritised roadmap of proposed additions.

## Module contract

```bash
#!/usr/bin/env bash
# check: <name> – <one-line description>
run_check() {
  local device=$1
  ssh_exec "$device" "tmsh ..." || return 1
}
```

- Return `0` on success, non-zero on failure.
- Use `ssh_exec` (never raw `ssh`) so retries, timeouts, dry-run and quoting are
  handled centrally.
- Keep remote commands read-only. `check_multi` is an **audit** tool; modules
  must never mutate device state.

## Shipping modules

| Module | Purpose | Primary command(s) |
|--------|---------|--------------------|
| `preflight` | Connectivity + version smoke test | `echo OK`, `tmsh show sys version` |
| `platform`  | Version, hardware, provisioning | `tmsh show sys version/hardware`, `list sys provision` |
| `umm`       | Provisioned modules | `tmsh list sys provision` |
| `certs`     | SSL certificate inventory | `tmsh list sys file ssl-cert` |
| `keys`      | SSL key inventory | `tmsh list sys file ssl-key` |
| `syncgroup` | Device-group sync status | `tmsh show cm sync-status` |
| `network`   | Interfaces & trunks | `tmsh show net interface/trunk` |
| `ntp`       | Clock sync & NTP config | `tmsh list sys ntp`, `ntpq -pn` |
| `license`   | Licence status & feature modules | `tmsh show sys license` |
| `diskspace` | Filesystem utilisation | `df -h`, `tmsh show sys disk` |
| `ha`        | Active/standby & failover health | `tmsh show sys failover` |

## Roadmap — proposed modules

Grouped by theme and roughly ordered by value for a staging pre-check workflow.

### Change-readiness (high priority)
- **`ucs`** – Verify a recent UCS backup exists and is restorable
  (`tmsh show sys ucs`, age of newest archive).
- **`config-sync-drift`** – Detect pending/unsynced config across the device
  group beyond a simple status string.
- **`cert-expiry`** – Flag certificates expiring within *N* days (parse the
  `expiration` field rather than dumping the inventory).
- **`ssl-profiles`** – Map cert/key usage to client/server SSL profiles to catch
  orphaned or shared material before rotation.

### Health & capacity
- **`cpu-mem`** – TMM/CPU and memory pressure (`tmsh show sys cpu/memory`).
- **`connection-stats`** – Current vs. licensed connection/throughput limits.
- **`pool-health`** – Pools/members with down or forced-offline nodes
  (`tmsh show ltm pool`).
- **`virtual-servers`** – Virtual server availability and offline VIPs.

### Platform & security
- **`software-images`** – Installed/boot volumes and available images
  (`tmsh show sys software`).
- **`hotfix`** – Applied hotfixes vs. a desired baseline.
- **`accounts`** – Local admin accounts, auth source, and password policy.
- **`snmp-logging`** – SNMP, syslog and remote logging destinations.
- **`dns-resolvers`** – Configured DNS resolvers and reachability.

### Reporting & integration
- **JSON/HTML per-check artefacts** – Structured per-device output for each
  module (not just pass/fail) so reports can show the captured data.
- **Baseline diffing** – Compare a run against a stored golden baseline and
  report drift.

## Suggesting or contributing a module

Open an issue describing the check and the tmsh command(s) it runs, or follow
[CONTRIBUTING.md](../CONTRIBUTING.md) to add one directly. New modules should
ship with a matching entry in the CI dry-run smoke test and a short note here.
