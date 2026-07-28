"""Rich console rendering: per-device tables plus a GO/NO-GO dashboard.

Colour is applied by Rich only when writing to a TTY, and the ``NO_COLOR``
convention is honoured via ``Console(no_color=...)`` in the CLI.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..core.gate import Decision, RunVerdict
from ..core.models import Status

_STATUS_STYLE = {
    Status.PASS: "bold green",
    Status.WARN: "bold yellow",
    Status.FAIL: "bold red",
    Status.INFO: "cyan",
    Status.SKIP: "dim",
}


def _status_text(status: Status) -> Text:
    return Text(status.value, style=_STATUS_STYLE.get(status, ""))


def render(verdict: RunVerdict, console: Console | None = None) -> None:
    """Render the full verdict to the console."""
    console = console or Console()
    for device in verdict.devices:
        table = Table(
            title=f"{device.device}  —  {device.decision.value}",
            title_style="bold",
            expand=True,
        )
        table.add_column("Check", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Sev", justify="center")
        table.add_column("Summary")
        for r in device.results:
            table.add_row(
                r.check,
                _status_text(r.status),
                r.severity.value,
                r.summary + (f"  [dim]({r.reference})[/dim]" if r.reference else ""),
            )
        console.print(table)
    _render_dashboard(verdict, console)


def _render_dashboard(verdict: RunVerdict, console: Console) -> None:
    counts = verdict.counts
    summary = (
        f"PASS {counts['PASS']}  "
        f"WARN {counts['WARN']}  "
        f"FAIL {counts['FAIL']}  "
        f"INFO {counts['INFO']}  "
        f"SKIP {counts['SKIP']}"
    )
    if verdict.decision is Decision.GO:
        style, headline = "bold green", "GO"
    else:
        style, headline = "bold red", "NO-GO"
    blockers = [
        f"  • {d.device}: {r.check} — {r.summary}"
        for d in verdict.devices
        for r in d.blocking
    ]
    body = Text(summary, style="bold")
    if blockers:
        body.append("\n\nBlocking issues:\n" + "\n".join(blockers), style="red")
    console.print(Panel(body, title=f"UPGRADE READINESS: {headline}", border_style=style))


__all__ = ["render"]
