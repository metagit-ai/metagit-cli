#!/usr/bin/env python
"""
Minimal local JSON HTTP API for managed workspace repository search.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from metagit.core.api.catalog_handler import CatalogApiHandler
from metagit.core.api.layout_handler import LayoutApiHandler
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.project.search_service import ManagedRepoSearchService


def _parse_tag_filters_from_query(tag_values: list[str]) -> dict[str, str] | None:
    """Parse repeated `tag=key=value` style query pairs into a tag filter dict."""
    if not tag_values:
        return None
    parsed: dict[str, str] = {}
    for item in tag_values:
        if "=" not in item:
            continue
        key, _, value = item.partition("=")
        if key:
            parsed[key] = value
    return parsed or None


def _first(
    params: dict[str, list[str]], key: str, default: str | None = None
) -> str | None:
    """Return the first query value for a key, or default if missing or empty."""
    values = params.get(key)
    if not values:
        return default
    first = values[0]
    return first if first else default


def build_server(root: str, host: str, port: int) -> ThreadingHTTPServer:
    """Build a threading HTTP server rooted at a workspace directory."""
    root_resolved = str(Path(root).resolve())
    config_path = os.path.join(root_resolved, ".metagit.yml")
    service = ManagedRepoSearchService()
    catalog = CatalogApiHandler(
        workspace_root=root_resolved,
        config_path=config_path,
    )
    layout = LayoutApiHandler(
        definition_root=root_resolved,
        config_path=config_path,
    )

    class ReusableThreadingHTTPServer(ThreadingHTTPServer):
        allow_reuse_address = True

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            _ = (format, args)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query, keep_blank_values=True)
            if catalog.handle(
                "GET",
                parsed.path,
                parsed.query,
                b"",
                self._json,
            ):
                return
            manager = MetagitConfigManager(config_path)
            loaded = manager.load_config()
            if isinstance(loaded, Exception):
                self._json(
                    500,
                    {
                        "error": {
                            "kind": "config_error",
                            "message": str(loaded),
                        }
                    },
                )
                return
            config = loaded

            if parsed.path == "/v1/repos/search":
                limit_raw = _first(params, "limit", "10") or "10"
                try:
                    limit_val = int(limit_raw)
                except ValueError:
                    limit_val = 10
                limit_val = max(1, min(limit_val, 500))
                project_raw = _first(params, "project")
                project_filter = (
                    project_raw.strip()
                    if isinstance(project_raw, str) and project_raw.strip()
                    else None
                )
                result = service.search(
                    config=config,
                    workspace_root=root_resolved,
                    query=_first(params, "q", "") or "",
                    project=project_filter,
                    exact=(_first(params, "exact", "false") or "false").lower()
                    == "true",
                    synced_only=(
                        _first(params, "synced_only", "false") or "false"
                    ).lower()
                    == "true",
                    tags=_parse_tag_filters_from_query(params.get("tag", [])),
                    limit=limit_val,
                )
                self._json(200, result.model_dump(mode="json"))
                return

            if parsed.path == "/v1/repos/resolve":
                project_raw = _first(params, "project")
                project_filter = (
                    project_raw.strip()
                    if isinstance(project_raw, str) and project_raw.strip()
                    else None
                )
                resolved = service.resolve_one(
                    config=config,
                    workspace_root=root_resolved,
                    query=_first(params, "q", "") or "",
                    project=project_filter,
                    exact=(_first(params, "exact", "false") or "false").lower()
                    == "true",
                    synced_only=(
                        _first(params, "synced_only", "true") or "true"
                    ).lower()
                    == "true",
                    tags=_parse_tag_filters_from_query(params.get("tag", [])),
                )
                if resolved.match is not None:
                    code = 200
                elif (
                    resolved.error is not None
                    and resolved.error.kind == "ambiguous_match"
                ):
                    code = 409
                else:
                    code = 404
                self._json(code, resolved.model_dump(mode="json"))
                return

            self._json(
                404,
                {"error": {"kind": "not_found", "message": "Unknown endpoint"}},
            )

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else b""
            if layout.handle("POST", parsed.path, parsed.query, body, self._json):
                return
            if catalog.handle("POST", parsed.path, parsed.query, body, self._json):
                return
            self._json(
                404,
                {"error": {"kind": "not_found", "message": "Unknown endpoint"}},
            )

        def do_DELETE(self) -> None:
            parsed = urlparse(self.path)
            if catalog.handle("DELETE", parsed.path, parsed.query, b"", self._json):
                return
            self._json(
                404,
                {"error": {"kind": "not_found", "message": "Unknown endpoint"}},
            )

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ReusableThreadingHTTPServer((host, port), Handler)
