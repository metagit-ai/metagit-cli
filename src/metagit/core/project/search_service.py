#!/usr/bin/env python
"""
Search and resolve managed workspace repositories from `.metagit.yml` only.
"""

from typing import Any

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.project.search_models import (
    ManagedRepoError,
    ManagedRepoMatch,
    ManagedRepoResolveResult,
    ManagedRepoSearchResult,
    ManagedRepoStatus,
)


class ManagedRepoSearchService:
    """Match queries against configured workspace repos using WorkspaceIndexService rows."""

    def __init__(self) -> None:
        self._index = WorkspaceIndexService()

    def search(
        self,
        config: MetagitConfig,
        workspace_root: str,
        query: str,
        *,
        project: str | None = None,
        exact: bool = False,
        synced_only: bool = False,
        tags: dict[str, str] | None = None,
        limit: int = 10,
    ) -> ManagedRepoSearchResult:
        """Return ranked matches for a free-text query and optional filters."""
        rows = self._index.build_index(config=config, workspace_root=workspace_root)
        matches: list[ManagedRepoMatch] = []
        for row in rows:
            if project and row["project_name"] != project:
                continue
            if synced_only and row["status"] != "synced":
                continue
            row_tags = row.get("tags") or {}
            if tags and any(row_tags.get(key) != value for key, value in tags.items()):
                continue
            score, reasons = self._match_row(row=row, query=query, exact=exact)
            if score <= 0:
                continue
            matches.append(self._to_match(row=row, score=score, reasons=reasons))
        matches.sort(key=lambda item: (-item.score, item.project_name, item.repo_name))
        return ManagedRepoSearchResult(query=query, matches=matches[:limit])

    def resolve_one(
        self,
        config: MetagitConfig,
        workspace_root: str,
        query: str,
        *,
        project: str | None = None,
        exact: bool = False,
        synced_only: bool = True,
        tags: dict[str, str] | None = None,
    ) -> ManagedRepoResolveResult:
        """Return a single best match or a structured not_found / ambiguous error."""
        result = self.search(
            config=config,
            workspace_root=workspace_root,
            query=query,
            project=project,
            exact=exact,
            synced_only=synced_only,
            tags=tags,
            limit=25,
        )
        if not result.matches:
            return ManagedRepoResolveResult(
                error=ManagedRepoError(
                    kind="not_found",
                    message="No managed repository matched the query.",
                )
            )
        if len(result.matches) > 1:
            return ManagedRepoResolveResult(
                error=ManagedRepoError(
                    kind="ambiguous_match",
                    message="Search matched more than one managed repository.",
                    matches=result.matches,
                )
            )
        return ManagedRepoResolveResult(match=result.matches[0])

    def _to_match(
        self,
        *,
        row: dict[str, Any],
        score: int,
        reasons: list[str],
    ) -> ManagedRepoMatch:
        status = ManagedRepoStatus(
            resolved_path=row["repo_path"],
            exists=row["exists"],
            is_git_repo=row["is_git_repo"],
            sync_enabled=bool(row["sync"]),
            status=row["status"],
        )
        return ManagedRepoMatch(
            project_name=row["project_name"],
            repo_name=row["repo_name"],
            url=row.get("url"),
            configured_path=row.get("configured_path"),
            tags=dict(row.get("tags") or {}),
            status=status,
            match_reasons=list(reasons),
            score=score,
        )

    def _match_row(
        self, *, row: dict[str, Any], query: str, exact: bool
    ) -> tuple[int, list[str]]:
        reasons: list[str] = []
        q = query.strip()
        if not q:
            return 0, []
        name = row.get("repo_name") or ""
        if exact:
            if name == q:
                return 100, ["repo_name:exact"]
            return 0, []
        score = 0
        q_lower = q.lower()
        name_lower = name.lower()
        if name_lower == q_lower:
            score += 100
            reasons.append("repo_name:exact")
        elif q_lower in name_lower:
            score += 60
            reasons.append("repo_name:substring")
        url = row.get("url") or ""
        if url and q_lower in str(url).lower():
            score += 30
            reasons.append("url:substring")
        for key, val in (row.get("tags") or {}).items():
            if q_lower in str(key).lower():
                score += 15
                reasons.append(f"tag_key:{key}")
            if q_lower in str(val).lower():
                score += 25
                reasons.append(f"tag_value:{key}")
        project_name = row.get("project_name") or ""
        if q_lower in project_name.lower():
            score += 10
            reasons.append("project_name:substring")
        return score, reasons
