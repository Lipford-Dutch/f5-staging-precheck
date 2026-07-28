# Security Model – check_multi 2.0

## Principles
1. Prefer SSH public-key authentication.
2. Never write credentials to disk.
3. Temporary files are mode 0600 and cleaned on exit.
4. Output directories are mode 0750; logs/results are 0640.
5. Host-key checking is controlled by environment profile.
6. Every run produces an audit trail.

## Password Mode
Password authentication via `sshpass` is supported only for emergency / migration use.
When enabled (`-p`), a large red warning banner is displayed.
The password is held only in the `SSHPASS` environment variable and is never written to a file.

**Recommendation:** Migrate all devices to key-based auth as soon as practical.

## Host Key Checking
- Lab profile: `strict_host_key_checking: false` (convenient for lab rebuilds)
- Prod profile: `strict_host_key_checking: true` (recommended)

## Temporary Files
All temporary files are created with `mktemp`, immediately set to mode 0600, tracked, and removed by the EXIT/INT/TERM/HUP trap.

## Audit Trail
Every run writes an immutable JSON record under `results/.../audit/` containing:
- Run ID, timestamps, operator, host
- Check name, inventory path
- Success / failure counts
- Dry-run flag

## Hardening Checklist for Production
- [ ] Use SSH keys only (disable `-p`)
- [ ] Set `strict_host_key_checking: true` in prod profile
- [ ] Run from a dedicated jump host with restricted access
- [ ] Keep inventories in a controlled location
- [ ] Review audit logs periodically
- [ ] Pin tool version and review changes before upgrading
