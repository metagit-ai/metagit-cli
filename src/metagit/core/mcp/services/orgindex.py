#!/usr/bin/env python
"""MCP adapters for organization index, search, and materialize."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.orgindex.indexer import GitHubOrgIndexer
from metagit.core.orgindex.search import OrgSearchService
from metagit.core.orgindex.store import default_index_home
from metagit.core.repo.materialize import RepoMaterializeService
from metagit.core.repo.neighborhood import GraphNeighborhoodService
from metagit.core.repo.resolver import RepositoryResolver


class OrgIndexMcpService:
    """Thin MCP-facing wrapper around organization index services."""

    def __init__(self, *, index_home: Path | None = None) -> None:
        self._index_home = index_home or default_index_home()

    def index_github(
        self,
        organization: str,
        *,
        app_config: AppConfig,
        refresh: bool = False,
        full: bool = False,
    ) -> dict[str, Any]:
        result = GitHubOrgIndexer(app_config=app_config, index_home=self._index_home).index(
            organization,
            refresh=refresh,
            full=full,
        )
        return result.model_dump(mode="json")

    def search(
        self,
        query: str | None = None,
        *,
        organization: str | None = None,
        language: str | None = None,
        topic: str | None = None,
        has: str | None = None,
        stale_days: int | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        result = OrgSearchService(index_home=self._index_home).search(
            query,
            organization=organization,
            language=language,
            topic=topic,
            has=has,
            stale_days=stale_days,
            limit=limit,
        )
        return result.model_dump(mode="json")

    def get_repository(self, identifier: str, config: MetagitConfig | None = None) -> dict[str, Any]:
        resolver = RepositoryResolver(config, index_home=self._index_home)
        resolved = resolver.resolve(identifier)
        if isinstance(resolved, Exception):
            return {"ok": False, "error": str(resolved)}
        if resolved is None:
            return {"ok": False, "error": f"unknown repository '{identifier}'"}
        return {"ok": True, "repository": resolved.model_dump(mode="json")}

    def neighbors(self, identifier: str, config: MetagitConfig | None = None) -> dict[str, Any]:
        result = GraphNeighborhoodService(index_home=self._index_home).neighbors(config, identifier)
        return result.model_dump(mode="json")

    def materialize(
        self,
        identifier: str,
        *,
        config: MetagitConfig,
        config_path: str,
        workspace_root: str,
        project_name: str | None = None,
        confirm: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if not confirm and not dry_run:
            return {"ok": False, "error": "confirm must be true to materialize (or pass dry_run)"}
        result = RepoMaterializeService().materialize(
            config,
            config_path,
            identifier,
            workspace_root=workspace_root,
            project_name=project_name,
            dry_run=dry_run,
        )
        return result.model_dump(mode="json")
