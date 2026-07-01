#!/usr/bin/env python
"""Local HTTP server for the metagit web UI."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from metagit.core.api.catalog_handler import CatalogApiHandler
from metagit.core.api.grep_handler import GrepApiHandler
from metagit.core.api.layout_handler import LayoutApiHandler
from metagit.core.appconfig import load_config as load_appconfig
from metagit.core.web.agent_handler import AgentWebHandler
from metagit.core.web.config_handler import ConfigWebHandler
from metagit.core.web.ops_handler import OpsWebHandler
from metagit.core.web.static_handler import StaticWebHandler


def _resolve_workspace_root(root: str, workspace_path: str) -> str:
    """Resolve workspace sync root from appconfig path (relative to manifest root)."""
    path = Path(workspace_path).expanduser()
    path = (Path(root) / path).resolve() if not path.is_absolute() else path.resolve()
    return str(path)


def build_web_server(
    *,
    root: str,
    appconfig_path: str,
    host: str = "127.0.0.1",
    port: int = 8787,
) -> ThreadingHTTPServer:
    """Build a threading HTTP server for web UI routes."""
    root_resolved = str(Path(root).resolve())
    config_path = os.path.join(root_resolved, ".metagit.yml")
    appconfig_resolved = str(Path(appconfig_path).resolve())
    app_config = load_appconfig(appconfig_resolved)
    if isinstance(app_config, Exception):
        raise ValueError(f"Failed to load app config: {app_config}")
    if app_config.workspace is None:
        raise ValueError("app config missing workspace section")
    workspace_root = _resolve_workspace_root(
        root_resolved,
        str(app_config.workspace.path),
    )
    static_handler = StaticWebHandler()
    catalog_handler = CatalogApiHandler(
        workspace_root=workspace_root,
        config_path=config_path,
    )
    layout_handler = LayoutApiHandler(
        definition_root=root_resolved,
        config_path=config_path,
    )
    grep_handler = GrepApiHandler(
        workspace_root=workspace_root,
        config_path=config_path,
    )
    config_handler = ConfigWebHandler(
        metagit_config_path=config_path,
        appconfig_path=appconfig_resolved,
    )
    ops_handler = OpsWebHandler(
        root=root_resolved,
        config_path=config_path,
        appconfig_path=appconfig_resolved,
        workspace_root=workspace_root,
    )
    agent_handler = AgentWebHandler(manifest_root=root_resolved)

    class ReusableThreadingHTTPServer(ThreadingHTTPServer):
        allow_reuse_address = True

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            _ = (format, args)

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_PATCH(self) -> None:
            self._dispatch("PATCH")

        def do_POST(self) -> None:
            self._dispatch("POST")

        def do_DELETE(self) -> None:
            self._dispatch("DELETE")

        def do_PUT(self) -> None:
            self._dispatch("PUT")

        def _dispatch(self, method: str) -> None:
            parsed = urlparse(self.path)
            events_job_id = ops_handler.sync_events_job_id(method, parsed.path)
            if events_job_id is not None:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                ops_handler.stream_sync_events(events_job_id, self.wfile)
                return

            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else b""
            request_headers = dict(self.headers.items())

            if agent_handler.handle(
                method,
                parsed.path,
                parsed.query,
                body,
                self._json,
            ):
                return

            if method == "GET":
                if static_handler.handle(method, parsed.path, self):
                    return
                if catalog_handler.handle(
                    method,
                    parsed.path,
                    parsed.query,
                    body,
                    self._json,
                ):
                    return
                if grep_handler.handle(
                    method,
                    parsed.path,
                    parsed.query,
                    body,
                    self._json,
                ):
                    return
                if layout_handler.handle(
                    method,
                    parsed.path,
                    parsed.query,
                    body,
                    self._json,
                ):
                    return
                if config_handler.handle(
                    method,
                    parsed.path,
                    parsed.query,
                    body,
                    self._json,
                ):
                    return
                if ops_handler.handle(
                    method,
                    parsed.path,
                    parsed.query,
                    body,
                    self._json,
                    request_headers,
                ):
                    return
                if StaticWebHandler.is_api_path(parsed.path):
                    self._json(
                        404,
                        {"error": {"kind": "not_found", "message": "Unknown endpoint"}},
                    )
                    return
                return

            if layout_handler.handle(
                method,
                parsed.path,
                parsed.query,
                body,
                self._json,
            ):
                return
            if catalog_handler.handle(
                method,
                parsed.path,
                parsed.query,
                body,
                self._json,
            ):
                return
            if config_handler.handle(
                method,
                parsed.path,
                parsed.query,
                body,
                self._json,
            ):
                return
            if ops_handler.handle(
                method,
                parsed.path,
                parsed.query,
                body,
                self._json,
                request_headers,
            ):
                return
            if StaticWebHandler.is_api_path(parsed.path):
                self._json(
                    404,
                    {"error": {"kind": "not_found", "message": "Unknown endpoint"}},
                )
                return
            self._json(
                404,
                {"error": {"kind": "not_found", "message": "Unknown endpoint"}},
            )

        def _json(
            self,
            status: int,
            payload: dict[str, Any],
            headers: dict[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            if headers:
                for key, value in headers.items():
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

    return ReusableThreadingHTTPServer((host, port), Handler)
