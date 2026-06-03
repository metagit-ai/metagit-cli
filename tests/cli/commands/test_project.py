#!/usr/bin/env python
"""CLI tests for metagit project commands."""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _write_manifest(path: Path, *, projects_yaml: str) -> None:
    path.write_text(
        "\n".join(
            [
                "name: test",
                "kind: application",
                "workspace:",
                "  projects:",
                projects_yaml,
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_app_config(path: Path, workspace_path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "config:",
                "  description: test",
                "  workspace:",
                f"    path: {workspace_path.as_posix()}",
                "    default_project: default",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_project_list_catalog_when_default_missing(tmp_path: Path) -> None:
    runner = CliRunner()
    metagit_yml = tmp_path / ".metagit.yml"
    _write_manifest(
        metagit_yml,
        projects_yaml="\n".join(
            [
                "    - name: remote",
                "      repos:",
                "        - name: test",
                "          path: ./web",
            ]
        ),
    )
    app_cfg = tmp_path / "metagit.config.yaml"
    _write_app_config(app_cfg, tmp_path / ".metagit")

    result = runner.invoke(
        cli,
        ["--config", str(app_cfg), "project", "-c", str(metagit_yml), "list"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "name: remote" in result.output


def test_project_list_catalog_when_multiple_without_default(tmp_path: Path) -> None:
    runner = CliRunner()
    metagit_yml = tmp_path / ".metagit.yml"
    _write_manifest(
        metagit_yml,
        projects_yaml="\n".join(
            [
                "    - name: alpha",
                "      repos: []",
                "    - name: beta",
                "      repos: []",
            ]
        ),
    )
    app_cfg = tmp_path / "metagit.config.yaml"
    _write_app_config(app_cfg, tmp_path / ".metagit")

    result = runner.invoke(
        cli,
        ["--config", str(app_cfg), "project", "-c", str(metagit_yml), "list"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "alpha (0 repos)" in result.output
    assert "beta (0 repos)" in result.output


def test_project_list_empty_workspace(tmp_path: Path) -> None:
    runner = CliRunner()
    metagit_yml = tmp_path / ".metagit.yml"
    metagit_yml.write_text(
        "\n".join(["name: test", "kind: application", "workspace:", "  projects: []"])
        + "\n",
        encoding="utf-8",
    )
    app_cfg = tmp_path / "metagit.config.yaml"
    _write_app_config(app_cfg, tmp_path / ".metagit")

    result = runner.invoke(
        cli,
        ["--config", str(app_cfg), "project", "-c", str(metagit_yml), "list"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_project_select_missing_default_uses_single_project(
    tmp_path: Path, monkeypatch
) -> None:
    finder_calls: list[object] = []

    class _DummyFinder:
        def __init__(self, config) -> None:
            finder_calls.append(config)

        def run(self):
            return None

    monkeypatch.setattr(
        "metagit.core.project.manager.FuzzyFinder",
        _DummyFinder,
    )

    runner = CliRunner()
    workspace = tmp_path / ".metagit"
    project_dir = workspace / "remote"
    project_dir.mkdir(parents=True)
    (project_dir / "test").mkdir()

    metagit_yml = tmp_path / ".metagit.yml"
    _write_manifest(
        metagit_yml,
        projects_yaml="\n".join(
            [
                "    - name: remote",
                "      repos:",
                "        - name: test",
                "          path: ./web",
            ]
        ),
    )
    app_cfg = tmp_path / "metagit.config.yaml"
    _write_app_config(app_cfg, workspace)

    result = runner.invoke(
        cli,
        ["--config", str(app_cfg), "project", "-c", str(metagit_yml), "select"],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    assert "IndexError" not in result.output
    assert "Traceback" not in result.output
    assert "Project 'default' not found" not in result.output
    assert len(finder_calls) == 1
