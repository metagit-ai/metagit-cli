#!/usr/bin/env python
from pathlib import Path

from types import SimpleNamespace

from metagit.cli.config_path import (
    DEFAULT_MANIFEST,
    detect_cli_config_file,
    resolve_cli_bootstrap,
    resolve_cli_manifest_path,
    resolve_cli_project,
)


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


def test_resolve_cli_manifest_path_prefers_root_definition() -> None:
    ctx = SimpleNamespace(obj={"definition_path": "/tmp/umbrella/.metagit.yml"})
    assert resolve_cli_manifest_path(DEFAULT_MANIFEST, ctx) == "/tmp/umbrella/.metagit.yml"


def test_resolve_cli_manifest_path_explicit_non_default_wins() -> None:
    ctx = SimpleNamespace(obj={"definition_path": "/tmp/umbrella/.metagit.yml"})
    assert resolve_cli_manifest_path("/other/.metagit.yml", ctx) == "/other/.metagit.yml"


def test_resolve_cli_project_leaf_then_command_then_root() -> None:
    ctx = SimpleNamespace(obj={"target_project": "rootproj", "command_project": "groupproj"})
    assert resolve_cli_project(ctx, explicit="leafproj") == "leafproj"
    ctx_root_only = SimpleNamespace(obj={"target_project": "rootproj", "command_project": None})
    assert resolve_cli_project(ctx_root_only, explicit=None) == "rootproj"
