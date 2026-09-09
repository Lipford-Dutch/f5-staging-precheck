
# check_multi 2.0

**Enterprise Device Audit Framework**  
Multi-function, parallel SSH-based audit tool for network appliances (primarily F5 BIG-IP).

[![CI](https://github.com/willyd61/f5-staging-precheck/actions/workflows/ci.yml/badge.svg)](https://github.com/willyd61/f5-staging-precheck/actions/workflows/ci.yml)
[![Docs](https://github.com/willyd61/f5-staging-precheck/actions/workflows/docs.yml/badge.svg)](https://github.com/willyd61/f5-staging-precheck/actions/workflows/docs.yml)
[![Version](https://img.shields.io/badge/Version-2.0.0--alpha-orange)]()
[![ShellCheck](https://img.shields.io/badge/ShellCheck-clean-brightgreen)]()
[![License](https://img.shields.io/badge/License-Internal-blue)]()

📖 **Documentation site:** <https://willyd61.github.io/f5-staging-precheck/>

---

## Overview

`check_multi` is a modular, secure, and governance-ready framework for running configuration, health, and compliance checks against large inventories of network devices.

It was completely redesigned from a legacy monolithic Bash script into a clean, extensible architecture following industry best practices.

> **New:** [`bigip-precheck`](src/bigip_precheck/README.md) is a Python,
> **iControl REST**–driven companion focused on **pre-upgrade / change-window
> readiness** for LTM & GTM. Where `check_multi` runs fast SSH/tmsh sweeps,
> `bigip-precheck` performs deeper REST checks and emits a per-device and overall
> **GO / NO-GO** verdict with a full audit trail. See its
> [README](src/bigip_precheck/README.md) and
> [architecture](docs/bigip-precheck/ARCHITECTURE.md). *(alpha; phase A)*

### Key Features (Alpha)

| Feature                        | Status |
|--------------------------------|--------|
| Modular library architecture   | ✅     |
| External YAML configuration    | ✅     |
| Plugin-style check modules     | ✅     |
| Secure SSH abstraction         | ✅     |
| Dry-run mode                   | ✅     |
| Structured logging + JSON      | ✅     |
| Retry with backoff             | ✅     |
| Inventory pre-flight validation| ✅     |
| Executive Excel reports        | ✅     |
| Audit trail / run logging      | ✅     |
| Environment profiles (lab/prod)| ✅     |
| Argument validation + safety prompts | ✅ |
| "Did you mean…?" check suggestions | ✅ |
| Bash tab-completion            | ✅     |
| GitHub Actions CI (lint, tests, smoke) | ✅ |
| Published docs site (GitHub Pages) | ✅ |

---

## Requirements

| Tool | Purpose | Required |
|------|---------|----------|
| `bash` ≥ 4 | Runtime | Yes |
| `ssh` / OpenSSH | Device access | Yes |
| `yq` (mikefarah) | YAML config/profiles | Optional (falls back to built-in defaults) |
| `python3` + `openpyxl` | `--excel` reports | Optional |
| `sshpass` | Password auth (`-p`, discouraged) | Optional |
| `shellcheck`, `bats` | Development / CI | Dev only |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/willyd61/f5-staging-precheck.git
cd f5-staging-precheck

# View help
./bin/check_multi --help

# Safe dry-run against example inventory
./bin/check_multi --dry-run platform examples/devices.txt

# Real run with Excel report
./bin/check_multi -e lab -t 10 --excel platform examples/devices.txt
```

---

## Documentation

The full, styled documentation is published to
**[GitHub Pages](https://willyd61.github.io/f5-staging-precheck/)** and built
from the Markdown under [`docs/`](docs/):

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](docs/QUICKSTART.md) | First-run guide |
| [INSTALL.md](docs/INSTALL.md) | Detailed installation instructions |
| [USAGE.md](docs/USAGE.md) | Full CLI reference and safety behaviours |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | YAML config, profiles, env vars |
| [MODULES.md](docs/MODULES.md) | Check catalogue and roadmap |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical design |
| [SECURITY.md](docs/SECURITY.md) | Security model and recommendations |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [FAQ.md](docs/FAQ.md) | Frequently asked questions |

---

## Architecture

```
check_multi_2.0/
├── bin/check_multi              # Main CLI entry point
├── lib/
│   ├── common.sh                # Logging, colours, utils, temp files
│   ├── ssh.sh                   # Secure SSH + retry abstraction
│   ├── inventory.sh             # Device list loading & validation
│   ├── parallel.sh              # Concurrency control
│   ├── config.sh                # YAML config loader
│   ├── audit.sh                 # Run audit trail
│   ├── summary.sh               # summary.json generator
│   ├── registry.sh              # Check discovery + name validation
│   └── checks/                  # Plugin check modules
│       ├── platform.sh  umm.sh  certs.sh  keys.sh
│       ├── syncgroup.sh network.sh preflight.sh
│       └── ntp.sh  license.sh  diskspace.sh  ha.sh
├── config/
│   ├── defaults.yaml
│   └── environments/{lab,prod}.yaml
├── completions/check_multi.bash   # Bash tab-completion
├── scripts/
│   ├── generate_excel_report.py
│   ├── build_docs.py            # Guide generator      → site/docs/
│   ├── build_hero.py            # Hero landing page    → site/index.html
│   └── shellcheck_all.sh
├── docs/                        # Markdown → published to GitHub Pages
├── examples/  tests/  Makefile
└── .github/workflows/{ci.yml,docs.yml}
```

### Published site

A repository gets exactly one GitHub Pages site, so both parts ship in a single
deployment (`docs.yml`) rather than competing workflows:

```
/            hero landing page              ← scripts/build_hero.py
/docs/       technical user + admin guide   ← scripts/build_docs.py
```

Build it locally with `make docs` (or `make docs-serve` to preview on :8000).

---

## Usage

```text
check_multi [OPTIONS] <check_name> <inventory_file>
```

### Global Options

| Option                    | Description                              |
|---------------------------|------------------------------------------|
| `-h, --help`              | Show help                                |
| `-d, --dry-run`           | No SSH connections                       |
| `-v, --verbose`           | Debug logging                            |
| `-t, --threads <N>`       | Max parallel sessions                    |
| `-o, --output-dir <DIR>`  | Results directory                        |
| `-e, --env <lab\|prod>`   | Environment profile                      |
| `-c, --config <FILE>`     | Override defaults.yaml                   |
| `-u, --user <USER>`       | SSH username                             |
| `-p, --password`          | Use password auth (discouraged)          |
| `-y, --yes`               | Assume "yes" for confirmation prompts     |
| `--excel`                 | Generate executive Excel report          |
| `--no-color`              | Disable coloured output (also `NO_COLOR`) |
| `--list-checks`           | List available check modules and exit     |
| `--version`               | Print version                            |

Command-line flags always override YAML config. Real runs against `prod` or
large inventories (≥ 50 devices) prompt for confirmation; use `-y` for
unattended execution. See [USAGE.md](docs/USAGE.md) for full details.

### Available Checks

Run `check_multi --list-checks` for the live list.

- `preflight`  – Lightweight connectivity + version check
- `platform`   – Version, build, modules, serial, telemetry
- `umm`        – Provisioned modules
- `certs`      – Certificate inventory
- `keys`       – Key inventory
- `syncgroup`  – CM sync status
- `network`    – Interfaces & trunks
- `ntp`        – NTP config and clock synchronisation
- `license`    – Licence status and feature modules
- `diskspace`  – Filesystem utilisation
- `ha`         – Active/standby and failover state

New checks are added by dropping a module in `lib/checks/` — see
[MODULES.md](docs/MODULES.md).

### Shell completion

```bash
# Enable tab-completion for the current shell
source completions/check_multi.bash
```

---

## Security Model

1. **Prefer SSH keys** – password mode (`-p`) prints a large warning.
2. Temporary files are created with mode `0600` and removed on exit.
3. Output directories use `0750`.
4. Host key checking is controlled via environment profile.
5. Full audit trail of every run.

---

## Development

All developer tasks are wrapped in the `Makefile`:

```bash
make lint        # ShellCheck every script (including bin/check_multi)
make syntax      # bash -n syntax check
make test        # bats unit tests
make smoke       # dry-run every check module (auto-discovered)
make check       # all of the above
make docs        # build the documentation site into ./site
make docs-serve  # build + serve docs at http://localhost:8000
make clean       # remove ./results and ./site
```

CI runs the same checks on every push and pull request (see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml)), and the documentation
site is built and deployed to GitHub Pages on merge to `main` (see
[`.github/workflows/docs.yml`](.github/workflows/docs.yml)). Please run
`make check` before opening a PR. Contribution guidelines live in
[CONTRIBUTING.md](CONTRIBUTING.md); notable changes are recorded in
[CHANGELOG.md](CHANGELOG.md).

Colour output is emitted only to a TTY and honours the
[`NO_COLOR`](https://no-color.org/) convention.

## License

Internal Use Only – Platform Engineering / Network Automation

---

*check_multi 2.0.0-alpha*
