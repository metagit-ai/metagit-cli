#!/usr/bin/env python
"""
Tests for manifest-driven source sync orchestration.
"""

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig, Workspace
from metagit.core.project.models import ProjectPath
from metagit.core.project.source_manifest_sync import SourceManifestSyncService
from metagit.core.project.source_models import (
    ProjectSource,
    SourceProvider,
    SourceSyncMode,
    SourceSyncPlan,
)
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.workspace.models import WorkspaceProject


def _config_with_sources() -> MetagitConfig:
    return MetagitConfig(
        name="demo",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    sources=[
                        ProjectSource(
                            id="acme-add",
                            provider=SourceProvider.GITHUB,
                            org="acme",
                            mode=SourceSyncMode.ADDITIVE,
                        ),
                        ProjectSource(
                            id="acme-reconcile",
                            provider=SourceProvider.GITHUB,
                            org="acme",
                            mode=SourceSyncMode.RECONCILE,
                        ),
                    ],
                    repos=[
                        ProjectPath(
                            name="manual",
                            path="./",
                        ),
                        ProjectPath(
                            name="old",
                            url="https://github.com/acme/old.git",
                            source_id="acme-reconcile",
                            source_provider="github",
                            source_namespace="acme",
                        ),
                    ],
                )
            ],
        ),
    )


def test_manifest_sync_partial_apply_queues_removals(
    monkeypatch,
    tmp_path,
) -> None:
    config = _config_with_sources()
    config_path = str(tmp_path / ".metagit.yml")

    def _discover(self, spec):
        return []

    def _plan(self, spec, project, discovered, mode):
        if spec.source_id == "acme-add":
            return SourceSyncPlan(
                discovered_count=1,
                filtered_count=1,
                to_add=[
                    ProjectPath(
                        name="new",
                        url="https://github.com/acme/new.git",
                        source_id="acme-add",
                    )
                ],
            )
        return SourceSyncPlan(
            discovered_count=1,
            filtered_count=1,
            to_remove=[
                ProjectPath(
                    name="old",
                    url="https://github.com/acme/old.git",
                    source_id="acme-reconcile",
                )
            ],
        )

    monkeypatch.setattr(
        "metagit.core.project.source_manifest_sync.SourceSyncService.discover",
        _discover,
    )
    monkeypatch.setattr(
        "metagit.core.project.source_manifest_sync.SourceSyncService.plan",
        _plan,
    )
    monkeypatch.setattr(
        "metagit.core.project.source_manifest_sync.MetagitConfigManager.save_config",
        lambda self, cfg, path: cfg,
    )

    approvals: list[dict] = []

    class _FakeApprovalService:
        def __init__(self, workspace_root: str) -> None:
            _ = workspace_root

        def request(self, action, payload, requested_by):
            approvals.append({"action": action, "payload": payload})
            from metagit.core.context.models import ApprovalRequest

            return ApprovalRequest(
                id="apr-1",
                action=action,
                status="pending",
                requested_by=requested_by,
                payload=payload,
                created_at="2026-06-11T00:00:00Z",
            )

    monkeypatch.setattr(
        "metagit.core.project.source_manifest_sync.ApprovalService",
        _FakeApprovalService,
    )

    result = SourceManifestSyncService().sync_project(
        app_config=AppConfig(),
        logger=UnifiedLogger(LoggerConfig(log_level="ERROR", minimal_console=True)),
        config=config,
        config_path=config_path,
        project_name="platform",
        apply=True,
        force=False,
        session_root=str(tmp_path),
    )

    assert result.ok is True
    assert result.applied is True
    assert result.pending_approval_id == "apr-1"
    project = config.workspace.projects[0]
    assert any(repo.name == "new" for repo in project.repos)
    assert any(repo.name == "old" for repo in project.repos)
    assert any(repo.name == "manual" for repo in project.repos)
    assert len(approvals) == 1
