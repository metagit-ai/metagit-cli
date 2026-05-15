#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.workspace_health
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_health import WorkspaceHealthService
from metagit.core.project.models import ProjectPath
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
                                url="https://github.com/example/api.git",
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


def test_health_check_reports_missing_repo(tmp_path: Path) -> None:
    config, workspace_root = _config(tmp_path)
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {str(tmp_path / "workspace" / "alpha" / "api"): "missing"}
    service = WorkspaceHealthService(registry=registry)

    result = service.check(
        config=config,
        workspace_root=workspace_root,
        check_gitnexus=True,
    )

    assert result.ok is True
    actions = {item.action for item in result.recommendations}
    assert "clone" in actions
    assert result.summary["repos_missing"] >= 1


@patch("metagit.core.mcp.services.workspace_health.inspect_repo_state")
def test_health_check_stale_branch_metrics_and_recommendations(
    mock_inspect: MagicMock, tmp_path: Path
) -> None:
    config, workspace_root = _config(tmp_path)
    registry = MagicMock()
    registry.summarize_for_paths.return_value = {}

    mock_inspect.return_value = {
        "ok": True,
        "branch": "feature/old",
        "dirty": False,
        "ahead": 0,
        "behind": 0,
        "head_commit_age_days": 400.0,
        "merge_base_age_days": 100.0,
    }

    service = WorkspaceHealthService(registry=registry)
    result = service.check(
        config=config,
        workspace_root=workspace_root,
        check_gitnexus=False,
        check_stale_branches=True,
        branch_head_warning_days=180.0,
        branch_head_critical_days=365.0,
        integration_stale_days=90.0,
    )

    repo = next(r for r in result.repos if r.repo_name == "api")
    assert repo.head_commit_age_days == 400.0
    assert repo.merge_base_age_days == 100.0
    assert result.summary["repos_branch_head_stale_critical"] == 1
    assert result.summary["repos_integration_stale"] == 1
    actions = {item.action for item in result.recommendations}
    assert "review_branch_age" in actions
    assert "reconcile_integration" in actions
