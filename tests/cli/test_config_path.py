#!/usr/bin/env python
from pathlib import Path

from metagit.cli.config_path import detect_cli_config_file, resolve_cli_bootstrap


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


def test_resolve_manifest_loads_default_appconfig(tmp_path: Path) -> None:
    p = tmp_path / ".metagit.yml"
    p.write_text("name: umb\nkind: umbrella\nworkspace:\n  projects: []\n", encoding="utf-8")
    cfg, definition = resolve_cli_bootstrap(str(p))
    assert not isinstance(cfg, Exception)
    assert definition == str(p)
