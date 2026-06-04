#!/usr/bin/env python
"""
Tier-1 repo card assembly from workspace index rows and git inspect hints.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.context.models import RepoCardResult
from metagit.core.mcp.services.repo_git_stats import inspect_repo_state
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.agent_instructions import AgentInstructionsResolver
from metagit.core.workspace.models import WorkspaceProject


_STACK_FILENAMES: tuple[str, ...] = (
    "pyproject.toml",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "Dockerfile",
    "Taskfile.yml",
    "Makefile",
    "README.md",
)


def _tags_to_list(tags: Any) -> list[str]:
    """Flatten workspace manifest tag maps to stable repo-card strings."""
    if not isinstance(tags, dict) or not tags:
        return []
    return [f"{key}={value}" for key, value in sorted(tags.items())]


class RepoCardService:
    """Build ``RepoCardResult`` payloads for workspace repositories."""

    def __init__(self, index_service: Optional[WorkspaceIndexService] = None) -> None:
        self._index = index_service or WorkspaceIndexService()
        self._instructions = AgentInstructionsResolver()

    def build_one(
        self,
        config: MetagitConfig,
        workspace_root: str,
        project_name: str,
        repo_name: str,
        *,
        definition_root: str | None = None,
    ) -> RepoCardResult:
        """Produce a single repo card for ``project_name`` / ``repo_name``."""
        row = self._find_index_row(
            config,
            workspace_root,
            project_name,
            repo_name,
            definition_root=definition_root,
        )
        if row is None:
            raise ValueError(
                f"Unknown workspace repo '{project_name}/{repo_name}' in manifest",
            )
        project, repo_entry = self._locate_manifest_entries(
            config=config,
            project_name=project_name,
            repo_name=repo_name,
        )
        return self._build_from_row(config, row, project, repo_entry)

    def build_many(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        definition_root: str | None = None,
        project_name: Optional[str] = None,
        repo_name: Optional[str] = None,
        max_cards: int = 50,
    ) -> list[RepoCardResult]:
        """Produce up to ``max_cards`` repo cards with optional filtering."""
        rows = self._index.build_index(
            config=config,
            workspace_root=workspace_root,
            definition_root=definition_root or workspace_root,
        )
        filtered: list[dict[str, Any]] = []
        for row in rows:
            if project_name is not None and row["project_name"] != project_name:
                continue
            if repo_name is not None and row["repo_name"] != repo_name:
                continue
            filtered.append(row)
        cards: list[RepoCardResult] = []
        for row in filtered[:max_cards]:
            pname = str(row["project_name"])
            rname = str(row["repo_name"])
            proj, repo_entry = self._locate_manifest_entries(
                config=config,
                project_name=pname,
                repo_name=rname,
            )
            cards.append(self._build_from_row(config, row, proj, repo_entry))
        return cards

    def _build_from_row(
        self,
        config: MetagitConfig,
        row: dict[str, Any],
        project: Optional[WorkspaceProject],
        repo_entry: Optional[ProjectPath],
    ) -> RepoCardResult:
        repo_path = str(row["repo_path"])
        exists = bool(row["exists"])
        is_git_repo = bool(row["is_git_repo"])
        status = str(row["status"])
        inspected: dict[str, Any]
        if exists and is_git_repo:
            inspected = dict(inspect_repo_state(repo_path=repo_path))
        else:
            inspected = {}

        branch, dirty, ahead, behind, head_age_days = self._git_fields_from_inspect(
            inspected
        )

        url: Optional[str]
        description: Optional[str]
        manifest_tags_keyed: dict[str, str]
        if repo_entry:
            url_str = getattr(repo_entry, "url", None)
            url = str(url_str) if url_str else None
            description = repo_entry.description
            manifest_tags_keyed = dict(repo_entry.tags)
        else:
            url = row.get("url") if isinstance(row.get("url"), str) else None
            description = None
            raw_tags = row.get("tags")
            manifest_tags_keyed = dict(raw_tags) if isinstance(raw_tags, dict) else {}

        tags = _tags_to_list(manifest_tags_keyed)
        excerpt = self._agent_instructions_excerpt(config, project, repo_entry)

        stack = self._stack_hints(repo_path) if exists else []
        flags = self._health_flags(row=row, inspect_dict=inspected)

        return RepoCardResult(
            project_name=str(row["project_name"]),
            repo_name=str(row["repo_name"]),
            repo_path=repo_path,
            status=status,
            exists=exists,
            is_git_repo=is_git_repo,
            branch=branch,
            dirty=dirty,
            ahead=ahead,
            behind=behind,
            head_commit_age_days=head_age_days,
            tags=tags,
            url=url,
            description=description,
            agent_instructions_excerpt=excerpt,
            stack_hints=stack,
            health_flags=flags,
        )

    def _git_fields_from_inspect(
        self,
        inspected: dict[str, Any],
    ) -> tuple[str, bool, int, int, Optional[int]]:
        branch = ""
        dirty = False
        ahead = 0
        behind = 0
        head_age_days: Optional[int] = None
        if inspected.get("ok") is True:
            br = inspected.get("branch")
            branch = br if isinstance(br, str) else ""
            if inspected.get("dirty") is True:
                dirty = True
            a = inspected.get("ahead")
            if isinstance(a, int):
                ahead = max(a, 0)
            b = inspected.get("behind")
            if isinstance(b, int):
                behind = max(b, 0)
            raw_age = inspected.get("head_commit_age_days")
            if isinstance(raw_age, (int, float)):
                head_age_days = int(raw_age)
        return branch, dirty, ahead, behind, head_age_days

    def _find_index_row(
        self,
        config: MetagitConfig,
        workspace_root: str,
        project_name: str,
        repo_name: str,
        *,
        definition_root: str | None = None,
    ) -> Optional[dict[str, Any]]:
        rows = self._index.build_index(
            config=config,
            workspace_root=workspace_root,
            definition_root=definition_root or workspace_root,
        )
        for row in rows:
            if row["project_name"] == project_name and row["repo_name"] == repo_name:
                return row
        return None

    def _locate_manifest_entries(
        self,
        config: MetagitConfig,
        project_name: str,
        repo_name: str,
    ) -> tuple[Optional[WorkspaceProject], Optional[ProjectPath]]:
        if not config.workspace:
            return None, None
        for project in config.workspace.projects:
            if project.name != project_name:
                continue
            for repo_entry in project.repos:
                if repo_entry.name == repo_name:
                    return project, repo_entry
        return None, None

    def _agent_instructions_excerpt(
        self,
        config: MetagitConfig,
        project: Optional[WorkspaceProject],
        repo_entry: Optional[ProjectPath],
    ) -> Optional[str]:
        composition = self._instructions.resolve(
            config,
            project=project,
            repo=repo_entry,
        )
        text = composition.effective.strip()
        if text:
            return text[:500]
        if repo_entry and repo_entry.agent_instructions:
            return repo_entry.agent_instructions.strip()[:500]
        if project and project.agent_instructions:
            return project.agent_instructions.strip()[:500]
        return None

    def _stack_hints(self, repo_path: str) -> list[str]:
        root = repo_path
        found: list[str] = []
        for name in _STACK_FILENAMES:
            candidate = Path(os.path.join(root, name))
            if candidate.is_file():
                found.append(name)
        return found

    def _health_flags(
        self,
        *,
        row: dict[str, Any],
        inspect_dict: dict[str, Any],
    ) -> list[str]:
        flags: list[str] = []
        if row.get("exists") is False:
            flags.append("missing_clone")
        if inspect_dict.get("ok") is True and inspect_dict.get("dirty") is True:
            flags.append("dirty")
        behind_raw = inspect_dict.get("behind")
        behind = behind_raw if isinstance(behind_raw, int) else 0
        if behind > 0:
            flags.append("behind_remote")
        age_raw = inspect_dict.get("head_commit_age_days")
        age = age_raw if isinstance(age_raw, (int, float)) else None
        if age is not None and float(age) > 30:
            flags.append("stale_head_30d")
        return flags


__all__ = ["RepoCardService"]
