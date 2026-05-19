#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.cross_project_dependencies
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.cross_project_dependencies import (
    CrossProjectDependencyService,
)
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _workspace_config(tmp_path: Path) -> tuple[MetagitConfig, str]:
    root = tmp_path / "workspace"
    shared_url = "https://github.com/example/shared-lib.git"
    alpha_repo = root / "alpha" / "api"
    beta_repo = root / "beta" / "worker"
    alpha_repo.mkdir(parents=True)
    beta_repo.mkdir(parents=True)
    (alpha_repo / ".git").mkdir()
    (beta_repo / ".git").mkdir()
    relative_api = os.path.relpath(alpha_repo, beta_repo)
    (beta_repo / "package.json").write_text(
        json.dumps(
            {
                "name": "worker",
                "dependencies": {"api-client": f"file:{relative_api}"},
            }
        ),
        encoding="utf-8",
    )
    return (
        MetagitConfig(
            name="workspace",
            kind="application",
            workspace=Workspace(
                projects=[
                    WorkspaceProject(
                        name="alpha",
                        repos=[
                            ProjectPath(
                                name="api",
                                path="alpha/api",
                                url=shared_url,
                                sync=True,
                                tags={"depends_on": "beta"},
                            )
                        ],
                    ),
                    WorkspaceProject(
                        name="beta",
                        repos=[
                            ProjectPath(
                                name="worker",
                                path="beta/worker",
                                url=shared_url,
                                sync=True,
                            )
                        ],
                    ),
                ]
            ),
        ),
        str(root),
    )


def test_map_dependencies_finds_url_match_and_imports(tmp_path: Path) -> None:
    config, workspace_root = _workspace_config(tmp_path)
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {
        str(tmp_path / "workspace" / "alpha" / "api"): "indexed",
        str(tmp_path / "workspace" / "beta" / "worker"): "missing",
    }
    service = CrossProjectDependencyService(registry=registry)

    result = service.map_dependencies(
        config=config,
        workspace_root=workspace_root,
        source_project="alpha",
        dependency_types=["declared", "shared_config", "imports"],
        depth=2,
    )

    assert result.ok is True
    edge_types = {edge.type for edge in result.edges}
    assert "url_match" in edge_types
    assert "declared" in edge_types
    assert result.impact_summary.affected_projects == ["beta"]


def test_map_dependencies_unknown_project(tmp_path: Path) -> None:
    config, workspace_root = _workspace_config(tmp_path)
    service = CrossProjectDependencyService(registry=MagicMock())

    result = service.map_dependencies(
        config=config,
        workspace_root=workspace_root,
        source_project="missing",
    )

    assert result.ok is False
    assert result.error == "project_not_found"


def test_map_dependencies_respects_depth(tmp_path: Path) -> None:
    config, workspace_root = _workspace_config(tmp_path)
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = CrossProjectDependencyService(registry=registry)

    shallow = service.map_dependencies(
        config=config,
        workspace_root=workspace_root,
        source_project="alpha",
        depth=1,
    )
    deep = service.map_dependencies(
        config=config,
        workspace_root=workspace_root,
        source_project="alpha",
        depth=3,
    )

    assert len(deep.nodes) >= len(shallow.nodes)
