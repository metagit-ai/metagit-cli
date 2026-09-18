#!/usr/bin/env python
from pathlib import Path

from metagit.core.appconfig.paths import (
    default_user_appconfig_path,
    first_existing_user_appconfig,
    local_appconfig_paths,
    user_appconfig_paths,
)


def test_user_appconfig_paths_use_home_config(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    paths = user_appconfig_paths()
    assert paths[0] == home / ".config" / "metagit" / "config.yml"
    assert paths[1] == home / ".config" / "metagit" / "config.yaml"
    assert default_user_appconfig_path() == str(paths[0])
    assert first_existing_user_appconfig() is None


def test_user_appconfig_paths_honor_xdg(tmp_path: Path, monkeypatch) -> None:
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    existing = xdg / "metagit" / "config.yaml"
    existing.parent.mkdir(parents=True)
    existing.write_text("config:\n  description: xdg\n", encoding="utf-8")
    assert first_existing_user_appconfig() == existing
    assert default_user_appconfig_path() == str(existing)


def test_local_appconfig_paths() -> None:
    directory = Path("/tmp/project")
    assert local_appconfig_paths(directory) == [
        directory / "metagit.config.yaml",
        directory / "metagit.config.yml",
    ]
