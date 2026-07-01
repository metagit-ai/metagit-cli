#!/usr/bin/env python
"""Shared fixtures for state backend tests."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from metagit.core.context.models import HandoffItem, Objective
from metagit.core.state.local import local_bundle
from metagit.core.state.remote import _normalize_token


class _StateStubHandler(BaseHTTPRequestHandler):
    workspace_root: str = ""

    def log_message(self, format: str, *args: Any) -> None:
        _ = (format, args)

    def _bundle(self):
        return local_bundle(self.workspace_root)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        parsed = json.loads(raw.decode("utf-8") or "{}")
        return parsed if isinstance(parsed, dict) else {}

    def _send_json(self, status: int, payload: dict[str, Any], *, etag: str | None = None) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if etag:
            self.send_header("ETag", f'"{etag}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/v3/ops/objectives"):
            backend = self._bundle().objectives()
            rows, token = backend.load()
            self._send_json(200, {"ok": True, "objectives": [row.model_dump(mode="json") for row in rows]}, etag=token)
            return
        if self.path.startswith("/v3/ops/approvals"):
            backend = self._bundle().approvals()
            rows, token = backend.load()
            self._send_json(200, {"ok": True, "requests": [row.model_dump(mode="json") for row in rows]}, etag=token)
            return
        if self.path.startswith("/v3/ops/handoffs"):
            backend = self._bundle().handoffs()
            rows, token = backend.load()
            self._send_json(200, {"ok": True, "handoffs": [row.model_dump(mode="json") for row in rows]}, etag=token)
            return
        if self.path.startswith("/v3/ops/events"):
            from metagit.core.context.event_service import WorkspaceEventService

            since = None
            if "since=" in self.path:
                since = self.path.split("since=", 1)[1].split("&", 1)[0]
            result = WorkspaceEventService(workspace_root=self.workspace_root).list_events(since=since or None)
            self._send_json(200, result.model_dump(mode="json"))
            return
        self._send_json(404, {"ok": False, "error": {"kind": "not_found"}})

    def do_PUT(self) -> None:
        expected = _normalize_token(self.headers.get("If-Match"))
        payload = self._read_json()
        if self.path == "/v3/ops/objectives":
            backend = self._bundle().objectives()
            rows = payload.get("objectives", [])
            from metagit.core.state.errors import StateConflictError as Conflict

            try:
                token = backend.save(
                    [Objective.model_validate(item) for item in rows if isinstance(item, dict)],
                    expected=expected,
                )
            except Conflict:
                self._send_json(412, {"ok": False, "error": {"kind": "state_conflict"}})
                return
            self._send_json(200, {"ok": True, "objectives": rows}, etag=token)
            return
        if self.path == "/v3/ops/approvals":
            backend = self._bundle().approvals()
            from metagit.core.context.models import ApprovalRequest
            from metagit.core.state.errors import StateConflictError as Conflict

            rows = payload.get("requests", [])
            try:
                token = backend.save(
                    [ApprovalRequest.model_validate(item) for item in rows if isinstance(item, dict)],
                    expected=expected,
                )
            except Conflict:
                self._send_json(412, {"ok": False, "error": {"kind": "state_conflict"}})
                return
            self._send_json(200, {"ok": True, "requests": rows}, etag=token)
            return
        if self.path == "/v3/ops/handoffs":
            backend = self._bundle().handoffs()
            from metagit.core.state.errors import StateConflictError as Conflict

            rows = payload.get("handoffs", [])
            try:
                token = backend.save(
                    [HandoffItem.model_validate(item) for item in rows if isinstance(item, dict)],
                    expected=expected,
                )
            except Conflict:
                self._send_json(412, {"ok": False, "error": {"kind": "state_conflict"}})
                return
            self._send_json(200, {"ok": True, "handoffs": rows}, etag=token)
            return
        self._send_json(404, {"ok": False})

    def do_POST(self) -> None:
        if self.path == "/v3/ops/handoffs":
            payload = self._read_json()
            saved = self._bundle().handoffs().append(HandoffItem.model_validate(payload))
            self._send_json(200, saved.model_dump(mode="json"))
            return
        self._send_json(404, {"ok": False})


@pytest.fixture
def remote_stub_server(tmp_path):
    handler_cls = type(
        "BoundStateStubHandler",
        (_StateStubHandler,),
        {"workspace_root": str(tmp_path)},
    )
    server = HTTPServer(("127.0.0.1", 0), handler_cls)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
