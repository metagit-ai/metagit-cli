#!/usr/bin/env python
"""
Unit tests for workspace discovery / readiness (RFC-0020).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.models import McpActivationState, WorkspaceStatus
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.discovery_service import (
    WorkspaceDiscoveryService,
    readiness_grade,
)
from metagit.core.workspace.health_models import (
    HealthRecommendation,
    WorkspaceHealthResult,
)
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _config(tmp_path: Path) -> tuple[MetagitConfig, str]:
    root = tmp_path / "workspace"
    present = root / "alpha" / "api"
    present.mkdir(parents=True)
    (present / ".git").mkdir()
    (root / ".metagit.yml").write_text(
        "name: workspace\nkind: application\nworkspace:\n  projects: []\n",
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
                                sync=True,
                            ),
                            ProjectPath(
                                name="missing",
                                path="alpha/missing",
                                sync=True,
                            ),
                        ],
                    )
                ]
            ),
        ),
        str(root),
    )


def test_readiness_grade_bands() -> None:
    assert readiness_grade(90) == "excellent"
    assert readiness_grade(75) == "good"
    assert readiness_grade(50) == "fair"
    assert readiness_grade(49) == "poor"


def test_summary_includes_readiness_for_missing_clone(tmp_path: Path) -> None:
    config, workspace_root = _config(tmp_path)
    gate = MagicMock()
    gate.evaluate.return_value = WorkspaceStatus(
        state=McpActivationState.ACTIVE,
        root_path=workspace_root,
        reason=None,
    )
    health = MagicMock()
    health.check.return_value = WorkspaceHealthResult(
        ok=True,
        workspace_root=workspace_root,
        summary={"repos_total": 2, "repos_missing": 1, "recommendations": 1},
        recommendations=[
            HealthRecommendation(
                severity="warning",
                action="clone",
                message="Configured repository path is missing on disk.",
                project_name="alpha",
                repo_name="missing",
            )
        ],
    )
    index = MagicMock()
    index.build_index.return_value = [
        {
            "project_name": "alpha",
            "repo_name": "api",
            "repo_path": str(Path(workspace_root) / "alpha" / "api"),
            "exists": True,
            "is_git_repo": True,
            "status": "present",
        },
        {
            "project_name": "alpha",
            "repo_name": "missing",
            "repo_path": str(Path(workspace_root) / "alpha" / "missing"),
            "exists": False,
            "is_git_repo": False,
            "status": "configured_missing",
        },
    ]
    service = WorkspaceDiscoveryService(health_service=health, index_service=index, gate=gate)
    result = service.summary(
        config=config,
        workspace_root=workspace_root,
        include_coordination=False,
    )

    assert "readiness" in result.model_dump()
    assert isinstance(result.readiness.score, int)
    assert 0 <= result.readiness.score <= 100
    assert "gate_active" in result.readiness.dimensions
    assert "repos_present" in result.readiness.dimensions
    assert any(b.code == "missing_clone" for b in result.readiness.blockers)
    assert result.map.repos_total == 2
    assert result.map.repos_missing == 1
    assert result.map.repos_present == 1


def test_summary_readiness_deterministic(tmp_path: Path) -> None:
    config, workspace_root = _config(tmp_path)
    root = Path(workspace_root)
    (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    config = config.model_copy(update={"agent_instructions": "use context pack"})

    gate = MagicMock()
    gate.evaluate.return_value = WorkspaceStatus(
        state=McpActivationState.ACTIVE,
        root_path=workspace_root,
        reason=None,
    )
    health = MagicMock()
    health.check.return_value = WorkspaceHealthResult(
        ok=True,
        workspace_root=workspace_root,
        summary={"repos_total": 1, "repos_missing": 0, "recommendations": 0},
        recommendations=[],
    )
    index = MagicMock()
    api = root / "alpha" / "api"
    (api / "AGENTS.md").write_text("# repo\n", encoding="utf-8")
    index.build_index.return_value = [
        {
            "project_name": "alpha",
            "repo_name": "api",
            "repo_path": str(api),
            "exists": True,
            "is_git_repo": True,
            "status": "present",
        },
    ]
    service = WorkspaceDiscoveryService(
        health_service=health,
        index_service=index,
        gate=gate,
        now_fn=lambda: "2026-08-27T19:00:00Z",
    )
    first = service.summary(config=config, workspace_root=workspace_root, include_coordination=False)
    second = service.summary(config=config, workspace_root=workspace_root, include_coordination=False)
    assert first.readiness.score == second.readiness.score
    assert first.readiness.dimensions == second.readiness.dimensions
    assert first.generated_at == "2026-08-27T19:00:00Z"


def test_health_delegates_to_workspace_health_service(tmp_path: Path) -> None:
    config, workspace_root = _config(tmp_path)
    health = MagicMock()
    expected = WorkspaceHealthResult(ok=True, workspace_root=workspace_root)
    health.check.return_value = expected
    service = WorkspaceDiscoveryService(health_service=health)
    result = service.health(config=config, workspace_root=workspace_root, check_gitnexus=False)
    assert result is expected
    health.check.assert_called_once()
    kwargs = health.check.call_args.kwargs
    assert kwargs["check_gitnexus"] is False


def test_agent_surface_blockers_without_agents_md(tmp_path: Path) -> None:
    config, workspace_root = _config(tmp_path)
    gate = MagicMock()
    gate.evaluate.return_value = WorkspaceStatus(
        state=McpActivationState.ACTIVE,
        root_path=workspace_root,
        reason=None,
    )
    health = MagicMock()
    health.check.return_value = WorkspaceHealthResult(
        ok=True,
        workspace_root=workspace_root,
        recommendations=[],
    )
    index = MagicMock()
    index.build_index.return_value = [
        {
            "project_name": "alpha",
            "repo_name": "api",
            "repo_path": str(Path(workspace_root) / "alpha" / "api"),
            "exists": True,
            "is_git_repo": True,
            "status": "present",
        },
    ]
    service = WorkspaceDiscoveryService(health_service=health, index_service=index, gate=gate)
    result = service.summary(config=config, workspace_root=workspace_root, include_coordination=False)
    codes = {b.code for b in result.readiness.blockers}
    assert "missing_agents_md" in codes
    assert result.agent_surfaces.umbrella_has_agents_md is False
