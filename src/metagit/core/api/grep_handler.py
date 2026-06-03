#!/usr/bin/env python
"""
HTTP handler for workspace content grep (v2 API).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.mcp.services.workspace_search import WorkspaceSearchService

JsonResponder = Callable[[int, dict[str, Any]], None]


class GrepApiHandler:
    """Route workspace grep operations for the local JSON HTTP API."""

    def __init__(self, workspace_root: str, config_path: str) -> None:
        self._workspace_root = str(Path(workspace_root).resolve())
        self._config_path = str(Path(config_path).resolve())
        self._index = WorkspaceIndexService()
        self._search = WorkspaceSearchService()

    def handle(
        self,
        method: str,
        path: str,
        query: str,
        body: bytes,
        respond: JsonResponder,
    ) -> bool:
        """Dispatch grep routes; return True when handled."""
        _ = body
        parsed_path = urlparse(path).path
        if method != "GET":
            return False
        if parsed_path == "/v2/workspace/grep/info":
            respond(
                200,
                {"ok": True, "data": WorkspaceSearchService.ripgrep_status()},
            )
            return True
        if parsed_path != "/v2/workspace/grep":
            return False

        params = parse_qs(query, keep_blank_values=True)
        query_text = self._first(params, "q")
        if not query_text:
            respond(
                400,
                {
                    "ok": False,
                    "error": {"kind": "invalid_query", "message": "q is required"},
                },
            )
            return True

        config = self._load_config(respond)
        if config is None:
            return True

        repo_rows = self._index.build_index(config, self._workspace_root)
        project = self._first(params, "project")
        if project:
            repo_rows = [
                row for row in repo_rows if str(row.get("project_name", "")) == project
            ]

        repo_selectors = [
            item.strip() for item in params.get("repo", []) if item.strip()
        ]
        repo_paths = self._search.filter_repo_paths(
            repo_rows=repo_rows,
            repos=repo_selectors or None,
        )
        path_to_row = {str(row.get("repo_path", "")): row for row in repo_rows}

        max_results = self._bounded_int(
            self._first(params, "max_results", "25") or "25",
            default=25,
            minimum=1,
            maximum=500,
        )
        context_lines = self._bounded_int(
            self._first(params, "context_lines", "0") or "0",
            default=0,
            minimum=0,
            maximum=20,
        )
        include_paths = (
            self._first(params, "include_paths", "false") or "false"
        ).lower() == "true"

        hits = self._search.search(
            query=query_text,
            repo_paths=repo_paths,
            preset=self._first(params, "preset"),
            intent=self._first(params, "intent"),
            max_results=max_results,
            context_lines=context_lines,
            include_paths=include_paths,
        )
        enriched: list[dict[str, Any]] = []
        for hit in hits:
            row = path_to_row.get(str(hit.get("repo_path", "")))
            enriched_hit = dict(hit)
            if row is not None:
                enriched_hit["project_name"] = row.get("project_name")
                enriched_hit["repo_name"] = row.get("repo_name")
            enriched.append(enriched_hit)

        respond(200, {"ok": True, "data": {"hits": enriched}})
        return True

    def _load_config(self, respond: JsonResponder) -> MetagitConfig | None:
        manager = MetagitConfigManager(self._config_path)
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            respond(
                500,
                {
                    "ok": False,
                    "error": {"kind": "config_error", "message": str(loaded)},
                },
            )
            return None
        return loaded

    @staticmethod
    def _first(
        params: dict[str, list[str]], key: str, default: str | None = None
    ) -> str | None:
        values = params.get(key)
        if not values:
            return default
        first = values[0].strip()
        return first or default

    @staticmethod
    def _bounded_int(
        raw: str,
        *,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        try:
            value = int(raw)
        except ValueError:
            return default
        return max(minimum, min(value, maximum))
