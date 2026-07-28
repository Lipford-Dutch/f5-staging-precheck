# Troubleshooting

Practical fixes for the issues operators hit most often. Start every
investigation with `--dry-run` and `-v/--verbose`.

## Diagnostics first

```bash
# Prove the tool, inventory and check are wired up — no network needed
check_multi --dry-run -v <check> <inventory>
```

Dry-run validates arguments, loads the inventory and exercises the code path
without opening a single SSH connection.

## Common issues

### "requires a value" / usage error
A flag was given without its argument (e.g. `-t` with nothing after it), or the
positional `<check>` / `<inventory>` were omitted. Check `--help`.

### "Unknown check: …"
The check name is misspelled or the module isn't installed. Run
`check_multi --list-checks`; the error also suggests near matches.

### "--threads must be a positive integer"
`-t` was given a non-numeric or zero value. Note that an explicit `-t` always
overrides `max_threads` from YAML.

### "Confirmation required but stdin is not a TTY"
A real run against `prod` (or a large inventory) needs confirmation. In cron/CI,
add `-y/--yes` (or set `ASSUME_YES=true`).

### SSH failures / timeouts
- Confirm reachability: `ssh <user>@<device>` by hand.
- The tool retries per `ssh.retries`/`ssh.backoff_seconds`; increase them for
  flaky links.
- Increase `ssh.connect_timeout` / `ssh.command_timeout` for slow devices.
- Prefer **SSH keys**. Password mode (`-p`) is for emergencies only.

### Host key verification failed
The `prod` profile enforces `StrictHostKeyChecking=yes`. Add the device to your
`known_hosts`, or (lab only) use a profile with
`strict_host_key_checking: false`.

### YAML config seems ignored
`yq` (mikefarah) isn't installed, so built-in defaults are used — you'll see a
warning. Install `yq` to enable `config/*.yaml`.

### Excel report not produced
`--excel` needs `python3` and `openpyxl`
(`pip install openpyxl`). Without them a warning is logged and the run still
succeeds; `summary.json` is always written.

### Devices skipped as "invalid inventory entry"
Entries are rejected if they contain whitespace or shell metacharacters. One
host per line; use `#` for comments (inline comments are supported).

## Where to look

- `results/<run>/summary.json` — machine-readable results and counts.
- `results/<run>/audit/run_*.json` — who ran what, when, and the outcome.
- Re-run with `-v` for per-attempt SSH debug logging on stderr.

Still stuck? Open an issue with the `--dry-run -v` output (redact hostnames).
