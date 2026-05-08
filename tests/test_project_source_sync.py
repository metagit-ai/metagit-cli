#!/usr/bin/env python
"""
Tests for source sync planner and applier.
"""

from metagit.core.appconfig.models import AppConfig
from metagit.core.project.models import ProjectPath
from metagit.core.project.source_models import (
    DiscoveredRepo,
    SourceProvider,
    SourceSpec,
    SourceSyncMode,
)
from metagit.core.project.source_sync import SourceSyncService
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.workspace.models import WorkspaceProject


def _service() -> SourceSyncService:
    return SourceSyncService(
        app_config=AppConfig(),
        logger=UnifiedLogger(LoggerConfig(log_level="ERROR", minimal_console=True)),
    )


def test_plan_additive_adds_missing_repo() -> None:
    service = _service()
    spec = SourceSpec(provider=SourceProvider.GITHUB, org="metagit-ai")
    project = WorkspaceProject(name="default", repos=[])
    discovered = [
        DiscoveredRepo(
            provider=SourceProvider.GITHUB,
            namespace="metagit-ai",
            full_name="metagit-ai/metagit-cli",
            name="metagit-cli",
            clone_url="https://github.com/metagit-ai/metagit-cli.git",
            repo_id="123",
        )
    ]
    plan = service.plan(spec, project, discovered, SourceSyncMode.ADDITIVE)
    assert len(plan.to_add) == 1
    assert len(plan.to_remove) == 0


def test_plan_reconcile_removes_unmatched_provider_managed_repo() -> None:
    service = _service()
    spec = SourceSpec(provider=SourceProvider.GITHUB, org="metagit-ai")
    project = WorkspaceProject(
        name="default",
        repos=[
            ProjectPath(
                name="old-repo",
                url="https://github.com/metagit-ai/old-repo.git",
                source_provider="github",
                source_namespace="metagit-ai",
                source_repo_id="1",
            )
        ],
    )
    discovered = [
        DiscoveredRepo(
            provider=SourceProvider.GITHUB,
            namespace="metagit-ai",
            full_name="metagit-ai/new-repo",
            name="new-repo",
            clone_url="https://github.com/metagit-ai/new-repo.git",
            repo_id="2",
        )
    ]
    plan = service.plan(spec, project, discovered, SourceSyncMode.RECONCILE)
    assert len(plan.to_add) == 1
    assert len(plan.to_remove) == 1


def test_apply_plan_reconcile_preserves_protected_repo() -> None:
    service = _service()
    project = WorkspaceProject(
        name="default",
        repos=[
            ProjectPath(
                name="protected-repo",
                url="https://github.com/metagit-ai/protected-repo.git",
                source_provider="github",
                source_namespace="metagit-ai",
                protected=True,
            )
        ],
    )
    plan = service.plan(
        SourceSpec(provider=SourceProvider.GITHUB, org="metagit-ai"),
        project,
        [],
        SourceSyncMode.RECONCILE,
    )
    updated = service.apply_plan(project, plan, SourceSyncMode.RECONCILE)
    assert len(updated.repos) == 1
    assert updated.repos[0].name == "protected-repo"
