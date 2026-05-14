#!/usr/bin/env python
"""CLI tests for metagit project repo prune."""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def test_project_repo_prune_dry_run_lists_unmanaged(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".metagit"
    platform = workspace / "platform"
    platform.mkdir(parents=True)
    (platform / "managed").mkdir()
    (platform / "leftover").mkdir()

    metagit_yml = tmp_path / ".metagit.yml"
    metagit_yml.write_text(
        "\n".join(
            [
                "name: test",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: managed",
                "          url: https://example.com/managed.git",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    app_cfg = tmp_path / "metagit.config.yaml"
    app_cfg.write_text(
        "\n".join(
            [
                "config:",
                "  description: test",
                "  workspace:",
                "    path: " + str(workspace).replace("\\", "/"),
                "    default_project: platform",
                "    ui_ignore_hidden: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        [
            "--config",
            str(app_cfg),
            "project",
            "-c",
            str(metagit_yml),
            "--project",
            "platform",
            "repo",
            "prune",
            "--dry-run",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "leftover" in result.output
    assert "Prune context:" in result.output
    assert "workspace.path (sync root):" in result.output
    assert "project: platform" in result.output
    assert "project sync folder:" in result.output


def test_project_repo_prune_force_removes_without_prompt(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace = tmp_path / ".metagit"
    platform = workspace / "platform"
    platform.mkdir(parents=True)
    (platform / "managed").mkdir()
    leftover = platform / "leftover"
    leftover.mkdir()

    metagit_yml = tmp_path / ".metagit.yml"
    metagit_yml.write_text(
        "\n".join(
            [
                "name: test",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: managed",
                "          url: https://example.com/managed.git",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    app_cfg = tmp_path / "metagit.config.yaml"
    app_cfg.write_text(
        "\n".join(
            [
                "config:",
                "  description: test",
                "  workspace:",
                "    path: " + str(workspace).replace("\\", "/"),
                "    default_project: platform",
                "    ui_ignore_hidden: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        [
            "--config",
            str(app_cfg),
            "project",
            "-c",
            str(metagit_yml),
            "--project",
            "platform",
            "repo",
            "prune",
            "--force",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "--force" in result.output
    assert not leftover.exists()
    assert (platform / "managed").exists()
