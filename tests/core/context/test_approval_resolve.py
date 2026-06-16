#!/usr/bin/env python
"""Tests for shared approval resolve orchestration."""

from metagit.core.config.models import MetagitConfig, Workspace
from metagit.core.context.approval_resolve import ApprovalResolveOrchestrator
from metagit.core.context.approval_service import ApprovalService
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import WorkspaceProject


def test_resolve_applies_source_sync_reconcile(monkeypatch, tmp_path) -> None:
    config = MetagitConfig(
        name="demo",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[
                        ProjectPath(name="keep", url="https://github.com/acme/keep.git"),
                        ProjectPath(name="old", url="https://github.com/acme/old.git"),
                    ],
                )
            ],
        ),
    )
    config_path = str(tmp_path / ".metagit.yml")
    session_root = str(tmp_path)
    monkeypatch.setattr(
        "metagit.core.project.source_approval_executor.MetagitConfigManager.save_config",
        lambda self, cfg, path: cfg,
    )

    pending = ApprovalService(workspace_root=session_root).request(
        action="source_sync_reconcile",
        payload={
            "project": "platform",
            "source_id": "acme-reconcile",
            "to_remove": [
                {"name": "old", "url": "https://github.com/acme/old.git"},
            ],
        },
        requested_by="test",
    )

    row = ApprovalResolveOrchestrator().resolve(
        workspace_root=session_root,
        config=config,
        config_path=config_path,
        request_id=pending.id,
        decision="approved",
    )
    assert not isinstance(row, Exception)
    assert row.status == "approved"
    assert len(config.workspace.projects[0].repos) == 1
    assert config.workspace.projects[0].repos[0].name == "keep"
