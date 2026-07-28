# Usage

`check_multi` runs a single **check** against every device in an **inventory
file**, in parallel, and writes structured results.

```text
check_multi [OPTIONS] <check_name> <inventory_file>
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `-h, --help` | Show help and exit | – |
| `-d, --dry-run` | Never open SSH connections; print what would run | off |
| `-v, --verbose` | Debug logging | off |
| `-t, --threads <N>` | Maximum parallel SSH sessions (positive integer) | `12` (or config) |
| `-o, --output-dir <DIR>` | Results directory | `results/<ts>_<check>` |
| `-e, --env <name>` | Environment profile (`config/environments/<name>.yaml`) | `lab` |
| `-c, --config <FILE>` | Alternate `defaults.yaml` | bundled defaults |
| `-u, --user <USER>` | SSH username | current user |
| `-p, --password` | Password auth via `sshpass` (**discouraged**) | off |
| `-y, --yes` | Assume "yes" for confirmation prompts (unattended runs) | off |
| `--excel` | Also generate an executive Excel report | off |
| `--no-color` | Disable coloured output (also honours `NO_COLOR`) | off |
| `--list-checks` | Print available check modules and exit | – |
| `--version` | Print version and exit | – |

## Argument precedence

Configuration is resolved in this order (later wins):

1. Built-in defaults
2. `config/defaults.yaml` (or `--config`)
3. `config/environments/<env>.yaml`
4. **Command-line flags** — an explicit flag such as `-t` always wins.

## Safety behaviours

These exist to prevent common operator mistakes:

- **Fast validation.** Thread count, check name, inventory existence and the
  environment profile are validated *before* any connection is attempted.
- **"Did you mean…?"** A mistyped check name suggests close matches and points
  to `--list-checks`.
- **High-impact confirmation.** A *real* (non-dry-run) execution against the
  `prod` profile or a large inventory (≥ 50 devices) prompts for confirmation.
  Pass `-y/--yes` for unattended runs; on a non-interactive shell the run
  aborts unless `--yes` is given.
- **Path-safe check names.** Check names are restricted to `[A-Za-z0-9_-]`.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success — all device checks passed |
| `1` | Usage or configuration error |
| `4` | One or more device checks failed |

## Examples

```bash
# Safe preview — no SSH, populated summary.json
check_multi --dry-run platform examples/devices.txt

# Lab run, 10 threads, with an Excel report
check_multi -e lab -t 10 --excel platform examples/devices.txt

# Production certificate audit, unattended
check_multi -e prod --yes certs inventory/prod.txt

# Discover available checks
check_multi --list-checks
```

## Output layout

```text
results/YYYYMMDD_HHMMSS_<check>/
├── audit/run_*.json      # immutable per-run audit record
├── summary.json          # structured results (devices, counts, rate)
└── Device_Audit_Report_*.xlsx   # only with --excel
```

See [Configuration](CONFIGURATION.md) for tuning and
[Troubleshooting](TROUBLESHOOTING.md) for common issues.
