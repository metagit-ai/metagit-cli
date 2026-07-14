#!/usr/bin/env python
"""Layered skill inventory across workspace, project, and repo scopes."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.skills.installer import TARGET_PATHS
from metagit.core.workspace.agent_profile_models import AgentProfile
from metagit.core.workspace.root_resolver import resolve_definition_root


class SkillSurfaceEntry(BaseModel):
    """One skill observation at a scope."""

    skill_id: str
    scope: Literal["workspace", "project", "repo"]
    source: Literal["on_disk", "declared", "both"]
    path: Optional[str] = None
    vendor: Optional[str] = None
    project: Optional[str] = None
    repo: Optional[str] = None


class SkillSurfaceResult(BaseModel):
    """Layered skill inventory for agents."""

    ok: bool = True
    definition_root: str = ""
    workspace_root: str = ""
    entries: list[SkillSurfaceEntry] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


def _skill_dirs_under(root: Path) -> list[tuple[str, Path]]:
    """Return (vendor, skills_dir) pairs that exist under root."""
    found: list[tuple[str, Path]] = []
    for vendor, paths in TARGET_PATHS.items():
        candidate = root / paths.project_skills_path
        if candidate.is_dir():
            found.append((vendor, candidate))
    return found


def _list_skill_ids(skills_dir: Path) -> list[str]:
    """List skill directory names under a vendor skills root."""
    return sorted(item.name for item in skills_dir.iterdir() if item.is_dir() and (item / "SKILL.md").exists())


def _declared_skills(profile: Optional[AgentProfile]) -> list[str]:
    """Return declared skill ids from an agent_profile block."""
    if profile is None:
        return []
    return list(profile.skills)


class SkillSurfaceService:
    """Discover on-disk and declared skills for a workspace ladder."""

    def __init__(self, index_service: Optional[WorkspaceIndexService] = None) -> None:
        self._index = index_service or WorkspaceIndexService()

    def inventory(
        self,
        config: MetagitConfig,
        config_path: str,
        workspace_root: str,
        *,
        project_name: Optional[str] = None,
        repo_name: Optional[str] = None,
    ) -> SkillSurfaceResult:
        """Build a layered skill map for the workspace (optionally scoped)."""
        definition_root = resolve_definition_root(config_path)
        entries: list[SkillSurfaceEntry] = []

        # Workspace / manifest root
        entries.extend(
            self._scan_root(
                Path(definition_root),
                scope="workspace",
                declared=_declared_skills(config.workspace.agent_profile if config.workspace else None),
            )
        )

        if not config.workspace:
            return self._result(definition_root, workspace_root, entries)

        index_rows = self._index.build_index(
            config=config,
            workspace_root=workspace_root,
            definition_root=definition_root,
        )
        index_by_key = {(row["project_name"], row["repo_name"]): row for row in index_rows}

        for project in config.workspace.projects:
            if project_name and project.name != project_name:
                continue
            # Project-level declared profile (no dedicated on-disk project skills root)
            for skill_id in _declared_skills(project.agent_profile):
                entries.append(
                    SkillSurfaceEntry(
                        skill_id=skill_id,
                        scope="project",
                        source="declared",
                        project=project.name,
                    )
                )
            for repo in project.repos:
                if repo_name and repo.name != repo_name:
                    continue
                row = index_by_key.get((project.name, repo.name), {})
                repo_path = row.get("repo_path")
                declared = _declared_skills(repo.agent_profile)
                if repo_path and Path(repo_path).is_dir():
                    entries.extend(
                        self._scan_root(
                            Path(repo_path),
                            scope="repo",
                            declared=declared,
                            project=project.name,
                            repo=repo.name,
                        )
                    )
                else:
                    for skill_id in declared:
                        entries.append(
                            SkillSurfaceEntry(
                                skill_id=skill_id,
                                scope="repo",
                                source="declared",
                                project=project.name,
                                repo=repo.name,
                            )
                        )

        return self._result(definition_root, workspace_root, entries)

    def _scan_root(
        self,
        root: Path,
        *,
        scope: Literal["workspace", "project", "repo"],
        declared: list[str],
        project: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> list[SkillSurfaceEntry]:
        """Merge on-disk vendor skills with declared ids at one root."""
        on_disk: dict[str, tuple[str, str]] = {}
        for vendor, skills_dir in _skill_dirs_under(root):
            for skill_id in _list_skill_ids(skills_dir):
                on_disk[skill_id] = (vendor, str(skills_dir / skill_id))

        declared_set = set(declared)
        disk_set = set(on_disk)
        entries: list[SkillSurfaceEntry] = []
        for skill_id in sorted(disk_set | declared_set):
            if skill_id in disk_set and skill_id in declared_set:
                source: Literal["on_disk", "declared", "both"] = "both"
            elif skill_id in disk_set:
                source = "on_disk"
            else:
                source = "declared"
            vendor = on_disk[skill_id][0] if skill_id in on_disk else None
            path = on_disk[skill_id][1] if skill_id in on_disk else None
            entries.append(
                SkillSurfaceEntry(
                    skill_id=skill_id,
                    scope=scope,
                    source=source,
                    path=path,
                    vendor=vendor,
                    project=project,
                    repo=repo,
                )
            )
        return entries

    def _result(
        self,
        definition_root: str,
        workspace_root: str,
        entries: list[SkillSurfaceEntry],
    ) -> SkillSurfaceResult:
        """Attach summary counts."""
        counts = {
            "total": len(entries),
            "on_disk": sum(1 for e in entries if e.source in {"on_disk", "both"}),
            "declared": sum(1 for e in entries if e.source in {"declared", "both"}),
            "workspace": sum(1 for e in entries if e.scope == "workspace"),
            "project": sum(1 for e in entries if e.scope == "project"),
            "repo": sum(1 for e in entries if e.scope == "repo"),
        }
        return SkillSurfaceResult(
            ok=True,
            definition_root=definition_root,
            workspace_root=workspace_root,
            entries=entries,
            counts=counts,
        )
