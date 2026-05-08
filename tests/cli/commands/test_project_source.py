#!/usr/bin/env python
"""
CLI tests for project source sync commands.
"""

from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.project.models import ProjectPath
from metagit.core.project.source_models import SourceSyncPlan
from metagit.core.project.source_sync import SourceSyncService
from metagit.core.workspace.models import WorkspaceProject


def test_project_source_sync_dry_run(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(
        """
name: test-project
workspace:
  projects:
    - name: default
      repos: []
""".strip()
    )

    monkeypatch.setattr(
        SourceSyncService,
        "discover",
        lambda self, spec: [],
    )
    monkeypatch.setattr(
        SourceSyncService,
        "plan",
        lambda self, spec, project, discovered, mode: SourceSyncPlan(
            discovered_count=0, unchanged=0
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "project",
            "--config",
            str(config_path),
            "source",
            "sync",
            "--provider",
            "github",
            "--org",
            "metagit-ai",
            "--mode",
            "discover",
        ],
    )

    assert result.exit_code == 0


def test_project_source_sync_reconcile_requires_yes(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(
        """
name: test-project
workspace:
  projects:
    - name: default
      repos: []
""".strip()
    )

    monkeypatch.setattr(SourceSyncService, "discover", lambda self, spec: [])
    monkeypatch.setattr(
        SourceSyncService,
        "plan",
        lambda self, spec, project, discovered, mode: SourceSyncPlan(
            discovered_count=1,
            to_remove=[ProjectPath(name="old", url="https://example.com/repo.git")],
        ),
    )
    monkeypatch.setattr(
        SourceSyncService,
        "apply_plan",
        lambda self, project, plan, mode: WorkspaceProject(
            name=project.name, repos=project.repos
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "project",
            "--config",
            str(config_path),
            "source",
            "sync",
            "--provider",
            "github",
            "--org",
            "metagit-ai",
            "--mode",
            "reconcile",
            "--apply",
        ],
    )

    assert result.exit_code != 0
    assert "Reconcile mode has removals" in result.output
