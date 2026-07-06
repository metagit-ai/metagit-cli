#!/usr/bin/env python
"""Unit tests for agent_profile merge and validation."""

from __future__ import annotations

from pathlib import Path

from metagit.core.workspace.agent_profile_models import AgentProfile
from metagit.core.agent.profile_service import AgentProfileService
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _sample_config() -> MetagitConfig:
    return MetagitConfig(
        name="ws",
        workspace=Workspace(
            agent_profile=AgentProfile(skills=["metagit-cli"], mcp=["metagit"]),
            projects=[
                WorkspaceProject(
                    name="demo",
                    agent_profile=AgentProfile(
                        skills=["metagit-context-pack"],
                        inherit=True,
                    ),
                    repos=[
                        ProjectPath(
                            name="alpha",
                            path="./",
                            agent_profile=AgentProfile(
                                tier="full",
                                inherit=False,
                                skills=["metagit-workspace-scope"],
                            ),
                        ),
                    ],
                ),
            ],
        ),
    )


def test_effective_profile_child_override_without_inherit() -> None:
    config = _sample_config()
    service = AgentProfileService(config=config, definition_root=Path("."))
    effective = service.effective_profile(project_name="demo", repo_name="alpha")
    assert effective is not None
    assert effective.tier == "full"
    assert effective.skills == ["metagit-workspace-scope"]
    assert effective.mcp == []


def test_effective_profile_inheritance_merge() -> None:
    config = _sample_config()
    repo = config.workspace.projects[0].repos[0]
    repo.agent_profile = AgentProfile(
        tier="full",
        skills=["metagit-workspace-scope"],
        inherit=True,
    )
    service = AgentProfileService(config=config, definition_root=Path("."))
    effective = service.effective_profile(project_name="demo", repo_name="alpha")
    assert effective is not None
    assert "metagit-cli" in effective.skills
    assert "metagit-context-pack" in effective.skills
    assert "metagit-workspace-scope" in effective.skills
    assert effective.mcp == ["metagit"]


def test_profile_validation_unknown_skill() -> None:
    config = _sample_config()
    config.workspace.projects[0].repos[0].agent_profile = AgentProfile(
        skills=["definitely-not-a-real-skill"],
    )
    service = AgentProfileService(config=config, definition_root=Path("."))
    issues = service.list_validation_issues()
    assert issues
    assert "unknown skill" in issues[0].message
