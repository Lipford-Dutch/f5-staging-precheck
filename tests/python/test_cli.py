"""CLI contract tests: commands, exit codes, and report artefacts.

The ``run`` command is exercised end-to-end with the REST client monkeypatched
to a fake, so no device is contacted but the full wiring (orchestrator → gate →
report → digest → exit code) is proven.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from bigip_precheck import __version__
from bigip_precheck.cli import EXIT_CONFIG, EXIT_GO, EXIT_NO_GO, app

from .conftest import FakeRestClient
from .fixtures import icontrol as fx

runner = CliRunner()
EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "bigip-precheck" / "inventory.yaml"


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_list_checks():
    result = runner.invoke(app, ["list-checks", "--no-color"])
    assert result.exit_code == 0
    assert "system.version" in result.stdout
    assert "ha.sync-status" in result.stdout


def test_validate_config_ok():
    result = runner.invoke(app, ["validate-config", str(EXAMPLE), "--no-color"])
    assert result.exit_code == EXIT_GO
    assert "OK" in result.stdout


def test_validate_config_bad(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("settings:\n  max_workers: -1\n", encoding="utf-8")
    result = runner.invoke(app, ["validate-config", str(bad), "--no-color"])
    assert result.exit_code == EXIT_CONFIG


def test_run_missing_inventory():
    result = runner.invoke(app, ["run", "/no/such.yaml", "--no-color"])
    assert result.exit_code == EXIT_CONFIG


def _patch_client(monkeypatch, responses):
    def fake_ctor(device, cred, settings, **kwargs):
        return FakeRestClient(device, responses)

    monkeypatch.setattr("bigip_precheck.clients.rest.IControlRestClient", fake_ctor)
    monkeypatch.setenv("BIGIP_DEFAULT_TOKEN", "tok")


def test_run_go(monkeypatch, tmp_path: Path):
    _patch_client(monkeypatch, fx.HEALTHY_HA_STANDBY)
    result = runner.invoke(
        app,
        [
            "run", str(EXAMPLE),
            "--profile", "full",
            "--output-dir", str(tmp_path),
            "--ci", "--no-color",
        ],
    )
    assert result.exit_code == EXIT_GO, result.stdout
    reports = list(tmp_path.glob("report-*.json"))
    assert reports and reports[0].with_suffix(".json.sha256").exists()


def test_run_no_go(monkeypatch, tmp_path: Path):
    _patch_client(monkeypatch, fx.UNHEALTHY)
    result = runner.invoke(
        app,
        [
            "run", str(EXAMPLE),
            "--profile", "full",
            "--output-dir", str(tmp_path),
            "--ci", "--no-color",
        ],
    )
    assert result.exit_code == EXIT_NO_GO, result.stdout


def test_run_json_output(monkeypatch, tmp_path: Path):
    _patch_client(monkeypatch, fx.HEALTHY_HA_STANDBY)
    result = runner.invoke(
        app,
        [
            "run", str(EXAMPLE),
            "--profile", "quick",
            "--output-dir", str(tmp_path),
            "--ci", "--json", "--no-color",
        ],
    )
    assert result.exit_code == EXIT_GO, result.stdout
    assert '"decision": "GO"' in result.stdout
    assert '"schema_version"' in result.stdout
