#!/usr/bin/env python
"""Remote HTTP state backend using the metagit ops API contract."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from metagit.core.context.models import (
    ApprovalRequest,
    HandoffItem,
    Objective,
    WorkspaceEventsResult,
)
from metagit.core.state.base import BackendBundle, StateToken
from metagit.core.state.errors import StateBackendError, StateConflictError


@dataclass(frozen=True)
class RemoteBackendConfig:
    """Connection settings for ``RemoteHttpBackend``."""

    base_url: str
    bearer_token: str = ""


def _normalize_token(raw: str | None) -> StateToken:
    if raw is None:
        return None
    value = raw.strip()
    if not value or value == "*":
        return None
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value or None


def _format_if_match(token: StateToken) -> str:
    if token is None:
        return '""'
    return f'"{token}"'


class RemoteHttpBackend:
    """HTTP-backed objectives, handoffs, approvals, and events."""

    def __init__(self, config: RemoteBackendConfig) -> None:
        self._config = config
        parsed = urllib.parse.urlparse(config.base_url.rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise StateBackendError(f"remote state url must be http(s): {config.base_url!r}")
        self._base = config.base_url.rstrip("/")

    def _request_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._config.bearer_token:
            headers["Authorization"] = f"Bearer {self._config.bearer_token}"
        if extra:
            headers.update(extra)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        if_match: StateToken | None = None,
        send_if_match: bool = False,
    ) -> tuple[int, dict[str, Any], StateToken]:
        url = f"{self._base}{path}"
        payload = None if body is None else json.dumps(body).encode("utf-8")
        extra_headers: dict[str, str] = {}
        if send_if_match:
            extra_headers["If-Match"] = _format_if_match(if_match)
        request = urllib.request.Request(
            url,
            data=payload,
            headers=self._request_headers(extra_headers),
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
                raw = response.read()
                parsed: dict[str, Any] = json.loads(raw.decode("utf-8")) if raw else {}
                etag = _normalize_token(response.headers.get("ETag"))
                return response.status, parsed, etag
        except urllib.error.HTTPError as exc:
            if exc.code == 412:
                raise StateConflictError(f"remote state conflict for {path}") from exc
            detail = exc.read().decode("utf-8", errors="replace")
            raise StateBackendError(
                f"remote state request failed ({exc.code}) for {path}: {detail}",
            ) from exc
        except urllib.error.URLError as exc:
            raise StateBackendError(f"remote state request failed for {path}: {exc}") from exc

    def load_objectives(self) -> tuple[list[Objective], StateToken]:
        _, payload, token = self._request("GET", "/v3/ops/objectives")
        raw_list = payload.get("objectives")
        if not isinstance(raw_list, list):
            return [], token
        return [Objective.model_validate(item) for item in raw_list if isinstance(item, dict)], token

    def save_objectives(
        self,
        objectives: list[Objective],
        *,
        expected: StateToken,
    ) -> StateToken:
        body = {"objectives": [row.model_dump(mode="json") for row in objectives]}
        _, _, token = self._request(
            "PUT",
            "/v3/ops/objectives",
            body=body,
            if_match=expected,
            send_if_match=True,
        )
        return token

    def load_handoffs(self) -> tuple[list[HandoffItem], StateToken]:
        _, payload, token = self._request("GET", "/v3/ops/handoffs")
        raw_list = payload.get("handoffs")
        if not isinstance(raw_list, list):
            return [], token
        return [HandoffItem.model_validate(item) for item in raw_list if isinstance(item, dict)], token

    def save_handoffs(
        self,
        handoffs: list[HandoffItem],
        *,
        expected: StateToken,
    ) -> StateToken:
        body = {"handoffs": [row.model_dump(mode="json") for row in handoffs]}
        _, _, token = self._request(
            "PUT",
            "/v3/ops/handoffs",
            body=body,
            if_match=expected,
            send_if_match=True,
        )
        return token

    def append_handoff(self, item: HandoffItem) -> HandoffItem:
        body = item.model_dump(mode="json")
        _, payload, _ = self._request("POST", "/v3/ops/handoffs", body=body)
        if isinstance(payload, dict) and payload.get("id"):
            return HandoffItem.model_validate(payload)
        return item

    def load_requests(self) -> tuple[list[ApprovalRequest], StateToken]:
        _, payload, token = self._request("GET", "/v3/ops/approvals?status=all")
        raw_list = payload.get("requests")
        if not isinstance(raw_list, list):
            return [], token
        rows: list[ApprovalRequest] = []
        for item in raw_list:
            if isinstance(item, dict):
                rows.append(ApprovalRequest.model_validate(item))
        return rows, token

    def save_requests(
        self,
        requests: list[ApprovalRequest],
        *,
        expected: StateToken,
    ) -> StateToken:
        body = {"requests": [row.model_dump(mode="json") for row in requests]}
        _, _, token = self._request(
            "PUT",
            "/v3/ops/approvals",
            body=body,
            if_match=expected,
            send_if_match=True,
        )
        return token

    def list_events(self, *, since: str | None = None) -> WorkspaceEventsResult:
        query = f"?since={since}" if since else ""
        _, payload, _ = self._request("GET", f"/v3/ops/events{query}")
        return WorkspaceEventsResult.model_validate(payload)


class _RemoteObjectiveAdapter:
    def __init__(self, backend: RemoteHttpBackend) -> None:
        self._backend = backend

    def load(self) -> tuple[list[Objective], StateToken]:
        return self._backend.load_objectives()

    def save(
        self,
        objectives: list[Objective],
        *,
        expected: StateToken,
    ) -> StateToken:
        return self._backend.save_objectives(objectives, expected=expected)


class _RemoteHandoffAdapter:
    def __init__(self, backend: RemoteHttpBackend) -> None:
        self._backend = backend

    def load(self) -> tuple[list[HandoffItem], StateToken]:
        return self._backend.load_handoffs()

    def save(
        self,
        handoffs: list[HandoffItem],
        *,
        expected: StateToken,
    ) -> StateToken:
        return self._backend.save_handoffs(handoffs, expected=expected)

    def append(self, item: HandoffItem) -> HandoffItem:
        return self._backend.append_handoff(item)


class _RemoteApprovalAdapter:
    def __init__(self, backend: RemoteHttpBackend) -> None:
        self._backend = backend

    def load(self) -> tuple[list[ApprovalRequest], StateToken]:
        return self._backend.load_requests()

    def save(
        self,
        requests: list[ApprovalRequest],
        *,
        expected: StateToken,
    ) -> StateToken:
        return self._backend.save_requests(requests, expected=expected)


class _RemoteEventsAdapter:
    def __init__(self, backend: RemoteHttpBackend) -> None:
        self._backend = backend

    def list_events(self, *, since: str | None = None) -> WorkspaceEventsResult:
        return self._backend.list_events(since=since)


def remote_bundle(base_url: str, *, bearer_token: str = "") -> BackendBundle:
    """Construct a remote backend bundle for one ops base URL."""
    backend = RemoteHttpBackend(RemoteBackendConfig(base_url=base_url, bearer_token=bearer_token))
    return BackendBundle(
        objectives_backend=_RemoteObjectiveAdapter(backend),
        handoffs_backend=_RemoteHandoffAdapter(backend),
        approvals_backend=_RemoteApprovalAdapter(backend),
        events_backend=_RemoteEventsAdapter(backend),
    )


__all__ = ["RemoteBackendConfig", "RemoteHttpBackend", "remote_bundle"]
