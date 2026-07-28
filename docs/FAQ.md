# FAQ

**What is `check_multi`?**
A modular, parallel, SSH-based audit framework for network appliances (primarily
F5 BIG-IP). It runs read-only checks across an inventory and produces structured
JSON plus optional Excel reports.

**Does it change device configuration?**
No. `check_multi` is strictly an **audit** tool. Every check runs read-only
commands. Modules that mutate state are not accepted (see
[Modules](MODULES.md)).

**Which platforms are supported?**
Any SSH-reachable host. The bundled checks target F5 BIG-IP (`tmsh`), but the
framework is device-agnostic — write a module with the commands you need.

**What are the requirements?**
Bash 4+, OpenSSH. Optional: `yq` (YAML config), `python3` + `openpyxl` (Excel),
`sshpass` (password auth). See [Installation](INSTALL.md).

**How do I add a new check?**
Drop `lib/checks/<name>.sh` defining `run_check()`. It appears automatically in
`--list-checks`, tab-completion and the CI smoke test. See
[Modules](MODULES.md) and [CONTRIBUTING](https://github.com/willyd61/f5-staging-precheck/blob/main/CONTRIBUTING.md).

**How does parallelism work?**
Up to `--threads` checks run concurrently; the tool throttles new jobs until a
slot frees. Tune per environment via `max_threads`.

**Is password authentication safe?**
Prefer SSH keys. Password mode (`-p`) uses `sshpass`, prints a prominent warning,
and keeps the secret only in the `SSHPASS` environment variable — never on disk.
See [Security](SECURITY.md).

**Why was my production run blocked?**
Real runs against `prod` or large inventories require confirmation to prevent
accidents. Use `-y/--yes` for unattended execution.

**Where do results go?**
`results/<timestamp>_<check>/` — containing `summary.json`, an `audit/` record,
and an Excel report when `--excel` is used.

**How do I run it unattended (cron/CI)?**
Add `-y`, prefer key auth, and pin the environment profile, e.g.
`check_multi -y -e prod certs inventory/prod.txt`.

**Can I disable colour?**
Yes — `--no-color` or set `NO_COLOR=1`. Colour is auto-disabled when output is
not a terminal.
