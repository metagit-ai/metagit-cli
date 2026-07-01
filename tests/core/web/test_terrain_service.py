#!/usr/bin/env python
"""Tests for repository terrain DTO assembly."""

from pathlib import Path

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.web.terrain_service import RepositoryTerrainService


def test_build_manifest_view_is_fast_skeleton(tmp_path: Path) -> None:
    workspace_root = tmp_path / ".metagit"
    (workspace_root / "alpha" / "api").mkdir(parents=True)

    config = MetagitConfig(
        name="umbrella",
        workspace={
            "projects": [
                {
                    "name": "alpha",
                    "repos": [{"name": "api", "path": "services/api"}],
                },
                {
                    "name": "beta",
                    "repos": [{"name": "lib", "path": "lib"}],
                },
            ]
        },
    )
    app_config = AppConfig()

    view = RepositoryTerrainService().build_view(
        config=config,
        app_config=app_config,
        workspace_root=str(workspace_root),
        definition_root=str(workspace_root),
        detail_level="manifest",
    )

    assert view.detail_level == "manifest"
    assert view.node_count == 2
    assert len(view.projects) == 2
    assert view.projects[0].name == "alpha"
    node = view.nodes[0]
    assert node.visual.sync_color in {"gray", "neutral_blue"}
    assert node.git.branch is None
    assert node.pipeline is None


def test_build_view_filters_by_project(tmp_path: Path) -> None:
    workspace_root = tmp_path / ".metagit"
    api_dir = workspace_root / "alpha" / "services" / "api"
    lib_dir = workspace_root / "beta" / "lib"
    api_dir.mkdir(parents=True)
    lib_dir.mkdir(parents=True)

    config = MetagitConfig(
        name="umbrella",
        graph={
            "relationships": [
                {
                    "from": {"project": "alpha", "repo": "api"},
                    "to": {"project": "beta", "repo": "lib"},
                    "type": "depends_on",
                    "label": "imports lib",
                }
            ]
        },
        workspace={
            "projects": [
                {
                    "name": "alpha",
                    "repos": [
                        {
                            "name": "api",
                            "path": "services/api",
                            "url": "https://example.com/api.git",
                            "tags": {"team": "platform"},
                        },
                    ],
                },
                {
                    "name": "beta",
                    "repos": [{"name": "lib", "path": "lib"}],
                },
            ]
        },
    )
    app_config = AppConfig()

    view = RepositoryTerrainService().build_view(
        config=config,
        app_config=app_config,
        workspace_root=str(workspace_root),
        definition_root=str(workspace_root),
        project_filter="alpha",
        include_pipelines=False,
        include_inferred_deps=False,
    )

    assert view.ok
    assert view.node_count == 1
    assert view.project_filter == "alpha"
    assert len(view.projects) == 2
    assert view.nodes[0].repo_name == "api"
    assert view.nodes[0].ownership == "platform"


def test_build_view_places_nodes_and_dependencies(tmp_path: Path) -> None:
    workspace_root = tmp_path / ".metagit"
    api_dir = workspace_root / "alpha" / "services" / "api"
    lib_dir = workspace_root / "alpha" / "libs" / "core"
    api_dir.mkdir(parents=True)
    lib_dir.mkdir(parents=True)

    config = MetagitConfig(
        name="umbrella",
        graph={
            "relationships": [
                {
                    "from": {"project": "alpha", "repo": "api"},
                    "to": {"project": "alpha", "repo": "core"},
                    "type": "depends_on",
                    "label": "imports core",
                }
            ]
        },
        workspace={
            "projects": [
                {
                    "name": "alpha",
                    "repos": [
                        {
                            "name": "api",
                            "path": "services/api",
                            "url": "https://example.com/api.git",
                            "tags": {"team": "platform"},
                        },
                        {
                            "name": "core",
                            "path": "libs/core",
                            "url": "https://example.com/core.git",
                        },
                    ],
                }
            ]
        },
    )
    app_config = AppConfig()

    view = RepositoryTerrainService().build_view(
        config=config,
        app_config=app_config,
        workspace_root=str(workspace_root),
        definition_root=str(workspace_root),
        include_pipelines=False,
        include_inferred_deps=False,
    )

    assert view.ok
    assert view.detail_level == "enriched"
    assert view.node_count == 2
    assert len(view.nodes) == 2
    assert len(view.dependencies) == 1
    assert view.dependencies[0].label == "imports core"

    api_node = next(node for node in view.nodes if node.repo_name == "api")
    core_node = next(node for node in view.nodes if node.repo_name == "core")
    assert api_node.ownership == "platform"
    assert api_node.coordinates.x != core_node.coordinates.x or (
        api_node.coordinates.y != core_node.coordinates.y
    )
    assert api_node.dependencies_out == 1
    assert core_node.dependencies_in == 1
    assert len(view.regions) >= 1


def test_visual_state_elevation_from_ahead_behind() -> None:
    from metagit.core.web.terrain_service import (
        TerrainActivity,
        TerrainGitState,
        _visual_state,
    )

    git = TerrainGitState(ahead=5, behind=0, branch="main", branch_kind="default")
    visual = _visual_state(git, TerrainActivity(level="active", pulse_intensity=0.5))
    assert visual.elevation > 0
    assert visual.sync_color in {"green", "bright_green"}

    git_behind = TerrainGitState(ahead=0, behind=6, branch="main", branch_kind="default")
    visual_behind = _visual_state(git_behind, TerrainActivity(level="inactive"))
    assert visual_behind.elevation < 0
    assert visual_behind.sync_color == "deep_red"
    assert visual_behind.darken_factor > 0
