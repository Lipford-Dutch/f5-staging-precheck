# check_multi 2.0 Alpha – Quick Start

## 1. Prerequisites
- bash 4.2+
- ssh
- python3 + openpyxl (only if using --excel)
- yq (optional but recommended for YAML config)

## 2. First Run (safe)
```bash
./bin/check_multi --dry-run platform examples/devices.txt
```

## 3. Real Run
```bash
./bin/check_multi -e lab -t 10 platform examples/devices.txt
```

## 4. Executive Excel Report
```bash
./bin/check_multi -e prod --excel -t 15 certs inventory/prod.txt
```

The Excel file appears in the results directory and is suitable for emailing to leadership.

## 5. Available Checks
platform | umm | certs | keys | syncgroup | network | preflight

## 6. Useful Options
| Flag | Purpose |
|------|---------|
| `--dry-run` | Preview without SSH |
| `-t 15` | 15 parallel sessions |
| `-e prod` | Use production profile |
| `--excel` | Generate VP-ready Excel report |
| `-v` | Verbose / debug logging |
