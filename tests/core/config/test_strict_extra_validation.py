#!/usr/bin/env python
"""Regression tests for strict config extra-key validation."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _write_manifest(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_workspace_rejects_unknown_fields(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    _write_manifest(
        manifest,
        {
            "name": "demo",
            "workspace": {
                "projects": [],
                "research": [{"name": "extra"}],
            },
        },
    )

    result = MetagitConfigManager(config_path=manifest).load_config()

    assert isinstance(result, Exception)
    assert "research" in str(result)


def test_validate_config_returns_boolean_status(tmp_path: Path) -> None:
    valid_manifest = tmp_path / "valid.yml"
    _write_manifest(valid_manifest, {"name": "demo", "workspace": {"projects": []}})

    invalid_manifest = tmp_path / "invalid.yml"
    _write_manifest(
        invalid_manifest,
        {
            "name": "demo",
            "workspace": {"projects": [], "research": []},
        },
    )

    assert MetagitConfigManager(config_path=valid_manifest).validate_config() is True
    assert MetagitConfigManager(config_path=invalid_manifest).validate_config() is False


def test_core_manifest_models_forbid_extra_inputs() -> None:
    models: list[type[BaseModel]] = [MetagitConfig, Workspace, WorkspaceProject, ProjectPath]

    missing_forbid = [model.__name__ for model in models if model.model_config.get("extra") != "forbid"]

    assert not missing_forbid, f"Models missing extra='forbid': {', '.join(missing_forbid)}"
