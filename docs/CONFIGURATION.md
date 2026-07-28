# Configuration

`check_multi` reads YAML configuration when [`yq`](https://github.com/mikefarah/yq)
is available. Without `yq`, sane built-in defaults apply and a warning is logged.

## Files

| File | Purpose |
|------|---------|
| `config/defaults.yaml` | Base settings for every run |
| `config/environments/<name>.yaml` | Overrides applied with `-e <name>` |

## `defaults.yaml`

```yaml
max_threads: 12
ssh:
  connect_timeout: 8       # seconds to establish a connection
  command_timeout: 45      # seconds a remote command may run
  retries: 2               # additional attempts after the first failure
  backoff_seconds: 3       # delay between retries
  strict_host_key_checking: false
output:
  base_dir: "./results"
  keep_days: 30
logging:
  level: info
audit:
  enabled: true
```

## Environment profiles

Profiles overlay only the keys they specify. The bundled `prod` profile hardens
defaults:

```yaml
# config/environments/prod.yaml
ssh:
  strict_host_key_checking: true
  retries: 3
  backoff_seconds: 5
max_threads: 20
logging:
  level: warn
```

Create a new profile by dropping `config/environments/<name>.yaml` and selecting
it with `-e <name>`.

## Environment variables

| Variable | Effect |
|----------|--------|
| `NO_COLOR` | Disable coloured output (see <https://no-color.org/>) |
| `SSHPASS` | Pre-supply the SSH password for `-p` (avoids the prompt) |
| `ASSUME_YES` | When `true`, auto-approve confirmation prompts (same as `--yes`) |
| `TMPDIR` | Directory for temporary files (all created mode `0600`) |

## SSH tunables

The SSH layer honours these values (from config or the environment):

- `SSH_CONNECT_TIMEOUT`, `SSH_COMMAND_TIMEOUT`
- `SSH_RETRIES`, `SSH_BACKOFF`
- `STRICT_HOST_KEY` — when `true`, `StrictHostKeyChecking=yes` is enforced and a
  real `known_hosts` is used; when `false`, host-key checking is disabled (lab
  convenience) and a warning is printed.

See [Security](SECURITY.md) for the rationale behind the defaults.
