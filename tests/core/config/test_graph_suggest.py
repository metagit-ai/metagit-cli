#!/usr/bin/env python

"""Tests for graph.relationships suggestion service."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

from metagit.core.config.graph_suggest import GraphRelationshipSuggestService
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.cross_project_dependencies import (
    CrossProjectDependencyService,
)
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _workspace_fixture(tmp_path: Path) -> tuple[MetagitConfig, str]:
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


def test_suggest_finds_import_and_url_match_candidates(tmp_path: Path) -> None:
    config, workspace_root = _workspace_fixture(tmp_path)
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = GraphRelationshipSuggestService(
        dependency_service=CrossProjectDependencyService(registry=registry)
    )

    result = service.suggest(
        config,
        workspace_root,
        min_confidence="medium",
    )

    assert result.ok is True
    assert result.candidates
    edge_types = {item.source_edge_type for item in result.candidates}
    assert "import" in edge_types or "url_match" in edge_types
    assert result.operations
    assert result.operations[0]["op"] == "enable"
    assert result.operations[0]["path"] == "graph"


def test_suggest_skips_existing_manual_relationships(tmp_path: Path) -> None:
    config, workspace_root = _workspace_fixture(tmp_path)
    config.graph = {
        "relationships": [
            {
                "from": {"project": "beta", "repo": "worker"},
                "to": {"project": "alpha", "repo": "api"},
                "type": "depends_on",
                "id": "existing-edge",
            }
        ]
    }
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = GraphRelationshipSuggestService(
        dependency_service=CrossProjectDependencyService(registry=registry)
    )

    result = service.suggest(config, workspace_root, min_confidence="high")

    assert result.ok is True
    assert not any(
        candidate.id == "existing-edge" for candidate in result.candidates
    )
    assert result.already_manual


def test_suggest_and_apply_writes_manifest(tmp_path: Path) -> None:
    config, workspace_root = _workspace_fixture(tmp_path)
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text("name: workspace\nworkspace:\n  projects: []\n", encoding="utf-8")
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = GraphRelationshipSuggestService(
        dependency_service=CrossProjectDependencyService(registry=registry)
    )

    result = service.suggest_and_apply(
        config,
        workspace_root,
        str(manifest),
        min_confidence="medium",
        dry_run=True,
    )

    assert result.apply is not None
    assert result.apply.saved is False
