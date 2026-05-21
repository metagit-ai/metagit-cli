#!/usr/bin/env python

"""Tests for ConfigPatchService."""

from pathlib import Path

import yaml

from metagit.core.config.patch_service import ConfigPatchService
from metagit.core.web.models import ConfigOpKind, ConfigOperation


def _write_metagit(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")


def test_patch_metagit_set_name_dry_run(tmp_path: Path) -> None:
    config_path = tmp_path / ".metagit.yml"
    _write_metagit(
        config_path,
        {
            "name": "before",
            "kind": "application",
            "workspace": {"projects": []},
        },
    )
    service = ConfigPatchService()
    result = service.patch(
        "metagit",
        str(config_path),
        [ConfigOperation(op=ConfigOpKind.SET, path="name", value="after")],
        save=False,
    )
    assert not isinstance(result, Exception)
    assert result.ok is True
    assert result.saved is False
    assert result.validation_errors == []
    on_disk = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert on_disk["name"] == "before"


def test_patch_metagit_set_name_save(tmp_path: Path) -> None:
    config_path = tmp_path / ".metagit.yml"
    _write_metagit(
        config_path,
        {
            "name": "before",
            "kind": "application",
            "workspace": {"projects": []},
        },
    )
    service = ConfigPatchService()
    result = service.patch(
        "metagit",
        str(config_path),
        [ConfigOperation(op=ConfigOpKind.SET, path="name", value="after")],
        save=True,
    )
    assert not isinstance(result, Exception)
    assert result.ok is True
    assert result.saved is True
    on_disk = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert on_disk["name"] == "after"


def test_patch_append_workspace_project(tmp_path: Path) -> None:
    config_path = tmp_path / ".metagit.yml"
    _write_metagit(
        config_path,
        {
            "name": "workspace-test",
            "kind": "application",
            "workspace": {"projects": []},
        },
    )
    service = ConfigPatchService()
    result = service.patch(
        "metagit",
        str(config_path),
        [
            ConfigOperation(op=ConfigOpKind.APPEND, path="workspace.projects"),
            ConfigOperation(
                op=ConfigOpKind.SET,
                path="workspace.projects[0].name",
                value="new-project",
            ),
        ],
        save=True,
    )
    assert not isinstance(result, Exception)
    assert result.ok is True
    assert result.saved is True
    on_disk = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert on_disk["workspace"]["projects"][0]["name"] == "new-project"
