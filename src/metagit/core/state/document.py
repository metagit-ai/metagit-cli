#!/usr/bin/env python
"""DocumentStore protocol and record types for the central state plane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

StateToken = str | None


@dataclass(frozen=True)
class DocumentRef:
    org_id: str
    workspace_id: str
    namespace: str
    key: str


@dataclass(frozen=True)
class StateRecord:
    ref: DocumentRef
    body: dict[str, Any]
    token: StateToken


class DocumentStore(Protocol):
    def get(self, ref: DocumentRef) -> StateRecord | None: ...

    def put(
        self,
        ref: DocumentRef,
        body: dict[str, Any],
        *,
        expected: StateToken,
    ) -> StateToken: ...

    def append(self, ref: DocumentRef, item: dict[str, Any]) -> dict[str, Any]: ...

    def list_prefix(
        self,
        org_id: str,
        workspace_id: str,
        namespace: str,
        *,
        prefix: str = "",
        limit: int = 100,
    ) -> list[DocumentRef]: ...

    def delete(self, ref: DocumentRef, *, expected: StateToken) -> None: ...

    def describe(self) -> dict[str, Any]: ...
