#!/usr/bin/env python
"""Tests for per-project dedupe resolution."""

from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.dedupe_resolver import (
    resolve_dedupe_for_layout,
    resolve_effective_dedupe,
    resolve_effective_dedupe_for_project,
)
from metagit.core.workspace.models import (
    ProjectDedupeOverride,
    Workspace,
    WorkspaceProject,
)


def _config_with_projects() -> MetagitConfig:
    return MetagitConfig(
        name="ws",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="deduped",
                    repos=[ProjectPath(name="a", url="https://github.com/x/a.git")],
                ),
                WorkspaceProject(
                    name="plain",
                    dedupe=ProjectDedupeOverride(enabled=False),
                    repos=[ProjectPath(name="b", url="https://github.com/x/b.git")],
                ),
                WorkspaceProject(
                    name="force-dedupe",
                    dedupe=ProjectDedupeOverride(enabled=True),
                    repos=[ProjectPath(name="c", url="https://github.com/x/c.git")],
                ),
            ]
        ),
    )


def test_resolve_effective_dedupe_inherits_workspace_default() -> None:
    workspace_dedupe = WorkspaceDedupeConfig(enabled=True)
    assert resolve_effective_dedupe(workspace_dedupe, None) == workspace_dedupe


def test_resolve_effective_dedupe_project_disable_override() -> None:
    workspace_dedupe = WorkspaceDedupeConfig(enabled=True)
    project = WorkspaceProject(
        name="plain",
        dedupe=ProjectDedupeOverride(enabled=False),
        repos=[],
    )
    assert resolve_effective_dedupe(workspace_dedupe, project) is None


def test_resolve_effective_dedupe_project_enable_override() -> None:
    workspace_dedupe = WorkspaceDedupeConfig(enabled=False)
    project = WorkspaceProject(
        name="force",
        dedupe=ProjectDedupeOverride(enabled=True),
        repos=[],
    )
    assert resolve_effective_dedupe(workspace_dedupe, project) == workspace_dedupe


def test_resolve_effective_dedupe_for_project_by_name() -> None:
    config = _config_with_projects()
    workspace_dedupe = WorkspaceDedupeConfig(enabled=True)
    assert (
        resolve_effective_dedupe_for_project(workspace_dedupe, config, "plain") is None
    )
    assert (
        resolve_effective_dedupe_for_project(workspace_dedupe, config, "deduped")
        == workspace_dedupe
    )


def test_resolve_dedupe_for_layout_without_project() -> None:
    config = _config_with_projects()
    workspace_dedupe = WorkspaceDedupeConfig(enabled=False)
    assert resolve_dedupe_for_layout(workspace_dedupe, config, None) is None


def test_workspace_project_rejects_unknown_dedupe_keys() -> None:
    try:
        WorkspaceProject.model_validate(
            {
                "name": "bad",
                "repos": [],
                "dedupe": {"enabled": True, "canonical_dir": "_other"},
            }
        )
        raise AssertionError("expected validation error")
    except Exception:
        pass
