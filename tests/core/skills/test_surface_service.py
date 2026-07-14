#!/usr/bin/env python
"""Tests for SkillSurfaceService."""

from __future__ import annotations

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.skills.surface_service import SkillSurfaceService
from metagit.core.workspace.models import Workspace, WorkspaceProject


def test_skill_surface_merges_declared_and_on_disk(tmp_path: Path) -> None:
  definition = tmp_path / "manifest"
  definition.mkdir()
  config_path = definition / ".metagit.yml"
  config_path.write_text("name: demo\n", encoding="utf-8")

  workspace_skills = definition / ".cursor" / "skills" / "ws-skill"
  workspace_skills.mkdir(parents=True)
  (workspace_skills / "SKILL.md").write_text("# ws\n", encoding="utf-8")

  sync_root = tmp_path / "sync"
  repo_mount = sync_root / "portfolio" / "api"
  repo_skill = repo_mount / ".claude" / "skills" / "api-skill"
  repo_skill.mkdir(parents=True)
  (repo_skill / "SKILL.md").write_text("# api\n", encoding="utf-8")

  config = MetagitConfig(
    name="demo",
    workspace=Workspace(
      agent_profile={"skills": ["metagit-cli", "ws-skill"]},
      projects=[
        WorkspaceProject(
          name="portfolio",
          agent_profile={"skills": ["metagit-projects"]},
          repos=[
            ProjectPath(
              name="api",
              url="https://github.com/example/api.git",
              agent_profile={"skills": ["api-skill", "metagit-cli"]},
            )
          ],
        )
      ],
    ),
  )

  result = SkillSurfaceService().inventory(
    config,
    str(config_path),
    str(sync_root),
  )
  assert result.ok is True
  by_id = {(e.skill_id, e.scope): e for e in result.entries}
  assert by_id[("ws-skill", "workspace")].source == "both"
  assert by_id[("metagit-cli", "workspace")].source == "declared"
  assert by_id[("metagit-projects", "project")].source == "declared"
  assert by_id[("api-skill", "repo")].source == "both"
  assert result.counts["total"] >= 4
