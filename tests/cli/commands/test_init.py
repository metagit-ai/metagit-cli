#!/usr/bin/env python
"""
CLI tests for metagit init command.
"""

import subprocess
from pathlib import Path

import yaml
from click.testing import CliRunner

from metagit.cli.commands.init import _resolve_project_metadata, resolve_target_dir
from metagit.cli.main import cli


def test_resolve_project_metadata_non_git_directory(tmp_path: Path) -> None:
  project_dir = tmp_path / "my-project"
  project_dir.mkdir()
  name, url = _resolve_project_metadata(project_dir)
  assert name == "my-project"
  assert url is None


def test_resolve_project_metadata_git_repo_without_remote(tmp_path: Path) -> None:
  project_dir = tmp_path / "local-repo"
  project_dir.mkdir()
  subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
  name, url = _resolve_project_metadata(project_dir)
  assert name == "local-repo"
  assert url is None


def test_init_succeeds_outside_git_repository() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem():
    result = runner.invoke(
      cli,
      ["init", "--kind", "application", "--skip-gitignore", "--no-prompt"],
    )
    assert result.exit_code == 0, result.output
    config_path = Path(".metagit.yml")
    assert config_path.is_file()
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert loaded["name"] == Path.cwd().name
    assert loaded["kind"] == "application"


def test_init_list_templates() -> None:
  runner = CliRunner()
  result = runner.invoke(cli, ["init", "--list-templates"])
  assert result.exit_code == 0, result.output
  assert "hermes-orchestrator" in result.output
  assert "application" in result.output


def test_init_hermes_template_no_prompt() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem():
    answers = {
      "name": "hermes-test",
      "description": "Test workspace",
      "url": "",
      "portfolio_repo_name": "api",
      "portfolio_repo_url": "https://github.com/example/api.git",
      "local_site_name": "site",
      "local_site_path": "~/Sites/site",
    }
    answers_path = Path("answers.yml")
    answers_path.write_text(yaml.safe_dump(answers), encoding="utf-8")
    result = runner.invoke(
      cli,
      [
        "init",
        "--template",
        "hermes-orchestrator",
        "--answers-file",
        str(answers_path),
        "--no-prompt",
        "--skip-gitignore",
      ],
    )
    assert result.exit_code == 0, result.output
    loaded = yaml.safe_load(Path(".metagit.yml").read_text(encoding="utf-8"))
    assert loaded["name"] == "hermes-test"
    assert Path("AGENTS.md").is_file()


def test_resolve_target_dir_create(tmp_path: Path) -> None:
  target = tmp_path / "new-coordinator"
  resolved = resolve_target_dir(str(target), create=True)
  assert resolved == target.resolve()
  assert target.is_dir()


def test_init_writes_to_target_folder() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem():
    target = Path("coordinator")
    target.mkdir()
    result = runner.invoke(
      cli,
      [
        "init",
        str(target),
        "--kind",
        "application",
        "--no-prompt",
        "--skip-gitignore",
      ],
    )
    assert result.exit_code == 0, result.output
    assert (target / ".metagit.yml").is_file()
    assert not Path(".metagit.yml").exists()


def test_init_target_option_overrides_positional(tmp_path: Path) -> None:
  runner = CliRunner()
  chosen = tmp_path / "chosen"
  ignored = tmp_path / "ignored"
  chosen.mkdir()
  ignored.mkdir()
  result = runner.invoke(
    cli,
    [
      "init",
      str(ignored),
      "--target",
      str(chosen),
      "--minimal",
      "--kind",
      "application",
      "--no-prompt",
      "--skip-gitignore",
    ],
  )
  assert result.exit_code == 0, result.output
  assert (chosen / ".metagit.yml").is_file()
  assert not (ignored / ".metagit.yml").exists()


def test_init_minimal_service_kind() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem():
    result = runner.invoke(
      cli,
      [
        "init",
        "--kind",
        "service",
        "--minimal",
        "--no-prompt",
        "--description",
        "A microservice",
        "--skip-gitignore",
      ],
    )
    assert result.exit_code == 0, result.output
    loaded = yaml.safe_load(Path(".metagit.yml").read_text(encoding="utf-8"))
    assert loaded["kind"] == "service"


def test_init_idempotent_when_manifest_valid() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem():
    first = runner.invoke(
      cli,
      ["init", "--kind", "application", "--skip-gitignore", "--no-prompt"],
    )
    assert first.exit_code == 0, first.output
    before = Path(".metagit.yml").read_text(encoding="utf-8")

    second = runner.invoke(
      cli,
      ["init", "--kind", "application", "--skip-gitignore", "--no-prompt"],
    )
    assert second.exit_code == 0, second.output
    assert "Already initialized" in second.output
    assert Path(".metagit.yml").read_text(encoding="utf-8") == before


def test_init_fails_when_manifest_invalid() -> None:
  runner = CliRunner()
  with runner.isolated_filesystem():
    Path(".metagit.yml").write_text("name: broken\nkind: not-a-kind\n", encoding="utf-8")
    result = runner.invoke(
      cli,
      ["init", "--kind", "application", "--skip-gitignore", "--no-prompt"],
    )
    assert result.exit_code != 0

