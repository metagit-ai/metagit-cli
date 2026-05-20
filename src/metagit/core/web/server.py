#!/usr/bin/env python
"""Local HTTP server for the metagit web UI (config routes first)."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from metagit.core.web.config_handler import ConfigWebHandler


def build_web_server(
    *,
    root: str,
    appconfig_path: str,
    host: str = "127.0.0.1",
    port: int = 8787,
) -> ThreadingHTTPServer:
    """Build a threading HTTP server for web UI config routes."""
    root_resolved = str(Path(root).resolve())
    config_path = os.path.join(root_resolved, ".metagit.yml")
    config_handler = ConfigWebHandler(
        metagit_config_path=config_path,
        appconfig_path=str(Path(appconfig_path).resolve()),
    )

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

        def _dispatch(self, method: str) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else b""
            if config_handler.handle(
                method,
                parsed.path,
                parsed.query,
                body,
                self._json,
            ):
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
