#!/usr/bin/env python
"""
Tests for approved source reconcile removal executor.
"""

from metagit.core.config.models import MetagitConfig, Workspace
from metagit.core.context.models import ApprovalRequest
from metagit.core.project.models import ProjectPath
from metagit.core.project.source_approval_executor import SourceSyncApprovalExecutor
from metagit.core.workspace.models import WorkspaceProject


def test_apply_payload_removes_listed_repos(monkeypatch, tmp_path) -> None:
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
    monkeypatch.setattr(
        "metagit.core.project.source_approval_executor.MetagitConfigManager.save_config",
        lambda self, cfg, path: cfg,
    )

    approval = ApprovalRequest(
        id="apr-1",
        action="source_sync_reconcile",
        status="approved",
        requested_by="human",
        payload={
            "project": "platform",
            "source_id": "acme-reconcile",
            "to_remove": [
                {"name": "old", "url": "https://github.com/acme/old.git"},
            ],
        },
        created_at="2026-06-11T00:00:00Z",
        resolved_at="2026-06-11T00:00:01Z",
    )

    updated = SourceSyncApprovalExecutor().apply_if_approved(
        approval=approval,
        config=config,
        config_path=config_path,
    )
    assert not isinstance(updated, Exception)
    repos = updated.workspace.projects[0].repos
    assert len(repos) == 1
    assert repos[0].name == "keep"
