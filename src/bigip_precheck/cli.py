"""Typer CLI for bigip-precheck.

Commands:
    run              Run checks against an inventory and emit a GO/NO-GO verdict.
    list-checks      List available checks (optionally filtered by a profile).
    validate-config  Validate an inventory file without contacting any device.
    version          Print the tool version.

Safety: the tool is read-only in this release. ``run`` always operates in
check-only mode; there is no flag that mutates a device.

Exit codes:
    0  GO           — every device is clear to proceed.
    2  NO-GO        — at least one device has a blocking result.
    3  CONFIG       — the run could not start (bad config / unknown check).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from rich.console import Console

from . import __version__
from .checkers import build_default_registry
from .config.loader import load_inventory
from .config.models import Inventory
from .core.exceptions import ConfigError, PrecheckError
from .core.gate import Decision, Gate
from .core.orchestrator import Orchestrator
from .logging.audit import AuditLog
from .logging.integrity import write_digest
from .reporting import build_report, render, write_report

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Read-only F5 BIG-IP pre-upgrade / change-window readiness validator.",
)

EXIT_GO = 0
EXIT_NO_GO = 2
EXIT_CONFIG = 3


def _console(no_color: bool) -> Console:
    return Console(no_color=no_color or bool(os.environ.get("NO_COLOR")))


def _resolve_checks(inv: Inventory, profile: str | None, checks: list[str] | None) -> list[str] | None:
    """Turn a profile name and/or explicit checks into a concrete check list."""
    if checks:
        return checks
    if profile:
        prof = inv.profiles.get(profile)
        if prof is None:
            raise ConfigError(
                f"unknown profile '{profile}'. Known: {', '.join(sorted(inv.profiles)) or '(none)'}"
            )
        return prof.checks or None
    return None


@app.command()
def run(
    inventory: Path = typer.Argument(..., help="Path to the inventory YAML file."),
    profile: str | None = typer.Option(None, "--profile", "-P", help="Named profile to run."),
    check: list[str] = typer.Option(  # noqa: B008 - Typer option factory
        None, "--check", "-k", help="Explicit check name(s); repeatable. Overrides --profile."
    ),
    output_dir: Path | None = typer.Option(None, "--output-dir", "-o", help="Report/audit directory."),
    ci: bool = typer.Option(False, "--ci", help="Non-interactive; machine output; exit non-zero on NO-GO."),
    strict: bool = typer.Option(False, "--strict", help="Treat HIGH+ WARN results as blocking."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable coloured output."),
    json_only: bool = typer.Option(False, "--json", help="Print the JSON report to stdout; suppress tables."),
) -> None:
    """Run readiness checks and produce a GO/NO-GO verdict."""
    console = _console(no_color)
    try:
        inv = load_inventory(inventory)
        if not inv.devices:
            raise ConfigError("inventory contains no devices")
        registry = build_default_registry()
        wanted = _resolve_checks(inv, profile, check or None)
        selected = registry.select(wanted)
        out_dir = str(output_dir or inv.settings.output_dir)

        audit = AuditLog(out_dir)
        audit.event(
            "run_config",
            inventory=str(inventory),
            profile=profile or "(all)",
            checks=[c.name for c in selected],
            devices=[d.name for d in inv.devices],
            allow_prompt=not ci,
        )

        orch = Orchestrator(
            inv,
            selected,
            allow_prompt=not ci,
            on_event=lambda kind, fields: audit.event(kind, **fields),
        )
        results = orch.run(audit.session_id)

        gate = Gate(warn_is_blocking=strict)
        verdict = gate.evaluate(results)
        audit.close(decision=verdict.decision.value)

        report = build_report(
            verdict,
            session_id=audit.session_id,
            profile=profile or "(all)",
            inventory_path=str(inventory),
        )
        report_path = write_report(report, Path(out_dir) / f"report-{audit.session_id}.json")
        write_digest(report_path)

        if json_only:
            typer.echo(Path(report_path).read_text(encoding="utf-8"))
        else:
            render(verdict, console)
            console.print(f"[dim]Report: {report_path}  •  Audit: {audit.jsonl_path}[/dim]")

        raise typer.Exit(EXIT_GO if verdict.decision is Decision.GO else EXIT_NO_GO)
    except ConfigError as exc:
        console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(EXIT_CONFIG) from exc
    except PrecheckError as exc:  # pragma: no cover - safety net
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(EXIT_CONFIG) from exc


@app.command("list-checks")
def list_checks(
    profile: str | None = typer.Option(None, "--profile", "-P", help="Filter to a profile."),
    inventory: Path | None = typer.Option(None, "--inventory", "-i", help="Inventory for profiles."),
    no_color: bool = typer.Option(False, "--no-color"),
) -> None:
    """List available checks and their metadata."""
    console = _console(no_color)
    registry = build_default_registry()
    wanted: list[str] | None = None
    if profile:
        if inventory is None:
            console.print("[red]--profile requires --inventory[/red]")
            raise typer.Exit(EXIT_CONFIG)
        inv = load_inventory(inventory)
        prof = inv.profiles.get(profile)
        if prof is None:
            console.print(f"[red]unknown profile '{profile}'[/red]")
            raise typer.Exit(EXIT_CONFIG)
        wanted = prof.checks or None

    from rich.table import Table

    table = Table(title="Available checks")
    table.add_column("Name", no_wrap=True)
    table.add_column("Sev")
    table.add_column("Applies to")
    table.add_column("Description")
    for c in registry.select(wanted):
        applies = ", ".join(sorted(r.value for r in c.applies_to))
        table.add_row(c.name, c.severity.value, applies, c.description)
    console.print(table)


@app.command("validate-config")
def validate_config(
    inventory: Path = typer.Argument(..., help="Inventory YAML to validate."),
    no_color: bool = typer.Option(False, "--no-color"),
) -> None:
    """Validate an inventory file offline (no device contact)."""
    console = _console(no_color)
    try:
        inv = load_inventory(inventory)
    except ConfigError as exc:
        console.print(f"[bold red]Invalid:[/bold red] {exc}")
        raise typer.Exit(EXIT_CONFIG) from exc
    registry = build_default_registry()
    # Surface unknown checks referenced by any profile up front.
    for name, prof in inv.profiles.items():
        try:
            registry.select(prof.checks or None)
        except ConfigError as exc:
            console.print(f"[bold red]Profile '{name}' invalid:[/bold red] {exc}")
            raise typer.Exit(EXIT_CONFIG) from exc
    console.print(
        f"[bold green]OK[/bold green] — {len(inv.devices)} device(s), "
        f"{len(inv.profiles)} profile(s)."
    )


@app.command()
def version() -> None:
    """Print the tool version."""
    typer.echo(__version__)


def main() -> None:  # pragma: no cover - console-script entry
    app()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
