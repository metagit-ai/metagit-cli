#!/usr/bin/env python
"""Serve bundled static assets for the metagit web UI."""

from __future__ import annotations

import mimetypes
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse

from metagit import DATA_PATH

_API_PREFIXES = ("/v1", "/v2", "/v3")


class StaticWebHandler:
    """Serve SPA assets from the packaged web data directory."""

    def __init__(self, web_root: str | None = None) -> None:
        root = Path(web_root) if web_root is not None else Path(DATA_PATH) / "web"
        self._web_root = root.resolve()

    def handle(
        self, method: str, path: str, request_handler: BaseHTTPRequestHandler
    ) -> bool:
        """Serve static files for non-API GET requests."""
        if method != "GET":
            return False
        parsed_path = urlparse(path).path
        if parsed_path.startswith(_API_PREFIXES):
            return False
        file_path = self._resolve_file(parsed_path)
        if file_path is None or not file_path.is_file():
            file_path = self._web_root / "index.html"
        if not file_path.is_file():
            return False
        self._send_file(file_path, request_handler)
        return True

    def _resolve_file(self, parsed_path: str) -> Path | None:
        if parsed_path in ("", "/"):
            return self._web_root / "index.html"
        relative = unquote(parsed_path.lstrip("/"))
        candidate = (self._web_root / relative).resolve()
        web_root_resolved = self._web_root.resolve()
        if (
            candidate != web_root_resolved
            and web_root_resolved not in candidate.parents
        ):
            return None
        return candidate

    def _send_file(
        self, file_path: Path, request_handler: BaseHTTPRequestHandler
    ) -> None:
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"
        body = file_path.read_bytes()
        request_handler.send_response(200)
        request_handler.send_header("Content-Type", content_type)
        request_handler.send_header("Content-Length", str(len(body)))
        request_handler.end_headers()
        request_handler.wfile.write(body)

    @staticmethod
    def is_api_path(path: str) -> bool:
        """Return True when the path belongs to a versioned API route."""
        parsed_path = urlparse(path).path
        return parsed_path.startswith(_API_PREFIXES)
