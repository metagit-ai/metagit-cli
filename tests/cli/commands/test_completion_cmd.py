#!/usr/bin/env python
"""CLI tests for metagit completion commands."""

from click.testing import CliRunner

from metagit.cli.main import cli


def test_completion_show_zsh() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "show", "--shell", "zsh"])
    assert result.exit_code == 0, result.output
    assert "#compdef metagit" in result.output


def test_completion_install_stdout_hint() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["completion", "install", "--shell", "zsh", "--stdout"],
    )
    assert result.exit_code == 0, result.output
    assert "_METAGIT_COMPLETE=zsh_source" in result.output


def test_completion_doctor() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "doctor"])
    assert result.exit_code == 0, result.output
    assert "OK" in result.output
