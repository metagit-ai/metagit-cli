#!/usr/bin/env python
"""In-process EverRoom Gateway fixture matching the NxCore loopback contract."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

SECRET_TOKEN = "er_secret_token_TEST"
ROOM_ID = "room_01JTESTMIGRATION"
ROOM_TITLE = "terraform-hcp-migration"


def terraform_fixture() -> dict[str, Any]:
    """Canonical mock Room used by campaign context tests."""
    return {
        "room": {
            "id": ROOM_ID,
            "title": ROOM_TITLE,
            "kind": "context",
            "summary": "Migrate Terraform from HCP to self-hosted",
        },
        "context": {
            "roomId": ROOM_ID,
            "overview": "HCP Terraform is being replaced with a self-hosted backend.",
            "status": "in_progress",
            "nextSteps": [
                "Decide S3 state bucket ownership",
                "Confirm VCS webhook cutover window",
            ],
            "actionItems": [],
            "sourceDocuments": [],
            "entities": [],
            "meetings": [],
        },
        "sources": [
            {
                "id": "src-network",
                "title": "terraform-network",
                "originalName": "github.com/org/terraform-network",
                "sourceKind": "git",
            },
            {
                "id": "src-org",
                "title": "terraform-org",
                "originalName": "github.com/org/terraform-org",
                "sourceKind": "git",
            },
            {
                "id": "src-accounts",
                "title": "terraform-accounts",
                "originalName": "github.com/org/terraform-accounts",
                "sourceKind": "git",
            },
            {
                "id": "src-modules",
                "title": "terraform-modules",
                "originalName": "github.com/org/terraform-modules",
                "sourceKind": "git",
            },
        ],
        "decisions": [
            {
                "decisionId": "dec-s3",
                "title": "Centralized S3 state was rejected",
                "reason": "Account isolation requires per-account state buckets.",
                "status": "Accepted",
                "roomId": ROOM_ID,
                "evidence": "Prior incident with shared state lock contention.",
            },
            {
                "decisionId": "dec-vcs",
                "title": "Keep GitHub VCS, drop HCP run tasks",
                "reason": "Run tasks can be replaced with local CI.",
                "status": "Accepted",
                "roomId": ROOM_ID,
            },
            {
                "decisionId": "dec-agents",
                "title": "Agents must not crawl private source into EverRoom",
                "reason": "Privacy boundary: identity and summaries only.",
                "status": "Accepted",
                "roomId": ROOM_ID,
            },
        ],
        "documents": [
            {
                "id": "doc-migration-plan",
                "title": "HCP migration plan",
                "version": 2,
                "roomId": ROOM_ID,
            },
            {
                "id": "doc-runbook",
                "title": "Cutover runbook",
                "version": 1,
                "roomId": ROOM_ID,
            },
        ],
        "wiki": [{"id": "wiki-overview", "title": "Migration wiki", "path": "overview"}],
        "materials": [{"id": "mat-1", "title": "Architecture sketch", "documentId": "doc-migration-plan"}],
    }


@dataclass
class MockGatewayState:
    """Mutable Gateway data for attach/create/sync tests."""

    token: str = SECRET_TOKEN
    require_auth: bool = True
    fail_mode: Optional[str] = None
    sleep_seconds: float = 0.0
    fixture: dict[str, Any] = field(default_factory=terraform_fixture)
    created_rooms: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)

    def rooms(self) -> list[dict[str, Any]]:
        rooms = [dict(self.fixture["room"])]
        rooms.extend(self.created_rooms)
        return rooms


class MockEverRoomHandler(BaseHTTPRequestHandler):
    """Loopback Gateway: public health, bearer for all other routes."""

    state: MockGatewayState

    def log_message(self, format: str, *args: Any) -> None:
        _ = (format, args)

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def _dispatch(self, method: str) -> None:
        if self.state.sleep_seconds:
            import time

            time.sleep(self.state.sleep_seconds)
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        if self.state.fail_mode == "unavailable":
            self._send(503, {"error": "not ready"})
            return
        if path in {"/v1/health/live", "/v1/health/ready"}:
            if self.state.fail_mode == "health-malformed":
                self._send_raw(200, b"not-json")
                return
            self._send(200, {"status": "ok", "service": "nxcore-gateway"})
            return
        if self.state.require_auth and not self._authorized():
            self._send(401, {"error": "unauthorized"})
            return
        if self.state.fail_mode == "malformed":
            self._send_raw(200, b"{not json")
            return
        if method == "GET":
            self._get(path, query)
            return
        if method == "POST":
            self._post(path)
            return
        if method == "PUT":
            self._put(path)
            return
        self._send(405, {"error": "method not allowed"})

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {self.state.token}"

    def _get(self, path: str, query: dict[str, list[str]]) -> None:
        fixture = self.state.fixture
        room_id = fixture["room"]["id"]
        if path == "/v1/context-rooms":
            self._send(200, {"rooms": self.state.rooms()})
            return
        if path == "/v1/knowledge/rooms":
            self._send(200, {"items": self.state.rooms()})
            return
        if path.startswith("/v1/context-rooms/") and path.endswith("/overview"):
            wanted = path.split("/")[3]
            if wanted != room_id and wanted not in {item["id"] for item in self.state.created_rooms}:
                self._send(404, {"error": "not found"})
                return
            self._send(200, {"overview": fixture["context"]["overview"]})
            return
        if path.startswith("/v1/knowledge/rooms/") and path.endswith("/context"):
            wanted = path.split("/")[4]
            if wanted != room_id:
                self._send(404, {"error": "not found"})
                return
            self._send(200, fixture["context"])
            return
        if path.startswith("/v1/knowledge/rooms/") and path.endswith("/files"):
            self._send(200, {"items": fixture["sources"]})
            return
        if path.startswith("/v1/knowledge/rooms/") and path.endswith("/wiki/pages"):
            self._send(200, {"items": fixture["wiki"]})
            return
        if path.startswith("/v1/knowledge/rooms/") and path.endswith("/materials"):
            self._send(200, {"items": fixture["materials"]})
            return
        if path == "/v1/knowledge/decisions":
            self._send(200, {"items": fixture["decisions"]})
            return
        if path == "/v1/documents":
            room_filter = (query.get("roomId") or [room_id])[0]
            rows = [item for item in [*fixture["documents"], *self.state.documents] if item.get("roomId") == room_filter]
            self._send(200, {"items": rows})
            return
        self._send(404, {"error": "not found"})

    def _post(self, path: str) -> None:
        body = self._read_json()
        if path == "/v1/context-rooms":
            created = {
                "id": f"room-created-{len(self.state.created_rooms) + 1}",
                "title": str(body.get("title") or "untitled"),
                "summary": str(body.get("description") or ""),
            }
            self.state.created_rooms.append(created)
            self._send(200, {"room": created, "created": True})
            return
        if path == "/v1/documents/import":
            document = {
                "id": str(body.get("id") or "imported"),
                "title": str(body.get("title") or ""),
                "version": 1,
                "roomId": body.get("roomId"),
            }
            self.state.documents.append(document)
            self._send(200, document)
            return
        self._send(404, {"error": "not found"})

    def _put(self, path: str) -> None:
        if not path.startswith("/v1/documents/"):
            self._send(404, {"error": "not found"})
            return
        document_id = path.rsplit("/", 1)[-1]
        body = self._read_json()
        for item in [*self.state.fixture["documents"], *self.state.documents]:
            if item["id"] == document_id:
                item["version"] = int(item.get("version") or 0) + 1
                if body.get("title"):
                    item["title"] = body["title"]
                self._send(200, item)
                return
        self._send(404, {"error": "not found"})

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        parsed = json.loads(raw.decode("utf-8") or "{}")
        return parsed if isinstance(parsed, dict) else {}

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_raw(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@dataclass
class MockGateway:
    """Running mock Gateway plus helpers."""

    url: str
    state: MockGatewayState
    _server: HTTPServer
    _thread: threading.Thread

    def stop(self) -> None:
        self._server.shutdown()
        self._thread.join(timeout=5)


def start_mock_gateway(*, state: Optional[MockGatewayState] = None) -> MockGateway:
    """Bind an ephemeral loopback Gateway."""
    gateway_state = state or MockGatewayState()

    class BoundHandler(MockEverRoomHandler):
        state = gateway_state

    server = HTTPServer(("127.0.0.1", 0), BoundHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return MockGateway(url=f"http://{host}:{port}", state=gateway_state, _server=server, _thread=thread)
