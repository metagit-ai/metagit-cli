#!/usr/bin/env python
"""Tests for metagit prompt emission service."""

from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.prompt.catalog import is_kind_allowed, list_catalog
from metagit.core.prompt.service import PromptService, PromptServiceError
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _sample_config() -> MetagitConfig:
    return MetagitConfig(
        name="ws",
        agent_instructions="File rules.",
        workspace=Workspace(
            agent_instructions="Workspace rules.",
            projects=[
                WorkspaceProject(
                    name="alpha",
                    agent_instructions="Project rules.",
                    repos=[
                        ProjectPath(
                            name="api",
                            path="alpha/api",
                            agent_instructions="Repo rules.",
                        )
                    ],
                )
            ],
        ),
    )


def test_catalog_lists_instructions_kind() -> None:
    kinds = [entry.kind for entry in list_catalog()]
    assert "instructions" in kinds
    assert "session-start" in kinds
    assert "context-pack" in kinds


def test_emit_context_pack_workspace() -> None:
    result = PromptService().emit(
        _sample_config(),
        kind="context-pack",
        scope="workspace",
        definition_path="/tmp/.metagit.yml",
        workspace_root="/tmp/sync",
        include_instructions=False,
    )
    assert result.ok
    assert "metagit context pack --tier 0" in result.text
    assert "metagit_context_pack" in result.text
    assert "tier 1" in result.text.lower()
    assert "token" in result.text.lower()


def test_emit_instructions_workspace() -> None:
    result = PromptService().emit(
        _sample_config(),
        kind="instructions",
        scope="workspace",
        definition_path="/tmp/.metagit.yml",
        workspace_root="/tmp/sync",
    )
    assert result.ok
    assert "[FILE]" in result.text
    assert "[WORKSPACE]" in result.text
    assert "[PROJECT]" not in result.text


def test_emit_instructions_repo() -> None:
    result = PromptService().emit(
        _sample_config(),
        kind="instructions",
        scope="repo",
        definition_path="/tmp/.metagit.yml",
        workspace_root="/tmp/sync",
        project_name="alpha",
        repo_name="api",
    )
    assert len(result.instruction_layers) == 4
    assert "Repo rules." in result.text


def test_emit_session_start_includes_manifest_when_requested() -> None:
    result = PromptService().emit(
        _sample_config(),
        kind="session-start",
        scope="workspace",
        definition_path="/tmp/.metagit.yml",
        workspace_root="/tmp/sync",
        include_instructions=True,
    )
    assert "metagit workspace list" in result.text
    assert "[FILE]" in result.text


def test_emit_repo_enrich_includes_detect_commands() -> None:
    result = PromptService().emit(
        _sample_config(),
        kind="repo-enrich",
        scope="repo",
        definition_path="/tmp/.metagit.yml",
        workspace_root="/tmp/sync",
        project_name="alpha",
        repo_name="api",
        include_instructions=False,
    )
    assert "metagit detect repository" in result.text
    assert "merge" in result.text.lower()
    assert result.project_name == "alpha"
    assert result.repo_name == "api"


def test_kind_not_allowed_for_scope() -> None:
    try:
        PromptService().emit(
            _sample_config(),
            kind="session-start",
            scope="repo",
            definition_path="/tmp/.metagit.yml",
            workspace_root="/tmp/sync",
            project_name="alpha",
            repo_name="api",
        )
        raise AssertionError("expected PromptServiceError")
    except PromptServiceError:
        pass
    assert not is_kind_allowed("session-start", "repo")
