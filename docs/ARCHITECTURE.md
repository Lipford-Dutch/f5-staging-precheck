# Architecture – check_multi 2.0

## Design Goals
- Modular, testable, and extensible
- Secure by default (keys preferred, temp files locked down)
- Clear separation of execution vs reporting
- Governance-ready (audit trail, environment profiles)
- Operator-friendly CLI with dry-run and Excel output

## High-Level Flow

```
CLI (bin/check_multi)
    │
    ├─ load config + environment profile
    ├─ load check plugin
    ├─ validate inventory
    ├─ start audit run
    │
    ├─ parallel execution (lib/parallel.sh)
    │     └─ ssh_exec (lib/ssh.sh) → run_check()
    │
    ├─ generate summary.json (lib/summary.sh)
    ├─ optional Excel report (scripts/generate_excel_report.py)
    └─ end audit run
```

## Key Modules

| Module | Responsibility |
|--------|----------------|
| `lib/common.sh` | Logging, colours, temp files, JSON escape |
| `lib/ssh.sh` | SSH with retries, timeouts, dry-run, password warning |
| `lib/inventory.sh` | Load + validate device lists |
| `lib/parallel.sh` | Controlled concurrency |
| `lib/config.sh` | YAML defaults + environment overlays |
| `lib/audit.sh` | Immutable run records |
| `lib/summary.sh` | Structured summary.json for reporters |
| `lib/checks/*.sh` | Plugin check implementations |

## Plugin Contract
Every check module must define:

```bash
run_check() {
  local device=$1
  # perform work, return 0 on success, non-zero on failure
}
```

## Output Layout

```
results/YYYYMMDD_HHMMSS_<check>/
├── audit/
│   └── run_*.json
├── summary.json
└── Device_Audit_Report_*.xlsx   # when --excel used
```

## Extension Points
- Add new checks by dropping a file in `lib/checks/`
- Override behaviour via `config/environments/*.yaml`
- Replace the Excel reporter or add additional reporters that consume `summary.json`
