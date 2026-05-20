#!/usr/bin/env python
"""
HTTP handlers for workspace layout rename and move (v2 API).
"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlparse

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.workspace.layout_context import resolve_sync_context
from metagit.core.workspace.layout_models import LayoutMutationResult
from metagit.core.workspace.layout_service import WorkspaceLayoutService

JsonResponder = Callable[[int, dict[str, Any]], None]


class LayoutApiHandler:
    """Route layout rename/move operations for the local JSON HTTP API."""

    def __init__(self, definition_root: str, config_path: str) -> None:
        self._definition_root = definition_root
        self._config_path = config_path
        self._service = WorkspaceLayoutService()

    def handle(
        self,
        method: str,
        path: str,
        query: str,
        body: bytes,
        respond: JsonResponder,
    ) -> bool:
        """Dispatch layout routes; return True when handled."""
        parsed_path = urlparse(path).path
        params = parse_qs(query, keep_blank_values=True)
        config = self._load_config(respond)
        if config is None:
            return True

        sync_root, dedupe = resolve_sync_context(self._definition_root)

        if method == "POST" and parsed_path.endswith("/rename"):
            flags = self._layout_flags(params, body, respond)
            if flags is None:
                return True
            if parsed_path.startswith("/v2/projects/"):
                from_name = unquote(
                    parsed_path.removeprefix("/v2/projects/")
                    .removesuffix("/rename")
                    .strip("/")
                )
                payload = flags.get("body") or {}
                to_name = str(
                    payload.get("to_name") or self._first(params, "to_name") or ""
                ).strip()
                result = self._service.rename_project(
                    config,
                    self._config_path,
                    sync_root,
                    from_name=from_name,
                    to_name=to_name,
                    dedupe=dedupe,
                    dry_run=flags["dry_run"],
                    move_disk=flags["move_disk"],
                    update_sessions=flags["update_sessions"],
                    force=flags["force"],
                )
                self._respond_layout(result, respond)
                return True

            if "/v2/repos/" in parsed_path and parsed_path.endswith("/rename"):
                remainder = (
                    parsed_path.removeprefix("/v2/repos/")
                    .removesuffix("/rename")
                    .strip("/")
                )
                if "/" not in remainder:
                    respond(
                        400,
                        {
                            "ok": False,
                            "error": {
                                "kind": "invalid_path",
                                "message": "use /v2/repos/{project}/{repo}/rename",
                            },
                        },
                    )
                    return True
                project_name, repo_name = remainder.split("/", 1)
                if flags is None:
                    return True
                payload = flags.get("body") or {}
                result = self._service.rename_repo(
                    config,
                    self._config_path,
                    sync_root,
                    project_name=unquote(project_name),
                    from_name=unquote(repo_name),
                    to_name=str(payload.get("to_name", "")).strip(),
                    dedupe=dedupe,
                    dry_run=flags["dry_run"],
                    move_disk=flags["move_disk"],
                    force=flags["force"],
                )
                self._respond_layout(result, respond)
                return True

        if method == "POST" and parsed_path.endswith("/move"):
            flags = self._layout_flags(params, body, respond)
            if flags is None:
                return True
            if "/v2/repos/" in parsed_path:
                remainder = (
                    parsed_path.removeprefix("/v2/repos/")
                    .removesuffix("/move")
                    .strip("/")
                )
                if "/" not in remainder:
                    respond(
                        400,
                        {
                            "ok": False,
                            "error": {
                                "kind": "invalid_path",
                                "message": "use /v2/repos/{project}/{repo}/move",
                            },
                        },
                    )
                    return True
                project_name, repo_name = remainder.split("/", 1)
                if flags is None:
                    return True
                payload = flags.get("body") or {}
                result = self._service.move_repo(
                    config,
                    self._config_path,
                    sync_root,
                    repo_name=unquote(repo_name),
                    from_project=unquote(project_name),
                    to_project=str(payload.get("to_project", "")).strip(),
                    dedupe=dedupe,
                    dry_run=flags["dry_run"],
                    move_disk=flags["move_disk"],
                    force=flags["force"],
                )
                self._respond_layout(result, respond)
                return True

        return False

    def _layout_flags(
        self,
        params: dict[str, list[str]],
        body: bytes,
        respond: JsonResponder,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {}
        if body:
            try:
                parsed = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                respond(
                    400,
                    {
                        "ok": False,
                        "error": {"kind": "invalid_json", "message": str(exc)},
                    },
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
            payload = parsed

        def _bool_param(key: str, default: bool = False) -> bool:
            raw = params.get(key, [str(payload.get(key, default)).lower()])
            value = raw[0] if raw else str(default).lower()
            return value.lower() in {"1", "true", "yes"}

        manifest_only = _bool_param("manifest_only") or bool(
            payload.get("manifest_only", False)
        )
        return {
            "body": payload,
            "dry_run": _bool_param("dry_run") or bool(payload.get("dry_run", False)),
            "move_disk": not manifest_only,
            "update_sessions": not _bool_param("no_update_sessions"),
            "force": _bool_param("force") or bool(payload.get("force", False)),
        }

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

    def _respond_layout(
        self,
        mutation: LayoutMutationResult,
        respond: JsonResponder,
    ) -> None:
        status = 200 if mutation.ok else 409
        if mutation.error and mutation.error.kind == "not_found":
            status = 404
        if mutation.error and mutation.error.kind in {
            "invalid_name",
            "noop",
            "unsupported",
        }:
            status = 400
        if mutation.error and mutation.error.kind == "protected":
            status = 403
        respond(status, mutation.model_dump(mode="json"))

    @staticmethod
    def _first(params: dict[str, list[str]], key: str) -> str | None:
        values = params.get(key)
        if not values:
            return None
        first = values[0].strip()
        return first or None
