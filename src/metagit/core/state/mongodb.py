#!/usr/bin/env python
"""MongoDB DocumentStore backend (optional ``metagit-cli[state-mongodb]`` extra)."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import datetime, timezone
from typing import Any

from metagit.core.state.document import DocumentRef, StateRecord, StateToken
from metagit.core.state.errors import StateBackendError, StateConflictError
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_HANDOFFS

_INSTALL_HINT = "install metagit-cli[state-mongodb]"
_APPEND_RETRIES = 8


def _canonical_token(body: dict[str, Any]) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _composite_id(ref: DocumentRef) -> dict[str, str]:
    return {
        "org_id": ref.org_id,
        "workspace_id": ref.workspace_id,
        "namespace": ref.namespace,
        "key": ref.key,
    }


class MongoDocumentStore:
    """MongoDB DocumentStore with composite ``_id`` and conditional CAS writes."""

    def __init__(
        self,
        uri: str,
        database: str,
        collection: str = "metagit_state",
        *,
        client: Any | None = None,
    ) -> None:
        if not database.strip():
            raise StateBackendError("MongoDB state backend requires a non-empty database name")
        collection_name = collection.strip() or "metagit_state"
        self._uri = uri.strip()
        self._database = database.strip()
        self._collection_name = collection_name
        self._lock = threading.RLock()
        if client is None:
            try:
                from pymongo import MongoClient
            except ImportError as exc:
                raise StateBackendError(f"MongoDB state backend requires pymongo; {_INSTALL_HINT}") from exc
            if not self._uri:
                raise StateBackendError("MongoDB state backend requires a non-empty uri")
            self._client = MongoClient(self._uri)
        else:
            self._client = client
        self._collection = self._client[self._database][self._collection_name]

    @staticmethod
    def _is_duplicate_key_error(exc: BaseException) -> bool:
        try:
            from pymongo.errors import DuplicateKeyError
        except ImportError:
            return type(exc).__name__ == "DuplicateKeyError"
        return isinstance(exc, DuplicateKeyError) or type(exc).__name__ == "DuplicateKeyError"

    def get(self, ref: DocumentRef) -> StateRecord | None:
        try:
            doc = self._collection.find_one({"_id": _composite_id(ref)})
        except Exception as exc:
            raise StateBackendError(f"mongodb get failed: {exc}") from exc
        if doc is None:
            return None
        body = doc.get("body")
        token = doc.get("token")
        if not isinstance(body, dict) or not isinstance(token, str):
            raise StateBackendError(f"mongodb document is corrupt for {ref.namespace}/{ref.key}")
        return StateRecord(ref=ref, body=body, token=token)

    def put(
        self,
        ref: DocumentRef,
        body: dict[str, Any],
        *,
        expected: StateToken,
    ) -> StateToken:
        token = _canonical_token(body)
        doc_id = _composite_id(ref)
        payload = {
            "body": body,
            "token": token,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            if expected is None:
                try:
                    self._collection.insert_one({"_id": doc_id, **payload})
                except Exception as exc:
                    if not self._is_duplicate_key_error(exc):
                        raise
                    raise StateConflictError(
                        f"state conflict for {ref.namespace}/{ref.key}: expected {expected!r}"
                    ) from exc
                return token
            result = self._collection.find_one_and_update(
                {"_id": doc_id, "token": expected},
                {"$set": payload},
            )
            if result is None:
                raise StateConflictError(f"state conflict for {ref.namespace}/{ref.key}: expected {expected!r}")
            return token
        except StateConflictError:
            raise
        except Exception as exc:
            raise StateBackendError(f"mongodb put failed: {exc}") from exc

    def append(self, ref: DocumentRef, item: dict[str, Any]) -> dict[str, Any]:
        envelope = "handoffs" if ref.namespace == NS_COORD_HANDOFFS and ref.key == KEY_DOCUMENT else "items"
        with self._lock:
            for _ in range(_APPEND_RETRIES):
                current = self.get(ref)
                body = {envelope: []} if current is None else dict(current.body)
                items = body.get(envelope)
                if not isinstance(items, list):
                    items = []
                items = list(items) + [dict(item)]
                body[envelope] = items
                try:
                    self.put(ref, body, expected=None if current is None else current.token)
                except StateConflictError:
                    continue
                return dict(item)
        raise StateConflictError(f"state conflict appending to {ref.namespace}/{ref.key}")

    def list_prefix(
        self,
        org_id: str,
        workspace_id: str,
        namespace: str,
        *,
        prefix: str = "",
        limit: int = 100,
    ) -> list[DocumentRef]:
        if limit <= 0:
            return []
        query: dict[str, Any] = {
            "_id.org_id": org_id,
            "_id.workspace_id": workspace_id,
            "_id.namespace": namespace,
        }
        if prefix:
            query["_id.key"] = {"$regex": f"^{re.escape(prefix)}"}
        out: list[DocumentRef] = []
        try:
            cursor = self._collection.find(query, projection={"_id": 1}).limit(limit)
            for doc in cursor:
                doc_id = doc.get("_id")
                if not isinstance(doc_id, dict):
                    continue
                key = doc_id.get("key")
                if not isinstance(key, str):
                    continue
                if prefix and not key.startswith(prefix):
                    continue
                out.append(
                    DocumentRef(
                        org_id=org_id,
                        workspace_id=workspace_id,
                        namespace=namespace,
                        key=key,
                    )
                )
                if len(out) >= limit:
                    break
        except Exception as exc:
            raise StateBackendError(f"mongodb list_prefix failed: {exc}") from exc
        return out

    def delete(self, ref: DocumentRef, *, expected: StateToken) -> None:
        if expected is None:
            raise StateConflictError(f"state conflict deleting {ref.namespace}/{ref.key}")
        try:
            result = self._collection.find_one_and_delete({"_id": _composite_id(ref), "token": expected})
        except Exception as exc:
            raise StateBackendError(f"mongodb delete failed: {exc}") from exc
        if result is None:
            raise StateConflictError(f"state conflict deleting {ref.namespace}/{ref.key}")

    def describe(self) -> dict[str, Any]:
        # Never return uri — it may embed credentials.
        return {
            "backend": "mongodb",
            "database": self._database,
            "collection": self._collection_name,
        }


__all__ = ["MongoDocumentStore"]
