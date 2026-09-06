#!/usr/bin/env python
"""Tests for component structural validation."""

from __future__ import annotations

from pathlib import Path

from metagit.core.component.models import Component, ComponentRef
from metagit.core.config.component_validation import validate_components
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.agent_profile_models import AgentProfile
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _umbrella(*components: Component, repo_path: str = "./platform") -> MetagitConfig:
    return MetagitConfig(
        name="acme",
        kind="umbrella",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[
                        ProjectPath(
                            name="core",
                            path=repo_path,
                            components=list(components),
                        )
                    ],
                )
            ]
        ),
    )


def test_valid_nested_components_have_no_issues(tmp_path: Path) -> None:
    issues = validate_components(
        _umbrella(
            Component(name="web", path="apps/web"),
            Component(name="auth", path="apps/web/packages/auth"),
        ),
        definition_root=tmp_path,
    )
    assert issues == []


def test_duplicate_name_is_invalid(tmp_path: Path) -> None:
    issues = validate_components(
        _umbrella(
            Component(name="web", path="apps/web"),
            Component(name="web", path="apps/other"),
        ),
        definition_root=tmp_path,
    )
    assert any("duplicate" in item.lower() and "web" in item for item in issues)


def test_duplicate_normalized_path_is_invalid(tmp_path: Path) -> None:
    issues = validate_components(
        _umbrella(
            Component(name="web", path="apps/web"),
            Component(name="frontend", path="apps//web/"),
        ),
        definition_root=tmp_path,
    )
    assert any("duplicate" in item.lower() and "path" in item.lower() for item in issues)


def test_escaping_path_is_invalid(tmp_path: Path) -> None:
    issues = validate_components(
        _umbrella(Component(name="web", path="../outside")),
        definition_root=tmp_path,
    )
    assert any("escape" in item.lower() for item in issues)


def test_unknown_same_repo_depends_on(tmp_path: Path) -> None:
    issues = validate_components(
        _umbrella(Component(name="web", path="apps/web", depends_on=["auth"])),
        definition_root=tmp_path,
    )
    assert any("unknown" in item.lower() and "auth" in item for item in issues)


def test_cross_repo_depends_on_is_not_existence_checked(tmp_path: Path) -> None:
    issues = validate_components(
        _umbrella(
            Component(
                name="web",
                path="apps/web",
                depends_on=[ComponentRef(project="other", repo="svc", component="auth")],
            )
        ),
        definition_root=tmp_path,
    )
    assert issues == []


def test_same_repo_cycle_is_invalid(tmp_path: Path) -> None:
    issues = validate_components(
        _umbrella(
            Component(name="web", path="apps/web", depends_on=["api"]),
            Component(name="api", path="apps/api", depends_on=["web"]),
        ),
        definition_root=tmp_path,
    )
    assert any("cycle" in item.lower() for item in issues)


def test_missing_directory_fails_when_repo_exists(tmp_path: Path) -> None:
    repo = tmp_path / "platform"
    repo.mkdir()
    issues = validate_components(
        _umbrella(Component(name="web", path="apps/web"), repo_path="./platform"),
        definition_root=tmp_path,
    )
    assert any("does not exist" in item.lower() or "not found" in item.lower() for item in issues)


def test_missing_directory_skipped_when_repo_uncloned(tmp_path: Path) -> None:
    issues = validate_components(
        _umbrella(Component(name="web", path="apps/web"), repo_path="./platform"),
        definition_root=tmp_path,
    )
    assert issues == []


def test_existing_component_directory_passes(tmp_path: Path) -> None:
    (tmp_path / "platform" / "apps" / "web").mkdir(parents=True)
    issues = validate_components(
        _umbrella(Component(name="web", path="apps/web"), repo_path="./platform"),
        definition_root=tmp_path,
    )
    assert issues == []


def test_invalid_component_agent_profile_skill(tmp_path: Path) -> None:
    from metagit.core.agent.profile_service import AgentProfileService

    config = _umbrella(
        Component(
            name="web",
            path="apps/web",
            agent_profile=AgentProfile(skills=["definitely-not-a-real-skill"]),
        )
    )
    service = AgentProfileService(config=config, definition_root=tmp_path)
    issues = service.list_validation_issues()
    assert issues
    assert issues[0].scope == "component"
    assert issues[0].component == "web"
    assert "unknown skill" in issues[0].message
