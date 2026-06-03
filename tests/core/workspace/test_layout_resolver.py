#!/usr/bin/env python
"""Tests for workspace layout resolver helpers."""

from metagit.core.config.models import MetagitConfig
from metagit.core.workspace.layout_resolver import (
    active_project_resolution_error,
    list_project_names,
    project_exists_in_manifest,
    require_active_project_name,
    resolve_active_project_name,
)
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _config_with_projects(*names: str) -> MetagitConfig:
    return MetagitConfig(
        name="test",
        workspace=Workspace(
            projects=[WorkspaceProject(name=name, repos=[]) for name in names]
        ),
    )


def test_list_project_names_empty_without_workspace() -> None:
    config = MetagitConfig(name="test", workspace=None)
    assert list_project_names(config) == []


def test_minimal_metagit_config_has_no_synthetic_workspace() -> None:
    config = MetagitConfig(name="test")
    assert config.workspace is None


def test_resolve_active_project_prefers_explicit() -> None:
    config = _config_with_projects("alpha", "beta")
    assert (
        resolve_active_project_name(
            config,
            explicit="beta",
            default_project="platform",
        )
        == "beta"
    )


def test_resolve_active_project_uses_preference_when_present() -> None:
    config = _config_with_projects("platform", "other")
    assert (
        resolve_active_project_name(config, default_project="platform") == "platform"
    )


def test_resolve_active_project_falls_back_to_single_project() -> None:
    config = _config_with_projects("remote")
    assert resolve_active_project_name(config, default_project="default") == "remote"


def test_resolve_active_project_returns_local_without_workspace_projects() -> None:
    config = MetagitConfig(name="test", workspace=None)
    assert resolve_active_project_name(config) == "local"


def test_resolve_active_project_unresolved_when_multiple_without_preference() -> None:
    config = _config_with_projects("alpha", "beta")
    assert resolve_active_project_name(config) is None


def test_require_active_project_name_raises_for_multiple_projects() -> None:
    config = _config_with_projects("alpha", "beta")
    try:
        require_active_project_name(config)
    except ValueError as exc:
        assert "alpha" in str(exc)
        assert "beta" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_active_project_resolution_error_for_empty_workspace() -> None:
    config = MetagitConfig(name="test", workspace=Workspace(projects=[]))
    assert "metagit project add" in active_project_resolution_error(config)


def test_project_exists_in_manifest() -> None:
    config = _config_with_projects("remote")
    assert project_exists_in_manifest(config, "remote") is True
    assert project_exists_in_manifest(config, "default") is False
