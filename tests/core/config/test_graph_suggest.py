#!/usr/bin/env python

"""Tests for graph.relationships suggestion service."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

from metagit.core.config.graph_suggest import GraphRelationshipSuggestService
from metagit.core.config.graph_validation import validate_graph_relationships
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.cross_project_dependencies import (
    CrossProjectDependencyService,
)
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _workspace_fixture(
    tmp_path: Path,
    *,
    shared_url: bool = True,
    with_import: bool = True,
) -> tuple[MetagitConfig, str]:
    root = tmp_path / "workspace"
    alpha_url = "https://github.com/example/shared-lib.git"
    beta_url = alpha_url if shared_url else "https://github.com/example/beta-only.git"
    alpha_repo = root / "alpha" / "api"
    beta_repo = root / "beta" / "worker"
    alpha_repo.mkdir(parents=True)
    beta_repo.mkdir(parents=True)
    (alpha_repo / ".git").mkdir()
    (beta_repo / ".git").mkdir()
    if with_import:
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
                                url=alpha_url,
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
                                url=beta_url,
                                sync=True,
                            )
                        ],
                    ),
                ]
            ),
        ),
        str(root),
    )


def _applyable_fixture(tmp_path: Path) -> tuple[MetagitConfig, str, Path]:
    """Workspace fixture plus an on-disk manifest that mirrors it, with no graph section."""
    config, workspace_root = _workspace_fixture(tmp_path)
    manifest = tmp_path / ".metagit.yml"
    projects = "\n".join(
        f"    - name: {project.name}\n      repos:\n"
        + "\n".join(
            f"        - name: {repo.name}\n          path: {repo.path}\n          url: {repo.url}"
            for repo in project.repos
        )
        for project in config.workspace.projects
    )
    manifest.write_text(
        f"name: workspace\nkind: application\nworkspace:\n  projects:\n{projects}\n",
        encoding="utf-8",
    )
    return config, workspace_root, manifest


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
    assert len(result.operations) == 1
    operation = result.operations[0]
    assert operation["op"] == "set"
    assert operation["path"] == "graph.relationships"
    assert len(operation["value"]) == len(result.candidates)
    assert all("from" in value for value in operation["value"])


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


def test_suggest_aggregates_scan_stats_across_repos(tmp_path: Path) -> None:
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
    assert result.scan_stats is not None
    assert set(result.scan_stats) <= {"dirs_pruned", "files_skipped_gitignore", "files_yielded"}
    # Two repos, one prunable `.git` each: counted once per repo despite one
    # map_dependencies call per project re-scanning the whole workspace.
    assert result.scan_stats["dirs_pruned"] == 2


def test_suggest_reports_stale_manual_edges(tmp_path: Path) -> None:
    config, workspace_root = _workspace_fixture(tmp_path, shared_url=False, with_import=False)
    config.graph = {
        "relationships": [
            {
                "id": "orphan-edge",
                "from": {"project": "alpha", "repo": "api"},
                "to": {"project": "beta", "repo": "worker"},
                "type": "depends_on",
                "status": "active",
                "provenance": "manual",
            }
        ]
    }
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = GraphRelationshipSuggestService(
        dependency_service=CrossProjectDependencyService(registry=registry)
    )
    result = service.suggest(config, workspace_root, min_confidence="all", include_declared=True)
    assert any("orphan-edge" in item for item in result.stale_manual)


def test_suggest_does_not_flag_proposed_manual_edges_as_stale(tmp_path: Path) -> None:
    config, workspace_root = _workspace_fixture(tmp_path, shared_url=False, with_import=False)
    config.graph = {
        "relationships": [
            {
                "id": "draft-edge",
                "from": {"project": "alpha", "repo": "api"},
                "to": {"project": "beta", "repo": "worker"},
                "type": "depends_on",
                "status": "proposed",
                "provenance": "manual",
            }
        ]
    }
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = GraphRelationshipSuggestService(
        dependency_service=CrossProjectDependencyService(registry=registry)
    )
    result = service.suggest(config, workspace_root, min_confidence="all", include_declared=True)
    assert not any("draft-edge" in item for item in result.stale_manual)


def test_suggest_does_not_flag_promoted_or_imported_edges_as_stale(tmp_path: Path) -> None:
    config, workspace_root = _workspace_fixture(tmp_path, shared_url=False, with_import=False)
    config.graph = {
        "relationships": [
            {
                "id": "promoted-edge",
                "from": {"project": "alpha", "repo": "api"},
                "to": {"project": "beta", "repo": "worker"},
                "type": "depends_on",
                "status": "active",
                "provenance": "promoted",
            },
            {
                "id": "imported-edge",
                "from": {"project": "alpha", "repo": "api"},
                "to": {"project": "beta", "repo": "worker"},
                "type": "consumes",
                "status": "active",
                "provenance": "imported",
            },
        ]
    }
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = GraphRelationshipSuggestService(
        dependency_service=CrossProjectDependencyService(registry=registry)
    )
    result = service.suggest(config, workspace_root, min_confidence="all", include_declared=True)
    assert not any("promoted-edge" in item for item in result.stale_manual)
    assert not any("imported-edge" in item for item in result.stale_manual)


def test_suggest_does_not_flag_deprecated_manual_edges_as_stale(tmp_path: Path) -> None:
    config, workspace_root = _workspace_fixture(tmp_path, shared_url=False, with_import=False)
    config.graph = {
        "relationships": [
            {
                "id": "retired-edge",
                "from": {"project": "alpha", "repo": "api"},
                "to": {"project": "beta", "repo": "worker"},
                "type": "depends_on",
                "status": "deprecated",
                "provenance": "manual",
            }
        ]
    }
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = GraphRelationshipSuggestService(
        dependency_service=CrossProjectDependencyService(registry=registry)
    )
    result = service.suggest(config, workspace_root, min_confidence="all", include_declared=True)
    assert not any("retired-edge" in item for item in result.stale_manual)


def test_suggest_does_not_flag_manual_edge_supported_by_other_relationship_type(
    tmp_path: Path,
) -> None:
    """An inferred edge between the same endpoints supports a manual edge of any type."""
    config, workspace_root = _workspace_fixture(tmp_path)
    config.graph = {
        "relationships": [
            {
                "id": "typed-edge",
                "from": {"project": "beta", "repo": "worker"},
                "to": {"project": "alpha", "repo": "api"},
                "type": "consumes",
                "status": "active",
                "provenance": "manual",
            }
        ]
    }
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = GraphRelationshipSuggestService(
        dependency_service=CrossProjectDependencyService(registry=registry)
    )

    result = service.suggest(config, workspace_root, min_confidence="high")

    assert not any("typed-edge" in item for item in result.stale_manual)


def test_suggest_and_apply_produces_a_valid_manifest_without_prior_graph(
    tmp_path: Path,
) -> None:
    """Applying to a manifest with no graph section must not write placeholder edges."""
    config, workspace_root, manifest = _applyable_fixture(tmp_path)
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
    )

    assert result.apply is not None
    assert result.apply.ok is True
    assert result.apply.saved is True
    assert result.apply.applied_count >= 1

    reloaded = MetagitConfigManager(config_path=str(manifest)).load_config()
    assert not isinstance(reloaded, Exception)
    assert validate_graph_relationships(reloaded) == []
    assert reloaded.graph is not None
    assert len(reloaded.graph.relationships) == result.apply.applied_count


def test_suggest_and_apply_writes_alias_and_lifecycle_keys(tmp_path: Path) -> None:
    config, workspace_root, manifest = _applyable_fixture(tmp_path)
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}
    service = GraphRelationshipSuggestService(
        dependency_service=CrossProjectDependencyService(registry=registry)
    )

    service.suggest_and_apply(config, workspace_root, str(manifest), min_confidence="medium")

    written = manifest.read_text(encoding="utf-8")
    assert "from_endpoint:" not in written
    assert "from:" in written
    assert "status: active" in written
    assert "provenance: promoted" in written


def test_suggest_and_apply_reports_validation_errors_without_writing(tmp_path: Path) -> None:
    config, workspace_root, manifest = _applyable_fixture(tmp_path)
    # An existing edge with no id makes the patched document invalid, so the
    # pre-write gate must reject the whole apply.
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + "graph:\n  relationships:\n    - from:\n        project: alpha\n"
        "      to:\n        project: beta\n",
        encoding="utf-8",
    )
    before = manifest.read_text(encoding="utf-8")
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
    )

    assert result.apply is not None
    assert result.apply.ok is False
    assert result.apply.saved is False
    assert result.apply.validation_errors
    assert manifest.read_text(encoding="utf-8") == before


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
