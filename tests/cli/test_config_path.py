#!/usr/bin/env python
from pathlib import Path

import pytest

from metagit import DEFAULT_CONFIG
from metagit.cli.config_path import detect_cli_config_file, resolve_cli_bootstrap


def _empty_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    return home


def test_detect_appconfig(tmp_path: Path) -> None:
    p = tmp_path / "metagit.config.yaml"
    p.write_text("config:\n  description: x\n  editor: code\n", encoding="utf-8")
    assert detect_cli_config_file(str(p)) == "appconfig"


def test_detect_manifest(tmp_path: Path) -> None:
    p = tmp_path / ".metagit.yml"
    p.write_text("name: umb\nkind: umbrella\nworkspace:\n  projects: []\n", encoding="utf-8")
    assert detect_cli_config_file(str(p)) == "manifest"


def test_detect_invalid(tmp_path: Path) -> None:
    p = tmp_path / "junk.yml"
    p.write_text("foo: 1\n", encoding="utf-8")
    assert detect_cli_config_file(str(p)) == "invalid"


def test_resolve_manifest_loads_default_appconfig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _empty_home(tmp_path, monkeypatch)
    p = tmp_path / ".metagit.yml"
    p.write_text("name: umb\nkind: umbrella\nworkspace:\n  projects: []\n", encoding="utf-8")
    cfg, definition, appconfig_path = resolve_cli_bootstrap(str(p))
    assert not isinstance(cfg, Exception)
    assert definition == str(p)
    assert appconfig_path == DEFAULT_CONFIG


def test_resolve_missing_prefers_local_yml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _empty_home(tmp_path, monkeypatch)
    cwd = tmp_path / "project"
    cwd.mkdir()
    local_yml = cwd / "metagit.config.yml"
    local_yml.write_text("config:\n  description: from-yml\n  editor: vim\n", encoding="utf-8")
    monkeypatch.chdir(cwd)
    cfg, definition, appconfig_path = resolve_cli_bootstrap("metagit.config.yaml")
    assert not isinstance(cfg, Exception)
    assert definition is None
    assert appconfig_path == str(local_yml.resolve())
    assert cfg.description == "from-yml"


def test_resolve_missing_prefers_user_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = _empty_home(tmp_path, monkeypatch)
    user_cfg = home / ".config" / "metagit" / "config.yml"
    user_cfg.parent.mkdir(parents=True)
    user_cfg.write_text(
        "config:\n  description: from-user\n  editor: vim\n  workspace:\n    path: ~/.metagit\n",
        encoding="utf-8",
    )
    cwd = tmp_path / "project"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    cfg, definition, appconfig_path = resolve_cli_bootstrap("metagit.config.yaml")
    assert not isinstance(cfg, Exception)
    assert definition is None
    assert appconfig_path == str(user_cfg)
    assert cfg.description == "from-user"
    assert cfg.workspace.path == "~/.metagit"


def test_resolve_manifest_prefers_user_config_when_no_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _empty_home(tmp_path, monkeypatch)
    user_cfg = home / ".config" / "metagit" / "config.yml"
    user_cfg.parent.mkdir(parents=True)
    user_cfg.write_text(
        "config:\n  description: from-user\n  workspace:\n    path: ~/.metagit\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "project" / ".metagit.yml"
    manifest.parent.mkdir()
    manifest.write_text("name: umb\nkind: umbrella\nworkspace:\n  projects: []\n", encoding="utf-8")
    cfg, definition, appconfig_path = resolve_cli_bootstrap(str(manifest))
    assert not isinstance(cfg, Exception)
    assert definition == str(manifest)
    assert appconfig_path == str(user_cfg)
    assert cfg.workspace.path == "~/.metagit"


def test_resolve_local_yaml_wins_over_user_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = _empty_home(tmp_path, monkeypatch)
    user_cfg = home / ".config" / "metagit" / "config.yml"
    user_cfg.parent.mkdir(parents=True)
    user_cfg.write_text("config:\n  description: from-user\n", encoding="utf-8")
    cwd = tmp_path / "project"
    cwd.mkdir()
    local_yaml = cwd / "metagit.config.yaml"
    local_yaml.write_text("config:\n  description: from-local\n", encoding="utf-8")
    monkeypatch.chdir(cwd)
    cfg, definition, appconfig_path = resolve_cli_bootstrap("metagit.config.yaml")
    assert not isinstance(cfg, Exception)
    assert definition is None
    assert appconfig_path == str(local_yaml.resolve())
    assert cfg.description == "from-local"


def test_resolve_missing_falls_back_to_bundled_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _empty_home(tmp_path, monkeypatch)
    cwd = tmp_path / "project"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    cfg, definition, appconfig_path = resolve_cli_bootstrap("metagit.config.yaml")
    assert not isinstance(cfg, Exception)
    assert definition is None
    assert appconfig_path == DEFAULT_CONFIG
    assert appconfig_path != cfg.workspace.path
    assert cfg.workspace.path == "./.metagit"
