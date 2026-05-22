#!/usr/bin/env python
"""
Unit tests for metagit.core.context.models (context packs T0/T1 shapes).

Uses basename ``test_context_pack_models`` to avoid pytest import clashes with
``tests/core/mcp/test_models.py``.
"""

from metagit.core.context.models import (
  ContextPackResult,
  RepoCardResult,
  WorkspaceMapEntry,
  WorkspaceMapProject,
  WorkspaceMapResult,
)


def test_workspace_map_entry_optional_tags_omitted() -> None:
  entry = WorkspaceMapEntry(
    project_name="personal",
    repo_name="metagit-cli",
    repo_path="/w/personal/metagit-cli",
    status="cloned",
    exists=True,
  )
  assert entry.tags is None
  dumped = entry.model_dump(mode="python")
  assert dumped["tags"] is None


def test_workspace_map_entry_with_tags() -> None:
  entry = WorkspaceMapEntry(
    project_name="personal",
    repo_name="metagit-cli",
    repo_path="/w/personal/metagit-cli",
    status="cloned",
    exists=True,
    tags=["focus", "python"],
  )
  assert entry.tags == ["focus", "python"]


def test_workspace_map_result_tier_zero_defaults() -> None:
  proj = WorkspaceMapProject(name="personal", repo_count=2)
  repos = [
    WorkspaceMapEntry(
      project_name="personal",
      repo_name="metagit-cli",
      repo_path="/w/personal/metagit-cli",
      status="cloned",
      exists=True,
    )
  ]
  result = WorkspaceMapResult(
    workspace_name="default",
    workspace_root="/workspace",
    config_path="/workspace/.metagit.yml",
    project_count=1,
    repo_count=1,
    projects=[proj],
    repos=repos,
  )
  assert result.tier == 0
  assert result.active_project is None
  assert isinstance(result.projects[0], WorkspaceMapProject)
  roundtrip = WorkspaceMapResult.model_validate(result.model_dump(mode="python"))
  assert roundtrip == result


def test_workspace_map_result_active_project() -> None:
  result = WorkspaceMapResult(
    workspace_name="default",
    workspace_root="/workspace",
    config_path="/workspace/.metagit.yml",
    project_count=0,
    repo_count=0,
    projects=[],
    repos=[],
    active_project="personal",
  )
  assert result.active_project == "personal"


def test_workspace_map_project_description_optional() -> None:
  proj = WorkspaceMapProject(name="personal", repo_count=3)
  assert proj.description is None
  proj2 = WorkspaceMapProject(
    name="personal",
    repo_count=3,
    description="Home lab",
  )
  assert proj2.description == "Home lab"


def test_repo_card_result_tier_one_and_lists() -> None:
  card = RepoCardResult(
    project_name="personal",
    repo_name="metagit-cli",
    repo_path="/w/personal/metagit-cli",
    status="cloned",
    exists=True,
    is_git_repo=True,
    branch="feat/context-packs",
    dirty=True,
    ahead=1,
    behind=2,
    head_commit_age_days=12,
    tags=["cli"],
    url="https://github.com/example/metagit-cli",
    description="Toolkit",
    agent_instructions_excerpt="Do X.",
    stack_hints=["pyproject.toml", "package.json"],
    health_flags=["dirty", "behind_remote"],
  )
  assert card.tier == 1
  assert card.stack_hints[:2] == ["pyproject.toml", "package.json"]
  cloned = RepoCardResult.model_validate_json(card.model_dump_json())
  assert cloned == card


def test_repo_card_result_optional_manifest_and_age() -> None:
  card = RepoCardResult(
    project_name="personal",
    repo_name="fork",
    repo_path="/w/personal/fork",
    status="missing",
    exists=False,
    is_git_repo=False,
    branch="",
    dirty=False,
    ahead=0,
    behind=0,
    tags=[],
  )
  assert card.head_commit_age_days is None
  assert card.url is None
  assert card.description is None
  assert card.agent_instructions_excerpt is None


def test_context_pack_result_defaults_tier_zero_map() -> None:
  wm = WorkspaceMapResult(
    workspace_name="default",
    workspace_root="/workspace",
    config_path="/workspace/.metagit.yml",
    project_count=0,
    repo_count=0,
    projects=[],
    repos=[],
  )
  pack = ContextPackResult(
    tier=0,
    workspace_name="default",
    map=wm,
  )
  assert pack.ok is True
  assert pack.cards is None
  assert pack.token_estimate is None
  assert pack.map is not None
  assert pack.map.tier == 0


def test_context_pack_result_tier_one_cards() -> None:
  pack = ContextPackResult(
    tier=1,
    workspace_name="default",
    cards=[],
    token_estimate=100,
  )
  assert pack.map is None
  assert pack.cards == []
  assert pack.token_estimate == 100
