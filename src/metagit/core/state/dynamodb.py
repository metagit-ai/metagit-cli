#!/usr/bin/env python
"""DynamoDB DocumentStore backend (optional ``metagit-cli[state-dynamodb]`` extra)."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any

from metagit.core.state.document import DocumentRef, StateRecord, StateToken
from metagit.core.state.errors import StateBackendError, StateConflictError
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_HANDOFFS

_INSTALL_HINT = "install metagit-cli[state-dynamodb]"
_APPEND_RETRIES = 8


def _canonical_token(body: dict[str, Any]) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _pk(org_id: str, workspace_id: str) -> str:
    return f"ORG#{org_id}#WS#{workspace_id}"


def _sk(namespace: str, key: str) -> str:
    return f"NS#{namespace}#KEY#{key}"


def _sk_prefix(namespace: str, prefix: str) -> str:
    return f"NS#{namespace}#KEY#{prefix}"


def _parse_key_from_sk(sk: str, namespace: str) -> str | None:
    marker = f"NS#{namespace}#KEY#"
    if not sk.startswith(marker):
        return None
    return sk[len(marker) :]


def _is_conditional_failure(exc: BaseException) -> bool:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return False
    error = response.get("Error")
    if not isinstance(error, dict):
        return False
    return error.get("Code") == "ConditionalCheckFailedException"


class DynamoDocumentStore:
    """Single-table DynamoDB DocumentStore with conditional CAS writes."""

    def __init__(self, table: str, *, region: str = "", endpoint_url: str = "") -> None:
        if not table.strip():
            raise StateBackendError("DynamoDB state backend requires a non-empty table name")
        try:
            import boto3
        except ImportError as exc:
            raise StateBackendError(f"DynamoDB state backend requires boto3; {_INSTALL_HINT}") from exc

        self._table = table.strip()
        self._region = region.strip()
        self._endpoint_url = endpoint_url.strip()
        self._lock = threading.RLock()
        client_kwargs: dict[str, Any] = {}
        if self._region:
            client_kwargs["region_name"] = self._region
        if self._endpoint_url:
            client_kwargs["endpoint_url"] = self._endpoint_url
        self._client = boto3.client("dynamodb", **client_kwargs)
        # Capture ClientError class for typed handling without a hard top-level dep.
        from botocore.exceptions import ClientError

        self._client_error = ClientError

    def get(self, ref: DocumentRef) -> StateRecord | None:
        try:
            response = self._client.get_item(
                TableName=self._table,
                Key={
                    "pk": {"S": _pk(ref.org_id, ref.workspace_id)},
                    "sk": {"S": _sk(ref.namespace, ref.key)},
                },
                ConsistentRead=True,
            )
        except self._client_error as exc:
            raise StateBackendError(f"dynamodb get failed: {exc}") from exc
        item = response.get("Item")
        if not item:
            return None
        try:
            body = json.loads(item["body"]["S"])
            token = item["token"]["S"]
        except (KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StateBackendError(f"dynamodb item is corrupt for {ref.namespace}/{ref.key}") from exc
        if not isinstance(body, dict):
            raise StateBackendError(f"dynamodb body must be a JSON object for {ref.namespace}/{ref.key}")
        return StateRecord(ref=ref, body=body, token=token)

    def put(
        self,
        ref: DocumentRef,
        body: dict[str, Any],
        *,
        expected: StateToken,
    ) -> StateToken:
        token = _canonical_token(body)
        item = {
            "pk": {"S": _pk(ref.org_id, ref.workspace_id)},
            "sk": {"S": _sk(ref.namespace, ref.key)},
            "body": {"S": json.dumps(body, sort_keys=True, separators=(",", ":"))},
            "token": {"S": token},
            "updated_at": {"S": datetime.now(timezone.utc).isoformat()},
        }
        kwargs: dict[str, Any] = {
            "TableName": self._table,
            "Item": item,
        }
        if expected is None:
            kwargs["ConditionExpression"] = "attribute_not_exists(pk) AND attribute_not_exists(sk)"
        else:
            kwargs["ConditionExpression"] = "#tok = :expected"
            kwargs["ExpressionAttributeNames"] = {"#tok": "token"}
            kwargs["ExpressionAttributeValues"] = {":expected": {"S": expected}}
        try:
            self._client.put_item(**kwargs)
        except self._client_error as exc:
            if _is_conditional_failure(exc):
                raise StateConflictError(
                    f"state conflict for {ref.namespace}/{ref.key}: expected {expected!r}"
                ) from exc
            raise StateBackendError(f"dynamodb put failed: {exc}") from exc
        return token

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
        out: list[DocumentRef] = []
        exclusive_start_key: dict[str, Any] | None = None
        try:
            while len(out) < limit:
                kwargs: dict[str, Any] = {
                    "TableName": self._table,
                    "KeyConditionExpression": "pk = :pk AND begins_with(sk, :sk_prefix)",
                    "ExpressionAttributeValues": {
                        ":pk": {"S": _pk(org_id, workspace_id)},
                        ":sk_prefix": {"S": _sk_prefix(namespace, prefix)},
                    },
                    "ProjectionExpression": "sk",
                    "Limit": min(limit - len(out), 100),
                    "ConsistentRead": True,
                }
                if exclusive_start_key is not None:
                    kwargs["ExclusiveStartKey"] = exclusive_start_key
                response = self._client.query(**kwargs)
                for row in response.get("Items", []):
                    key = _parse_key_from_sk(row["sk"]["S"], namespace)
                    if key is None:
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
                exclusive_start_key = response.get("LastEvaluatedKey")
                if not exclusive_start_key:
                    break
        except self._client_error as exc:
            raise StateBackendError(f"dynamodb list_prefix failed: {exc}") from exc
        return out

    def delete(self, ref: DocumentRef, *, expected: StateToken) -> None:
        if expected is None:
            # Stored tokens are always non-empty strings; None never matches.
            raise StateConflictError(f"state conflict deleting {ref.namespace}/{ref.key}")
        try:
            self._client.delete_item(
                TableName=self._table,
                Key={
                    "pk": {"S": _pk(ref.org_id, ref.workspace_id)},
                    "sk": {"S": _sk(ref.namespace, ref.key)},
                },
                ConditionExpression="#tok = :expected",
                ExpressionAttributeNames={"#tok": "token"},
                ExpressionAttributeValues={":expected": {"S": expected}},
            )
        except self._client_error as exc:
            if _is_conditional_failure(exc):
                raise StateConflictError(f"state conflict deleting {ref.namespace}/{ref.key}") from exc
            raise StateBackendError(f"dynamodb delete failed: {exc}") from exc

    def describe(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "backend": "dynamodb",
            "table": self._table,
            "region": self._region,
        }
        if self._endpoint_url:
            info["endpoint_url"] = self._endpoint_url
        return info


__all__ = ["DynamoDocumentStore"]
