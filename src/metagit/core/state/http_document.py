#!/usr/bin/env python
"""HTTP DocumentStore adapter for existing coordination ops routes."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from metagit.core.state.document import DocumentRef, StateRecord, StateToken
from metagit.core.state.errors import StateBackendError, StateConflictError
from metagit.core.state.plane import (
    KEY_DOCUMENT,
    NS_COORD_APPROVALS,
    NS_COORD_EVENTS,
    NS_COORD_HANDOFFS,
    NS_COORD_OBJECTIVES,
)

_COORD_PATHS: dict[str, str] = {
    NS_COORD_OBJECTIVES: "/v3/ops/objectives",
    NS_COORD_HANDOFFS: "/v3/ops/handoffs",
    NS_COORD_APPROVALS: "/v3/ops/approvals",
    NS_COORD_EVENTS: "/v3/ops/events",
}


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
    return '""' if token is None else f'"{token}"'


def sanitize_base_url_for_describe(base_url: str) -> str:
    """Redact userinfo and query values from a base URL for diagnostics."""
    parsed = urllib.parse.urlparse(base_url)
    hostname = parsed.hostname or ""
    port = parsed.port
    default_port = 443 if parsed.scheme == "https" else 80
    netloc = f"{hostname}:{port}" if port is not None and port != default_port else hostname
    redacted_query = ""
    if parsed.query:
        pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        redacted_query = "&".join(f"{key}=***" for key, _ in pairs)
    return urllib.parse.urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, redacted_query, ""))


class HttpDocumentStore:
    """Expose coordination documents through the existing v3 ops HTTP API."""

    def __init__(self, base_url: str, bearer_token: str = "") -> None:
        normalized_url = base_url.rstrip("/")
        parsed = urllib.parse.urlparse(normalized_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise StateBackendError(f"http document store url must be http(s): {base_url!r}")
        self._base_url = normalized_url
        self._bearer_token = bearer_token

    def get(self, ref: DocumentRef) -> StateRecord | None:
        path = self._path_for(ref)
        if ref.namespace == NS_COORD_APPROVALS:
            path = f"{path}?status=all"
        body, token = self._request("GET", path)
        return StateRecord(ref=ref, body=body, token=token)

    def put(
        self,
        ref: DocumentRef,
        body: dict[str, Any],
        *,
        expected: StateToken,
    ) -> StateToken:
        if ref.namespace == NS_COORD_EVENTS and ref.key == KEY_DOCUMENT:
            raise StateBackendError("coord events document is read-only")
        path = self._path_for(ref)
        _, token = self._request(
            "PUT",
            path,
            body=body,
            if_match=expected,
            send_if_match=True,
        )
        return token

    def append(self, ref: DocumentRef, item: dict[str, Any]) -> dict[str, Any]:
        self._path_for(ref)
        if ref.namespace != NS_COORD_HANDOFFS:
            raise StateBackendError("HTTP append is supported only for coord handoffs")
        body, _ = self._request("POST", _COORD_PATHS[NS_COORD_HANDOFFS], body=item)
        return body

    def list_prefix(
        self,
        org_id: str,
        workspace_id: str,
        namespace: str,
        *,
        prefix: str = "",
        limit: int = 100,
    ) -> list[DocumentRef]:
        self._path_for(
            DocumentRef(
                org_id=org_id,
                workspace_id=workspace_id,
                namespace=namespace,
                key=KEY_DOCUMENT,
            )
        )
        if limit <= 0 or (prefix and not KEY_DOCUMENT.startswith(prefix)):
            return []
        return [
            DocumentRef(
                org_id=org_id,
                workspace_id=workspace_id,
                namespace=namespace,
                key=KEY_DOCUMENT,
            )
        ]

    def delete(self, ref: DocumentRef, *, expected: StateToken) -> None:
        _ = expected
        self._path_for(ref)
        raise self._deferred_error(ref)

    def describe(self) -> dict[str, Any]:
        return {
            "backend": "http",
            "base_url": sanitize_base_url_for_describe(self._base_url),
            "namespaces": sorted(_COORD_PATHS),
        }

    def _path_for(self, ref: DocumentRef) -> str:
        path = _COORD_PATHS.get(ref.namespace) if ref.key == KEY_DOCUMENT else None
        if path is None:
            raise self._deferred_error(ref)
        return path

    def _deferred_error(self, ref: DocumentRef) -> StateBackendError:
        return StateBackendError(
            f"unsupported HTTP document {ref.namespace}/{ref.key}; generic /v3/state API is deferred"
        )

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        if extra:
            headers.update(extra)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        if_match: StateToken = None,
        send_if_match: bool = False,
    ) -> tuple[dict[str, Any], StateToken]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        extra_headers = {"If-Match": _format_if_match(if_match)} if send_if_match else None
        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=payload,
            headers=self._headers(extra_headers),
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
                raw = response.read()
                parsed = json.loads(raw.decode("utf-8")) if raw else {}
                if not isinstance(parsed, dict):
                    raise StateBackendError(f"HTTP document response must be an object for {path}")
                return parsed, _normalize_token(response.headers.get("ETag"))
        except urllib.error.HTTPError as exc:
            if exc.code == 412:
                raise StateConflictError(f"HTTP document conflict for {path}") from exc
            detail = exc.read().decode("utf-8", errors="replace")
            raise StateBackendError(f"HTTP document request failed ({exc.code}) for {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise StateBackendError(f"HTTP document request failed for {path}: {exc}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StateBackendError(f"invalid HTTP document response for {path}: {exc}") from exc


__all__ = ["HttpDocumentStore", "sanitize_base_url_for_describe"]
