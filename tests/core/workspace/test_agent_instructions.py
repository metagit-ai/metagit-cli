#!/usr/bin/env python
"""
Unit tests for metagit.core.workspace.agent_instructions
"""

from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.agent_instructions import AgentInstructionsResolver
from metagit.core.workspace.models import Workspace, WorkspaceProject


def test_file_level_instructions_without_workspace_block() -> None:
    config = MetagitConfig(
        name="standalone",
        agent_instructions="Controller rules at file scope.",
        workspace=None,
    )
    result = AgentInstructionsResolver().resolve(config)
    assert len(result.layers) == 1
    assert result.layers[0].layer == "file"
    assert "Controller rules" in result.effective


def test_legacy_agent_prompt_alias_on_load() -> None:
    config = MetagitConfig.model_validate(
        {
            "name": "legacy",
            "agent_prompt": "From deprecated key.",
            "workspace": {
                "projects": [
                    {
                        "name": "p1",
                        "repos": [],
                        "agent_prompt": "Project legacy.",
                    }
                ],
                "agent_prompt": "Workspace legacy.",
            },
        }
    )
    assert config.agent_instructions == "From deprecated key."
    assert config.workspace is not None
    assert config.workspace.agent_instructions == "Workspace legacy."
    assert config.workspace.projects[0].agent_instructions == "Project legacy."


def test_compose_all_layers_including_repo() -> None:
    config = MetagitConfig(
        name="ws",
        agent_instructions="File layer.",
        workspace=Workspace(
            agent_instructions="Workspace layer.",
            projects=[
                WorkspaceProject(
                    name="alpha",
                    agent_instructions="Project layer.",
                    repos=[
                        ProjectPath(
                            name="api",
                            path="alpha/api",
                            agent_instructions="Repo layer.",
                        )
                    ],
                )
            ],
        ),
    )
    project = config.workspace.projects[0]
    repo = project.repos[0]
    result = AgentInstructionsResolver().resolve(config, project=project, repo=repo)
    assert [layer.layer for layer in result.layers] == [
        "file",
        "workspace",
        "project",
        "repo",
    ]
    assert "[FILE]" in result.effective
    assert "[REPO]" in result.effective
    assert "Repo layer." in result.effective
