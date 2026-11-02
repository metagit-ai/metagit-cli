#!/usr/bin/env python
"""Every manifest-reading command accepts -c/--config and METAGIT_CONFIG."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli

MANIFEST = "name: demo\nkind: application\n"


def _commands(group: click.Group, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], click.Command]]:
    found: list[tuple[tuple[str, ...], click.Command]] = []
    seen: set[int] = set()
    for name, command in group.commands.items():
        path = prefix + (name,)
        if id(command) not in seen:
            seen.add(id(command))
            if _manifest_option(command) is not None:
                found.append((path, command))
        if isinstance(command, click.Group):
            found.extend(_commands(command, path))
    return found


def _manifest_option(command: click.Command) -> click.Option | None:
    for param in command.params:
        if isinstance(param, click.Option) and param.envvar == "METAGIT_CONFIG" and "--config" in param.opts:
            return param
    return None


COMMANDS = _commands(cli)


@pytest.mark.parametrize(("path", "command"), COMMANDS, ids=[" ".join(path) for path, _command in COMMANDS])
def test_manifest_command_accepts_config_flag_and_env(path: tuple[str, ...], command: click.Command, tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    option = _manifest_option(command)
    assert option is not None
    assert option.envvar == "METAGIT_CONFIG"
    assert "-c" in option.opts
    runner = CliRunner()
    flagged = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, *path, "-c", str(manifest), "--help"],
    )
    assert flagged.exit_code == 0, flagged.output
    assert "No such option" not in flagged.output
    from_env = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, *path, "--help"],
        env={"METAGIT_CONFIG": str(manifest)},
    )
    assert from_env.exit_code == 0, from_env.output


def test_validate_reads_metagit_config_env(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "validate"],
        env={"METAGIT_CONFIG": str(manifest)},
    )
    assert result.exit_code == 0, result.output


def test_deprecated_config_path_still_works(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "validate", "--config-path", str(manifest)],
    )
    assert result.exit_code == 0, result.output
    captured = capfd.readouterr()
    notice = captured.err + (getattr(result, "stderr", None) or "") + result.output
    assert "deprecated" in notice


def test_unknown_command_and_option_suggest_a_name() -> None:
    runner = CliRunner()
    command = runner.invoke(cli, ["--config", DEFAULT_CONFIG, "confg"])
    assert command.exit_code != 0
    assert "Did you mean" in command.output
    assert "config" in command.output
    option = runner.invoke(cli, ["--config", DEFAULT_CONFIG, "config", "validate", "--confg", "x"])
    assert option.exit_code != 0
    assert "Did you mean" in option.output
    assert "Traceback" not in option.output
