#!/usr/bin/env python
"""CLI tests for metagit version commands."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import patch

from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.release.models import (
    LatestReleaseInfo,
    VersionCheckResult,
    VersionUpgradeResult,
)


def _sample_result(*, update_available: bool = True) -> VersionCheckResult:
    return VersionCheckResult(
        installed_version="1.0.0",
        latest_release=LatestReleaseInfo(
            version="2.0.0",
            tag_name="v2.0.0",
            name="Metagit 2.0.0",
            published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            html_url="https://github.com/metagit-ai/metagit-cli/releases/tag/v2.0.0",
            body="## Notes\n- change",
            source="github",
        ),
        pypi_version="2.0.0",
        update_available=update_available,
        is_latest=not update_available,
    )


@patch("metagit.cli.commands.version_cmd.ReleaseCheckService")
def test_version_check_json(mock_service_cls: object) -> None:
    mock_service_cls.return_value.check.return_value = _sample_result()
    runner = CliRunner()
    result = runner.invoke(cli, ["version", "check", "--json"], catch_exceptions=False)

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["installed_version"] == "1.0.0"
    assert payload["latest_release"]["version"] == "2.0.0"
    assert payload["update_available"] is True
    assert payload["latest_release"]["body"] == "## Notes\n- change"


@patch("metagit.cli.commands.version_cmd.ReleaseCheckService")
def test_version_check_human_output(mock_service_cls: object) -> None:
    mock_service_cls.return_value.check.return_value = _sample_result()
    runner = CliRunner()
    result = runner.invoke(cli, ["version", "check"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "installed: 1.0.0" in result.output
    assert "latest:    2.0.0" in result.output
    assert "update available: yes" in result.output
    assert "release notes:" in result.output


@patch("metagit.cli.commands.version_cmd.ReleaseCheckService")
def test_version_check_no_notes(mock_service_cls: object) -> None:
    mock_service_cls.return_value.check.return_value = _sample_result()
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["version", "check", "--json", "--no-notes"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    mock_service_cls.return_value.check.assert_called_once_with(include_notes=False)


@patch("metagit.cli.commands.version_cmd.ReleaseCheckService")
def test_version_default_shows_installed(mock_service_cls: object) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["version"], catch_exceptions=False)

    assert result.exit_code == 0
    mock_service_cls.assert_not_called()


def _sample_upgrade_result(*, dry_run: bool = True) -> VersionUpgradeResult:
    return VersionUpgradeResult(
        ok=True,
        dry_run=dry_run,
        applied=not dry_run,
        install_method="uv_tool",
        command="uv tool upgrade metagit-cli",
        check=_sample_result(),
        message="Update available. Re-run with --apply to execute: uv tool upgrade metagit-cli",
    )


@patch("metagit.cli.commands.version_cmd.VersionUpgradeService")
def test_version_upgrade_json_dry_run(mock_service_cls: object) -> None:
    mock_service_cls.return_value.upgrade.return_value = _sample_upgrade_result()
    runner = CliRunner()
    result = runner.invoke(
        cli, ["version", "upgrade", "--json"], catch_exceptions=False
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["dry_run"] is True
    assert payload["command"] == "uv tool upgrade metagit-cli"
    mock_service_cls.return_value.upgrade.assert_called_once_with(apply=False)


@patch("metagit.cli.commands.version_cmd.VersionUpgradeService")
def test_version_upgrade_apply_exits_on_failure(mock_service_cls: object) -> None:
    mock_service_cls.return_value.upgrade.return_value = VersionUpgradeResult(
        ok=False,
        dry_run=False,
        applied=True,
        install_method="uv_tool",
        command="uv tool upgrade metagit-cli",
        check=_sample_result(),
        error="upgrade_failed",
        message="Upgrade command failed.",
        stderr="network error",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["version", "upgrade", "--apply"], catch_exceptions=False
    )

    assert result.exit_code == 1
    assert "Upgrade command failed." in result.output
