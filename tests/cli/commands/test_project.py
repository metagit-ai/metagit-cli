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


def _write_app_config(
  path: Path,
  workspace_path: Path,
  *,
  default_project: str = "default",
) -> None:
  path.write_text(
    "\n".join(
      [
        "config:",
        "  description: test",
        "  workspace:",
        f"    path: {workspace_path.as_posix()}",
        f"    default_project: {default_project}",
      ]
    )
    + "\n",
    encoding="utf-8",
  )


def test_project_list_defaults_to_workspace_style_catalog(tmp_path: Path) -> None:
  runner = CliRunner()
  metagit_yml = tmp_path / ".metagit.yml"
  _write_manifest(
    metagit_yml,
    projects_yaml="\n".join(
      [
        "    - name: platform",
        "      repos:",
        "        - name: backend",
        "          path: ./backend",
        "    - name: data",
        "      repos:",
        "        - name: warehouse",
        "          path: ./warehouse",
      ]
    ),
  )
  app_cfg = tmp_path / "metagit.config.yaml"
  _write_app_config(app_cfg, tmp_path / ".metagit", default_project="platform")

  result = runner.invoke(
    cli,
    ["--config", str(app_cfg), "project", "-c", str(metagit_yml), "list"],
    catch_exceptions=False,
  )

  assert result.exit_code == 0
  assert "Definition:" in result.output
  assert "Projects: 2 | Repos: 2" in result.output
  assert "  - platform (1 repos)" in result.output
  assert "  - data (1 repos)" in result.output
  assert "name: platform" not in result.output


def test_project_list_json_matches_workspace_catalog_shape(tmp_path: Path) -> None:
  runner = CliRunner()
  metagit_yml = tmp_path / ".metagit.yml"
  _write_manifest(
    metagit_yml,
    projects_yaml="\n".join(
      [
        "    - name: alpha",
        "      repos: []",
      ]
    ),
  )
  app_cfg = tmp_path / "metagit.config.yaml"
  _write_app_config(app_cfg, tmp_path / ".metagit", default_project="alpha")

  result = runner.invoke(
    cli,
    ["--config", str(app_cfg), "project", "-c", str(metagit_yml), "list", "--json"],
    catch_exceptions=False,
  )

  assert result.exit_code == 0
  assert '"summary"' in result.output
  assert '"projects"' in result.output
  assert '"name": "alpha"' in result.output


def test_project_list_detail_with_explicit_project(tmp_path: Path) -> None:
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
  _write_app_config(app_cfg, tmp_path / ".metagit", default_project="remote")

  result = runner.invoke(
    cli,
    ["--config", str(app_cfg), "project", "-c", str(metagit_yml), "-p", "remote", "list"],
    catch_exceptions=False,
  )

  assert result.exit_code == 0
  assert "name: remote" in result.output
  assert "Projects:" not in result.output


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
  assert "Projects: 0 | Repos: 0" in result.output


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

  # Finder ran against the sole resolved project; cancel/None selection is non-crash.
  assert result.exit_code == 1
  assert "IndexError" not in result.output
  assert "Traceback" not in result.output
  assert "Project 'default' not found" not in result.output
  assert len(finder_calls) == 1
