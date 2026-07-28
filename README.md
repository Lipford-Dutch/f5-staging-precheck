# check_multi 2.0

**Enterprise Device Audit Framework**  
Multi-function, parallel SSH-based audit tool for network appliances (primarily F5 BIG-IP).

[![Version](https://img.shields.io/badge/Version-2.0.0--alpha-orange)]()
[![ShellCheck](https://img.shields.io/badge/ShellCheck-ready-brightgreen)]()
[![License](https://img.shields.io/badge/License-Internal-blue)]()

---

## Overview

`check_multi` is a modular, secure, and governance-ready framework for running configuration, health, and compliance checks against large inventories of network devices.

It was completely redesigned from a legacy monolithic Bash script into a clean, extensible architecture following industry best practices.

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
| GitHub Actions CI skeleton     | ✅     |

---

## Quick Start

```bash
# Clone or extract the repository
cd check_multi_2.0

# Make the entry point executable
chmod +x bin/check_multi

# View help
./bin/check_multi --help

# Safe dry-run against example inventory
./bin/check_multi --dry-run platform examples/devices.txt

# Real run with Excel report
./bin/check_multi -e lab -t 10 --excel platform examples/devices.txt
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [INSTALL.md](docs/INSTALL.md) | Detailed installation instructions |
| [QUICKSTART.md](docs/QUICKSTART.md) | First-run guide |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Technical design |
| [SECURITY.md](docs/SECURITY.md) | Security model and recommendations |

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
│   └── checks/                  # Plugin check modules
│       ├── platform.sh
│       ├── umm.sh
│       ├── certs.sh
│       ├── keys.sh
│       ├── syncgroup.sh
│       ├── network.sh
│       └── preflight.sh
├── config/
│   ├── defaults.yaml
│   └── environments/
│       ├── lab.yaml
│       └── prod.yaml
├── scripts/
│   ├── generate_excel_report.py
│   └── shellcheck_all.sh
├── docs/
├── examples/
├── tests/
└── .github/workflows/ci.yml
```

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
| `--excel`                 | Generate executive Excel report          |
| `--version`               | Print version                            |

### Available Checks

- `platform`   – Version, build, modules, serial, telemetry
- `umm`        – Provisioned modules
- `certs`      – Certificate inventory
- `keys`       – Key inventory
- `syncgroup`  – CM sync status
- `network`    – Interfaces & trunks
- `preflight`  – Lightweight connectivity + version check

---

## Security Model

1. **Prefer SSH keys** – password mode (`-p`) prints a large warning.
2. Temporary files are created with mode `0600` and removed on exit.
3. Output directories use `0750`.
4. Host key checking is controlled via environment profile.
5. Full audit trail of every run.

---

## License

Internal Use Only – Platform Engineering / Network Automation

---

*check_multi 2.0.0-alpha*
