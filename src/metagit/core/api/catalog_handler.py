#!/usr/bin/env python
"""
HTTP handlers for workspace catalog list and mutation (v2 API).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlparse

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.workspace.catalog_models import CatalogError, CatalogMutationResult
from metagit.core.workspace.catalog_service import WorkspaceCatalogService


JsonResponder = Callable[[int, dict[str, Any]], None]


class CatalogApiHandler:
    """Route catalog operations for the local JSON HTTP API."""

    def __init__(self, workspace_root: str, config_path: str) -> None:
        self._workspace_root = str(Path(workspace_root).resolve())
        self._config_path = str(Path(config_path).resolve())
        self._service = WorkspaceCatalogService()

    def handle(
        self,
        method: str,
        path: str,
        query: str,
        body: bytes,
        respond: JsonResponder,
    ) -> bool:
        """Dispatch catalog routes; return True when handled."""
        parsed_path = urlparse(path).path
        params = parse_qs(query, keep_blank_values=True)
        config = self._load_config(respond)
        if config is None:
            return True

        if method == "GET" and parsed_path == "/v2/workspace":
            result = self._service.list_workspace(
                config,
                self._config_path,
                self._workspace_root,
            )
            respond(200, result.model_dump(mode="json"))
            return True

        if method == "GET" and parsed_path == "/v2/projects":
            result = self._service.list_projects(config)
            respond(200, result.model_dump(mode="json"))
            return True

        if method == "POST" and parsed_path == "/v2/projects":
            payload = self._parse_body(body, respond)
            if payload is None:
                return True
            name = str(payload.get("name", "")).strip()
            mutation = self._service.add_project(
                config,
                self._config_path,
                name=name,
                description=payload.get("description"),
                agent_instructions=payload.get("agent_instructions"),
                ensure=bool(payload.get("ensure", True)),
            )
            self._respond_mutation(mutation, respond)
            return True

        if method == "DELETE" and parsed_path.startswith("/v2/projects/"):
            name = unquote(parsed_path.removeprefix("/v2/projects/").strip("/"))
            mutation = self._service.remove_project(
                config,
                self._config_path,
                name=name,
            )
            self._respond_mutation(mutation, respond)
            return True

        if method == "GET" and parsed_path == "/v2/repos":
            project = self._first(params, "project")
            result = self._service.list_repos(
                config,
                self._workspace_root,
                project_name=project,
            )
            respond(200, result.model_dump(mode="json"))
            return True

        if method == "POST" and parsed_path == "/v2/repos":
            payload = self._parse_body(body, respond)
            if payload is None:
                return True
            project_name = str(payload.get("project", "")).strip()
            built = self._service.build_repo_from_fields(
                name=str(payload.get("name", "")),
                description=payload.get("description"),
                kind=payload.get("kind"),
                path=payload.get("path"),
                url=payload.get("url"),
                sync=payload.get("sync"),
                agent_instructions=payload.get("agent_instructions"),
                tags=payload.get("tags")
                if isinstance(payload.get("tags"), dict)
                else None,
            )
            if isinstance(built, CatalogError):
                respond(400, {"ok": False, "error": built.model_dump(mode="json")})
                return True
            mutation = self._service.add_repo(
                config,
                self._config_path,
                project_name=project_name,
                repo=built,
                ensure=bool(payload.get("ensure", True)),
            )
            self._respond_mutation(mutation, respond)
            return True

        if method == "DELETE" and parsed_path.startswith("/v2/repos/"):
            remainder = parsed_path.removeprefix("/v2/repos/").strip("/")
            if "/" not in remainder:
                respond(
                    400,
                    {
                        "ok": False,
                        "error": {
                            "kind": "invalid_path",
                            "message": "use /v2/repos/{project}/{repo}",
                        },
                    },
                )
                return True
            project_name, repo_name = remainder.split("/", 1)
            mutation = self._service.remove_repo(
                config,
                self._config_path,
                project_name=unquote(project_name),
                repo_name=unquote(repo_name),
            )
            self._respond_mutation(mutation, respond)
            return True

        return False

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

    def _parse_body(self, body: bytes, respond: JsonResponder) -> dict[str, Any] | None:
        if not body:
            respond(
                400,
                {
                    "ok": False,
                    "error": {"kind": "invalid_body", "message": "JSON body required"},
                },
            )
            return None
        try:
            parsed = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            respond(
                400,
                {"ok": False, "error": {"kind": "invalid_json", "message": str(exc)}},
            )
            return None
        if not isinstance(parsed, dict):
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_body",
                        "message": "expected JSON object",
                    },
                },
            )
            return None
        return parsed

    def _respond_mutation(
        self,
        mutation: CatalogMutationResult,
        respond: JsonResponder,
    ) -> None:
        status = 200 if mutation.ok else 409
        if mutation.error and mutation.error.kind == "not_found":
            status = 404
        if mutation.error and mutation.error.kind in {
            "invalid_name",
            "invalid_repo",
            "invalid_body",
        }:
            status = 400
        respond(status, mutation.model_dump(mode="json"))

    @staticmethod
    def _first(params: dict[str, list[str]], key: str) -> str | None:
        values = params.get(key)
        if not values:
            return None
        first = values[0].strip()
        return first or None
