#!/usr/bin/env python
"""CLI tests for project repo select --repo."""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _write_fixture(tmp_path: Path) -> tuple[Path, Path]:
  workspace = tmp_path / ".metagit"
  platform = workspace / "platform"
  repo_dir = platform / "backend"
  repo_dir.mkdir(parents=True)
  (repo_dir / "README.md").write_text("hello", encoding="utf-8")

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
        "        - name: backend",
        "          url: https://example.com/backend.git",
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
        "  editor: echo",
        "  workspace:",
        f"    path: {workspace.as_posix()}",
        "    default_project: platform",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  return app_cfg, metagit_yml


def test_project_select_repo_skips_picker_and_opens_editor(tmp_path: Path, monkeypatch) -> None:
  app_cfg, metagit_yml = _write_fixture(tmp_path)
  opened: list[str] = []

  def _fake_open_editor(editor: str, path: str):
    opened.append(path)
    return None

  monkeypatch.setattr("metagit.cli.commands.project_repo.open_editor", _fake_open_editor)

  def _fail_finder(*_args, **_kwargs):
    raise AssertionError("FuzzyFinder should not run when --repo is provided")

  monkeypatch.setattr("metagit.core.project.manager.FuzzyFinder", _fail_finder)

  runner = CliRunner()
  result = runner.invoke(
    cli,
    [
      "--config",
      str(app_cfg),
      "project",
      "-c",
      str(metagit_yml),
      "-p",
      "platform",
      "select",
      "--repo",
      "backend",
    ],
    catch_exceptions=False,
  )

  assert result.exit_code == 0
  assert len(opened) == 1
  assert opened[0].endswith("/platform/backend")


def test_project_select_repo_unknown_repo_exits_nonzero(tmp_path: Path) -> None:
  app_cfg, metagit_yml = _write_fixture(tmp_path)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    [
      "--config",
      str(app_cfg),
      "project",
      "-c",
      str(metagit_yml),
      "-p",
      "platform",
      "select",
      "--repo",
      "missing",
    ],
  )
  assert result.exit_code != 0
  assert "missing" in result.output
