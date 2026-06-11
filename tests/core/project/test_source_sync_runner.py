#!/usr/bin/env python
"""
Tests for shared source sync orchestration.
"""

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig, Workspace
from metagit.core.project.models import ProjectPath
from metagit.core.project.source_models import (
    SourceProvider,
    SourceSpec,
    SourceSyncMode,
    SourceSyncPlan,
)
from metagit.core.project.source_sync_runner import SourceSyncRunRequest, run_source_sync
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.workspace.models import WorkspaceProject


def _config() -> MetagitConfig:
    return MetagitConfig(
        name="test",
        workspace=Workspace(
            projects=[WorkspaceProject(name="default", repos=[])],
        ),
    )


def test_run_source_sync_dry_run(monkeypatch, tmp_path) -> None:
    config = _config()
    config_path = str(tmp_path / ".metagit.yml")

    monkeypatch.setattr(
        "metagit.core.project.source_sync_runner.SourceSyncService.discover",
        lambda self, spec: [],
    )
    monkeypatch.setattr(
        "metagit.core.project.source_sync_runner.SourceSyncService.plan",
        lambda self, spec, project, discovered, mode: SourceSyncPlan(
            discovered_count=0,
            filtered_count=0,
        ),
    )

    result = run_source_sync(
        app_config=AppConfig(),
        logger=UnifiedLogger(LoggerConfig(log_level="ERROR", minimal_console=True)),
        config=config,
        config_path=config_path,
        request=SourceSyncRunRequest(
            spec=SourceSpec(provider=SourceProvider.GITHUB, org="acme"),
            mode=SourceSyncMode.DISCOVER,
            project_name="default",
        ),
    )
    assert result.ok is True
    assert result.applied is False


def test_run_source_sync_reconcile_requires_confirm(monkeypatch, tmp_path) -> None:
    config = _config()
    config_path = str(tmp_path / ".metagit.yml")

    monkeypatch.setattr(
        "metagit.core.project.source_sync_runner.SourceSyncService.discover",
        lambda self, spec: [],
    )
    monkeypatch.setattr(
        "metagit.core.project.source_sync_runner.SourceSyncService.plan",
        lambda self, spec, project, discovered, mode: SourceSyncPlan(
            discovered_count=1,
            filtered_count=1,
            to_remove=[
                ProjectPath(name="old", url="https://github.com/acme/old.git"),
            ],
        ),
    )

    result = run_source_sync(
        app_config=AppConfig(),
        logger=UnifiedLogger(LoggerConfig(log_level="ERROR", minimal_console=True)),
        config=config,
        config_path=config_path,
        request=SourceSyncRunRequest(
            spec=SourceSpec(provider=SourceProvider.GITHUB, org="acme"),
            mode=SourceSyncMode.RECONCILE,
            project_name="default",
            apply=True,
            confirm_reconcile=False,
        ),
    )
    assert result.ok is False
    assert result.errors[0].kind == "reconcile_confirmation_required"
