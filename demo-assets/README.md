<div align="center">

<img src="branding/bofa-logo.png" alt="Bank of America" width="200"><br>
<sub><b>Bank of America</b> — Demo Asset Kit</sub>

</div>

---

# Demo Asset Kit — `f5-staging-precheck`

Everything needed to present or record a demo of both tools in this repo. All terminal output is **real**: the Python checks run against a local mock iControl REST server built from the project's own test fixtures, so you get authentic GO / NO-GO verdicts with no live BIG-IP.

## What's here

```
demo-assets/
├── CONTACT_SHEET.html        # open this first — every screenshot, captioned, grouped
├── RUN_OF_SHOW.md            # rehearsable 8–10 min talk track (scene → command → expected → screenshot)
├── README.md                 # this file (setup + reproduction)
├── branding/                 # Bank of America logo used in this kit's headers
├── png/                      # 18 feature screenshots (PNG, 1000–1560px wide — for slides)
├── svg/                      # same screenshots as SVG (scalable — for web/README embeds)
├── inventories/              # demo inventories (go / mixed / warn / invalid)
├── artifacts/                # canonical signed outputs: go_/nogo_ report.json + .sha256 + audit.jsonl
└── files/                    # raw run outputs + the executive Excel report (check_multi_report.xlsx)
```

## Screenshot index (18)

**Python `bigip-precheck`** — 07 version · 08 help · 09 list-checks · 10 list-checks --profile · 11a validate ok · 11b validate fail · 12 **run GO** · 13 **run NO-GO** · 14 run --strict · 15 run --json · 16 signed JSON report · 17 audit + integrity digest

**Bash `check_multi`** — 01 list-checks (11 modules) · 05 all-11 matrix · 02 dry-run platform · 03 did-you-mean · 04 input validation

**Excel** — 18 executive report (`.xlsx` in `files/check_multi_report.xlsx`)

> **Check count:** `check_multi` = 11 modules; `bigip-precheck` = 6 checkers = **17 total**. Scenes 01/05 and 09 show the exact lists.

## Reproduce it live (one-time setup)

Requires Python ≥ 3.11. From the repo root:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]' openpyxl

# 1) Start the mock iControl REST servers (healthy / degraded / warn) — keep running during the demo.
#    (The mock + cert used to build this kit are reproduced below.)
python demo-assets/mock/mock_tmos.py 18443 healthy  &
python demo-assets/mock/mock_tmos.py 18444 degraded &
python demo-assets/mock/mock_tmos.py 18445 warn     &

export BIGIP_DEFAULT_USERNAME=admin BIGIP_DEFAULT_PASSWORD=demo   # any value; mock accepts all

# 2) Run the scenes (see RUN_OF_SHOW.md for the full sequence)
python -m bigip_precheck.cli run demo-assets/inventories/lab-go.yaml    --ci   # -> GO   (exit 0)
python -m bigip_precheck.cli run demo-assets/inventories/lab-mixed.yaml --ci   # -> NO-GO(exit 2)
```

The Bash tool runs standalone (no mock needed) in dry-run:

```bash
./bin/check_multi --list-checks
./bin/check_multi --dry-run -e lab platform examples/devices.txt
```

Excel report:

```bash
./bin/check_multi --dry-run -e lab platform examples/devices.txt   # writes results/*/summary.json
python scripts/generate_excel_report.py results/*/summary.json report.xlsx
```

## How the screenshots were produced (for regenerating)

Terminal output was captured with color forced (`FORCE_COLOR=1` / a pseudo-tty for Bash), piped through a small helper that renders the ANSI faithfully into a terminal-window **SVG** (`rich` `Text.from_ansi` + `export_svg`), then rasterized to **PNG** via LibreOffice. This yields crisp, consistent, presentation-grade frames rather than OS screen-grabs.

## Notes & honesty

- The Python `run` output is **real**, driven by authentic fixture payloads over a genuine HTTPS iControl-REST exchange (token login, stats parsing) — just against a mock instead of a licensed device. Swap the inventory `host`/`port` to a real BIG-IP and the same commands work unchanged.
- The Bash checks are shown in **dry-run** (the CI-blessed, device-free path). Their per-device tmsh output requires a live BIG-IP; point `examples/devices.txt` at one and drop `--dry-run` to capture real sweeps.
- `files/` contains many `report-*/session-*` pairs — every run writes an immutable, hash-sealed record (a feature, not clutter). The **curated** canonical pair lives in `artifacts/` (`go_*`, `nogo_*`).
- A couple of LibreOffice lock/temp files (`.~lock…`, `*.tmp`) may linger in `png/`; they're harmless and safe to delete.
- Quality bar for the underlying code: see `../qa-report/PRODUCTION_READINESS.md` — 94% test coverage, ruff + mypy-strict + shellcheck clean, 3 bugs fixed.
