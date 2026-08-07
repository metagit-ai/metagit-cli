#!/usr/bin/env python
"""CLI tests for metagit nav / navigate."""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _write_multi_project_fixture(tmp_path: Path) -> tuple[Path, Path]:
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


def test_nav_project_and_repo_flags_open_editor(tmp_path: Path, monkeypatch) -> None:
    app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
    opened: list[str] = []

    def _fake_open(editor: str, path: str):
        opened.append(path)
        return None

    monkeypatch.setattr("metagit.cli.commands.nav.open_editor", _fake_open)
    monkeypatch.setattr(
        "metagit.cli.commands.nav.select_project_name",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("project picker should not run")),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            str(app_cfg),
            "nav",
            "-c",
            str(metagit_yml),
            "-p",
            "platform",
            "--repo",
            "backend",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert len(opened) == 1
    assert Path(opened[0]).resolve() == (tmp_path / ".metagit" / "platform" / "backend").resolve()


def test_navigate_alias_works(tmp_path: Path, monkeypatch) -> None:
    app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
    monkeypatch.setattr("metagit.cli.commands.nav.open_editor", lambda *_a, **_k: None)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            str(app_cfg),
            "navigate",
            "-c",
            str(metagit_yml),
            "-p",
            "edge",
            "--repo",
            "gateway",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


def test_nav_rejects_agent_mode(tmp_path: Path, monkeypatch) -> None:
    app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
    monkeypatch.setenv("METAGIT_AGENT_MODE", "true")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            str(app_cfg),
            "nav",
            "-c",
            str(metagit_yml),
            "-p",
            "platform",
            "--repo",
            "backend",
        ],
    )
    assert result.exit_code != 0
    combined = (result.output or "") + str(result.exception or "")
    assert "agent mode" in combined.lower()


def test_nav_unknown_project_exits_nonzero(tmp_path: Path) -> None:
    app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            str(app_cfg),
            "nav",
            "-c",
            str(metagit_yml),
            "-p",
            "missing",
            "--repo",
            "backend",
        ],
    )
    assert result.exit_code != 0


def test_nav_global_manifest_c_sets_definition_for_nav(tmp_path: Path, monkeypatch) -> None:
    app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
    opened: list[str] = []
    monkeypatch.setattr("metagit.cli.commands.nav.open_editor", lambda *_a, **_k: opened.append(_a[1]) or None)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", str(metagit_yml), "nav", "-p", "platform", "--repo", "backend"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert opened


def test_nav_expands_user_in_manifest_path(tmp_path: Path, monkeypatch) -> None:
    app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
    opened: list[str] = []
    monkeypatch.setattr("metagit.cli.commands.nav.open_editor", lambda _e, p: opened.append(p))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOMEDRIVE", tmp_path.drive or "")
    monkeypatch.setenv("HOMEPATH", str(tmp_path).removeprefix(tmp_path.drive) if tmp_path.drive else str(tmp_path))
    home_manifest = Path("~") / metagit_yml.name
    # Place manifest at $HOME/.metagit.yml so expanduser resolves it.
    home_copy = tmp_path / ".metagit.yml"
    home_copy.write_text(metagit_yml.read_text(encoding="utf-8"), encoding="utf-8")
    # Sync mounts still live under tmp_path/.metagit from the fixture appconfig.
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            str(app_cfg),
            "nav",
            "-c",
            str(home_manifest),
            "-p",
            "platform",
            "--repo",
            "backend",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert opened


def test_nav_resolves_sync_root_from_manifest_dir(tmp_path: Path, monkeypatch) -> None:
    """Nav must not use cwd-relative ./.metagit when manifest is elsewhere."""
    app_cfg, metagit_yml = _write_multi_project_fixture(tmp_path)
    workspace = tmp_path / ".metagit"
    app_cfg.write_text(
        app_cfg.read_text(encoding="utf-8").replace(
            f"path: {workspace.as_posix()}",
            "path: .metagit",
        ),
        encoding="utf-8",
    )
    other = tmp_path / "othercwd"
    other.mkdir()
    opened: list[str] = []
    monkeypatch.setattr("metagit.cli.commands.nav.open_editor", lambda _e, p: opened.append(p))
    monkeypatch.chdir(other)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", str(app_cfg), "nav", "-c", str(metagit_yml), "-p", "platform", "--repo", "backend"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert Path(opened[0]).resolve() == (tmp_path / ".metagit" / "platform" / "backend").resolve()
