#!/usr/bin/env python
"""In-memory DocumentStore for tests and ephemeral plane backends."""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

from metagit.core.state.base import StateToken
from metagit.core.state.document import DocumentRef, StateRecord
from metagit.core.state.errors import StateConflictError
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_HANDOFFS


def _canonical_token(body: dict[str, Any]) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _ref_key(ref: DocumentRef) -> tuple[str, str, str, str]:
    return (ref.org_id, ref.workspace_id, ref.namespace, ref.key)


class InMemoryDocumentStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._docs: dict[tuple[str, str, str, str], tuple[dict[str, Any], str]] = {}

    def get(self, ref: DocumentRef) -> StateRecord | None:
        with self._lock:
            row = self._docs.get(_ref_key(ref))
            if row is None:
                return None
            body, token = row
            return StateRecord(ref=ref, body=dict(body), token=token)

    def put(
        self,
        ref: DocumentRef,
        body: dict[str, Any],
        *,
        expected: StateToken,
    ) -> StateToken:
        with self._lock:
            key = _ref_key(ref)
            current = self._docs.get(key)
            current_token = None if current is None else current[1]
            if current_token != expected:
                raise StateConflictError(
                    f"state conflict for {ref.namespace}/{ref.key}: expected {expected!r}, have {current_token!r}"
                )
            token = _canonical_token(body)
            self._docs[key] = (dict(body), token)
            return token

    def append(self, ref: DocumentRef, item: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            key = _ref_key(ref)
            current = self._docs.get(key)
            envelope = "handoffs" if ref.namespace == NS_COORD_HANDOFFS and ref.key == KEY_DOCUMENT else "items"
            body = {envelope: []} if current is None else dict(current[0])
            items = body.get(envelope)
            if not isinstance(items, list):
                items = []
            items = list(items) + [dict(item)]
            body[envelope] = items
            token = _canonical_token(body)
            self._docs[key] = (body, token)
            return dict(item)

    def list_prefix(
        self,
        org_id: str,
        workspace_id: str,
        namespace: str,
        *,
        prefix: str = "",
        limit: int = 100,
    ) -> list[DocumentRef]:
        with self._lock:
            out: list[DocumentRef] = []
            for o, w, ns, k in sorted(self._docs.keys()):
                if o != org_id or w != workspace_id or ns != namespace:
                    continue
                if prefix and not k.startswith(prefix):
                    continue
                out.append(DocumentRef(org_id=o, workspace_id=w, namespace=ns, key=k))
                if len(out) >= limit:
                    break
            return out

    def delete(self, ref: DocumentRef, *, expected: StateToken) -> None:
        with self._lock:
            key = _ref_key(ref)
            current = self._docs.get(key)
            current_token = None if current is None else current[1]
            if current is None or current_token != expected:
                raise StateConflictError(f"state conflict deleting {ref.namespace}/{ref.key}")
            del self._docs[key]

    def describe(self) -> dict[str, Any]:
        with self._lock:
            return {"backend": "memory", "document_count": len(self._docs)}
