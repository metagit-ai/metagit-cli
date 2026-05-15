#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.workspace_template
"""

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_template import WorkspaceTemplateService
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def test_template_apply_dry_run_lists_files(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    repo = root / "alpha" / "api"
    repo.mkdir(parents=True)
    config = MetagitConfig(
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
                        )
                    ],
                )
            ]
        ),
    )
    service = WorkspaceTemplateService()

    result = service.apply(
        config=config,
        workspace_root=str(root),
        template="agent-standard",
        target_projects=["alpha"],
        dry_run=True,
    )

    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["results"][0]["files"]


def test_template_apply_requires_confirm_when_not_dry_run(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    (root / "alpha" / "api").mkdir(parents=True)
    config = MetagitConfig(
        name="workspace",
        kind="application",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="alpha",
                    repos=[ProjectPath(name="api", path="alpha/api", sync=True)],
                )
            ]
        ),
    )
    service = WorkspaceTemplateService()

    result = service.apply(
        config=config,
        workspace_root=str(root),
        template="agent-standard",
        target_projects=["alpha"],
        dry_run=False,
        confirm_apply=False,
    )

    assert result["ok"] is False
    assert result["error"] == "confirm_apply_required"
