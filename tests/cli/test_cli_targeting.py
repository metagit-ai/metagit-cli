#!/usr/bin/env python
"""Root -p/-c targeting and agent-style flag placement."""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _write_umbrella(tmp_path: Path) -> tuple[Path, Path]:
  workspace = tmp_path / ".metagit"
  for project, repo in (("platform", "backend"), ("edge", "gateway")):
    repo_dir = workspace / project / repo
    repo_dir.mkdir(parents=True)
    (repo_dir / "README.md").write_text("hello", encoding="utf-8")

  metagit_yml = tmp_path / ".metagit.yml"
  metagit_yml.write_text(
    "\n".join(
      [
        "name: test",
        "kind: umbrella",
        "workspace:",
        "  projects:",
        "    - name: platform",
        "      repos:",
        "        - name: backend",
        "          url: https://example.com/backend.git",
        "    - name: edge",
        "      repos:",
        "        - name: gateway",
        "          url: https://example.com/gateway.git",
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
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  return app_cfg, metagit_yml


def test_root_c_manifest_is_used_by_project_list(tmp_path: Path, monkeypatch) -> None:
  _, metagit_yml = _write_umbrella(tmp_path)
  other = tmp_path / "othercwd"
  other.mkdir()
  monkeypatch.chdir(other)
  runner = CliRunner()
  result = runner.invoke(cli, ["-c", str(metagit_yml), "project", "list"], catch_exceptions=False)
  assert result.exit_code == 0, result.output
  assert "platform" in result.output
  assert "edge" in result.output


def test_root_p_keeps_project_list_as_catalog(tmp_path: Path) -> None:
  app_cfg, metagit_yml = _write_umbrella(tmp_path)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    ["-c", str(app_cfg), "-p", "platform", "project", "-c", str(metagit_yml), "list"],
    catch_exceptions=False,
  )
  assert result.exit_code == 0, result.output
  assert "Projects:" in result.output
  assert "name: platform" not in result.output


def test_project_list_trailing_p_dumps_detail(tmp_path: Path) -> None:
  app_cfg, metagit_yml = _write_umbrella(tmp_path)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    ["-c", str(app_cfg), "project", "-c", str(metagit_yml), "list", "-p", "platform"],
    catch_exceptions=False,
  )
  assert result.exit_code == 0, result.output
  assert "name: platform" in result.output
  assert "Projects:" not in result.output


def test_project_list_trailing_c_loads_manifest(tmp_path: Path, monkeypatch) -> None:
  app_cfg, metagit_yml = _write_umbrella(tmp_path)
  other = tmp_path / "othercwd"
  other.mkdir()
  (other / ".metagit.yml").write_text(
    "name: decoy\nkind: umbrella\nworkspace:\n  projects:\n    - name: decoy\n      repos: []\n",
    encoding="utf-8",
  )
  monkeypatch.chdir(other)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    ["-c", str(app_cfg), "project", "list", "-c", str(metagit_yml)],
    catch_exceptions=False,
  )
  assert result.exit_code == 0, result.output
  assert "platform" in result.output
  assert "decoy" not in result.output


def test_root_c_manifest_is_used_by_workspace_project_list(tmp_path: Path, monkeypatch) -> None:
  _, metagit_yml = _write_umbrella(tmp_path)
  other = tmp_path / "othercwd"
  other.mkdir()
  monkeypatch.chdir(other)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    ["-c", str(metagit_yml), "workspace", "project", "list"],
    catch_exceptions=False,
  )
  assert result.exit_code == 0, result.output
  assert "platform" in result.output
  assert "edge" in result.output


def test_workspace_project_list_trailing_c(tmp_path: Path, monkeypatch) -> None:
  _, metagit_yml = _write_umbrella(tmp_path)
  other = tmp_path / "othercwd"
  other.mkdir()
  (other / ".metagit.yml").write_text(
    "name: decoy\nkind: umbrella\nworkspace:\n  projects:\n    - name: decoy\n      repos: []\n",
    encoding="utf-8",
  )
  monkeypatch.chdir(other)
  runner = CliRunner()
  result = runner.invoke(
    cli,
    ["workspace", "project", "list", "-c", str(metagit_yml)],
    catch_exceptions=False,
  )
  assert result.exit_code == 0, result.output
  assert "platform" in result.output
  assert "decoy" not in result.output


def test_nav_inherits_root_project_and_repo(tmp_path: Path, monkeypatch) -> None:
  app_cfg, metagit_yml = _write_umbrella(tmp_path)
  opened: list[str] = []
  monkeypatch.setattr("metagit.cli.commands.nav.open_editor", lambda *_a, **_k: opened.append(_a[1]) or None)
  monkeypatch.setattr(
    "metagit.cli.commands.nav.select_project_name",
    lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("project picker should not run")),
  )
  runner = CliRunner()
  result = runner.invoke(
    cli,
    ["-c", str(app_cfg), "-p", "platform", "--repo", "backend", "nav", "-c", str(metagit_yml)],
    catch_exceptions=False,
  )
  assert result.exit_code == 0, result.output
  assert len(opened) == 1
  assert Path(opened[0]).resolve() == (tmp_path / ".metagit" / "platform" / "backend").resolve()


def test_search_accepts_c_and_inherits_root_manifest(tmp_path: Path, monkeypatch) -> None:
  _, metagit_yml = _write_umbrella(tmp_path)
  other = tmp_path / "othercwd"
  other.mkdir()
  monkeypatch.chdir(other)
  runner = CliRunner()
  inherited = runner.invoke(
    cli,
    ["-c", str(metagit_yml), "search", "backend", "--json"],
    catch_exceptions=False,
  )
  assert inherited.exit_code == 0, inherited.output
  assert "backend" in inherited.output

  trailing = runner.invoke(
    cli,
    ["search", "gateway", "-c", str(metagit_yml), "--json"],
    catch_exceptions=False,
  )
  assert trailing.exit_code == 0, trailing.output
  assert "gateway" in trailing.output
