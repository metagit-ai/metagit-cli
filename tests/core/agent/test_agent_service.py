#!/usr/bin/env python
"""Tests for AgentService."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from metagit.core.agent.registry import AgentTemplateRegistry
from metagit.core.agent.service import AgentService


def test_registry_lists_orchestration_overseer() -> None:
    registry = AgentTemplateRegistry()
    templates = registry.list_templates()
    ids = [item.id for item in templates]
    assert "orchestration-overseer" in ids


def test_export_orchestration_overseer_no_prompt(tmp_path: Path) -> None:
    service = AgentService()
    result = service.export(
        "orchestration-overseer",
        tmp_path,
        directory_name="coord",
        git_remote_url=None,
        answers={
            "workspace_name": "test-workspace",
            "manifest_path": ".metagit.yml",
            "coordinator_description": "Test coordinator.",
        },
        no_prompt=True,
    )
    assert len(result.paths) == 3
    agent_file = tmp_path / "orchestration-overseer.md"
    manifest_file = tmp_path / "manifest.json"
    assert agent_file.is_file()
    assert manifest_file.is_file()
    content = agent_file.read_text(encoding="utf-8")
    assert "name: orchestration-overseer" in content
    assert "test-workspace" in content
    assert "graph-discover" in content
    assert "secretzero" in content.lower()


def test_create_writes_claude_code_agent(tmp_path: Path) -> None:
    service = AgentService()
    write_result, install_results = service.create(
        "orchestration-overseer",
        vendor="claude_code",
        scope="project",
        project_root=tmp_path,
        directory_name="coord",
        git_remote_url=None,
        answers={
            "workspace_name": "coord",
            "manifest_path": ".metagit.yml",
            "coordinator_description": "Coordinator.",
        },
        no_prompt=True,
        install_skills=True,
        dry_run=True,
    )
    assert write_result.vendor == "claude_code"
    assert write_result.dry_run is True
    expected = tmp_path / ".claude" / "agents" / "orchestration-overseer.md"
    assert write_result.paths == [str(expected)]
    assert install_results


def test_create_refuses_overwrite_without_force(tmp_path: Path) -> None:
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    existing = agents_dir / "orchestration-overseer.md"
    existing.write_text("existing", encoding="utf-8")
    service = AgentService()
    with pytest.raises(Exception) as exc_info:
        service.create(
            "orchestration-overseer",
            vendor="claude_code",
            scope="project",
            project_root=tmp_path,
            directory_name="coord",
            git_remote_url=None,
            answers={
                "workspace_name": "coord",
                "manifest_path": ".metagit.yml",
                "coordinator_description": "Coordinator.",
            },
            no_prompt=True,
        )
    assert "overwrite" in str(exc_info.value).lower()


def test_create_hermes_installs_skill(tmp_path: Path) -> None:
    service = AgentService()
    write_result, _ = service.create(
        "orchestration-overseer",
        vendor="hermes",
        scope="project",
        project_root=tmp_path,
        directory_name="coord",
        git_remote_url=None,
        answers={
            "workspace_name": "coord",
            "manifest_path": ".metagit.yml",
            "coordinator_description": "Coordinator.",
        },
        no_prompt=True,
    )
    expected = (
        tmp_path / ".hermes" / "skills" / "orchestration-overseer" / "SKILL.md"
    )
    assert write_result.paths == [str(expected)]
    assert expected.is_file()
    content = expected.read_text(encoding="utf-8")
    assert "name: orchestration-overseer" in content


def test_create_opencode_uses_subagent_frontmatter(tmp_path: Path) -> None:
    service = AgentService()
    write_result, _ = service.create(
        "orchestration-overseer",
        vendor="opencode",
        scope="project",
        project_root=tmp_path,
        directory_name="coord",
        git_remote_url=None,
        answers={
            "workspace_name": "coord",
            "manifest_path": ".metagit.yml",
            "coordinator_description": "Coordinator.",
        },
        no_prompt=True,
    )
    agent_file = tmp_path / ".opencode" / "agents" / "orchestration-overseer.md"
    assert write_result.paths == [str(agent_file)]
    content = agent_file.read_text(encoding="utf-8")
    assert "mode: subagent" in content


def test_create_cursor_agent(tmp_path: Path) -> None:
    service = AgentService()
    write_result, _ = service.create(
        "orchestration-overseer",
        vendor="cursor",
        scope="project",
        project_root=tmp_path,
        directory_name="coord",
        git_remote_url=None,
        answers={
            "workspace_name": "coord",
            "manifest_path": ".metagit.yml",
            "coordinator_description": "Coordinator.",
        },
        no_prompt=True,
    )
    agent_file = tmp_path / ".cursor" / "agents" / "orchestration-overseer.md"
    assert write_result.paths == [str(agent_file)]
    assert "@orchestration-overseer" in agent_file.read_text(encoding="utf-8")


def test_create_github_copilot_agent(tmp_path: Path) -> None:
    service = AgentService()
    write_result, _ = service.create(
        "orchestration-overseer",
        vendor="github_copilot",
        scope="project",
        project_root=tmp_path,
        directory_name="coord",
        git_remote_url=None,
        answers={
            "workspace_name": "coord",
            "manifest_path": ".metagit.yml",
            "coordinator_description": "Coordinator.",
        },
        no_prompt=True,
    )
    agent_file = tmp_path / ".github" / "agents" / "orchestration-overseer.agent.md"
    assert write_result.paths == [str(agent_file)]
    content = agent_file.read_text(encoding="utf-8")
    assert "description:" in content
    assert "tools:" in content


def test_create_windsurf_installs_skill(tmp_path: Path) -> None:
    service = AgentService()
    write_result, _ = service.create(
        "orchestration-overseer",
        vendor="windsurf",
        scope="project",
        project_root=tmp_path,
        directory_name="coord",
        git_remote_url=None,
        answers={
            "workspace_name": "coord",
            "manifest_path": ".metagit.yml",
            "coordinator_description": "Coordinator.",
        },
        no_prompt=True,
    )
    expected = (
        tmp_path / ".windsurf" / "skills" / "orchestration-overseer" / "SKILL.md"
    )
    assert write_result.paths == [str(expected)]
    assert expected.is_file()


def test_create_codex_installs_skill(tmp_path: Path) -> None:
    service = AgentService()
    write_result, _ = service.create(
        "orchestration-overseer",
        vendor="codex",
        scope="project",
        project_root=tmp_path,
        directory_name="coord",
        git_remote_url=None,
        answers={
            "workspace_name": "coord",
            "manifest_path": ".metagit.yml",
            "coordinator_description": "Coordinator.",
        },
        no_prompt=True,
    )
    expected = tmp_path / ".agents" / "skills" / "orchestration-overseer" / "SKILL.md"
    assert write_result.paths == [str(expected)]
    assert expected.is_file()


def test_unknown_template_raises() -> None:
    service = AgentService()
    with pytest.raises(Exception) as exc_info:
        service.export(
            "not-a-template",
            Path("."),
            directory_name="x",
            git_remote_url=None,
            no_prompt=True,
        )
    assert "Unknown agent template" in str(exc_info.value)
