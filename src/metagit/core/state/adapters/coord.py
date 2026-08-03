#!/usr/bin/env python
"""Adapt DocumentStore into coordination BackendBundle protocols."""

from __future__ import annotations

from pydantic import ValidationError

from metagit.core.context.models import (
    ApprovalRequest,
    HandoffItem,
    Objective,
    WorkspaceEventsResult,
)
from metagit.core.state.base import BackendBundle, StateToken
from metagit.core.state.document import DocumentRef, DocumentStore
from metagit.core.state.local import LocalFileBackend
from metagit.core.state.local_document import LocalDocumentStore
from metagit.core.state.plane import (
    KEY_DOCUMENT,
    NS_COORD_APPROVALS,
    NS_COORD_EVENTS,
    NS_COORD_HANDOFFS,
    NS_COORD_OBJECTIVES,
)


class _ObjectivesAdapter:
    def __init__(self, store: DocumentStore, org_id: str, workspace_id: str) -> None:
        self._store = store
        self._ref = DocumentRef(org_id, workspace_id, NS_COORD_OBJECTIVES, KEY_DOCUMENT)

    def load(self) -> tuple[list[Objective], StateToken]:
        record = self._store.get(self._ref)
        if record is None:
            return [], None
        raw = record.body.get("objectives")
        if not isinstance(raw, list):
            return [], record.token
        rows = [Objective.model_validate(item) for item in raw if isinstance(item, dict)]
        return rows, record.token

    def save(
        self,
        objectives: list[Objective],
        *,
        expected: StateToken,
    ) -> StateToken:
        body = {"objectives": [objective.model_dump(mode="json") for objective in objectives]}
        return self._store.put(self._ref, body, expected=expected)


class _HandoffsAdapter:
    def __init__(self, store: DocumentStore, org_id: str, workspace_id: str) -> None:
        self._store = store
        self._ref = DocumentRef(org_id, workspace_id, NS_COORD_HANDOFFS, KEY_DOCUMENT)

    def load(self) -> tuple[list[HandoffItem], StateToken]:
        record = self._store.get(self._ref)
        if record is None:
            return [], None
        raw = record.body.get("handoffs")
        if not isinstance(raw, list):
            return [], record.token
        rows = [HandoffItem.model_validate(item) for item in raw if isinstance(item, dict)]
        return rows, record.token

    def save(
        self,
        handoffs: list[HandoffItem],
        *,
        expected: StateToken,
    ) -> StateToken:
        body = {"handoffs": [handoff.model_dump(mode="json") for handoff in handoffs]}
        return self._store.put(self._ref, body, expected=expected)

    def append(self, item: HandoffItem) -> HandoffItem:
        returned = self._store.append(self._ref, item.model_dump(mode="json"))
        if isinstance(returned, dict) and returned.get("id"):
            try:
                return HandoffItem.model_validate(returned)
            except ValidationError:
                return item
        return item


class _ApprovalsAdapter:
    def __init__(self, store: DocumentStore, org_id: str, workspace_id: str) -> None:
        self._store = store
        self._ref = DocumentRef(org_id, workspace_id, NS_COORD_APPROVALS, KEY_DOCUMENT)

    def load(self) -> tuple[list[ApprovalRequest], StateToken]:
        record = self._store.get(self._ref)
        if record is None:
            return [], None
        raw = record.body.get("requests")
        if not isinstance(raw, list):
            return [], record.token
        rows = [ApprovalRequest.model_validate(item) for item in raw if isinstance(item, dict)]
        return rows, record.token

    def save(
        self,
        requests: list[ApprovalRequest],
        *,
        expected: StateToken,
    ) -> StateToken:
        body = {"requests": [request.model_dump(mode="json") for request in requests]}
        return self._store.put(self._ref, body, expected=expected)


class _EventsAdapter:
    def __init__(self, store: DocumentStore, org_id: str, workspace_id: str) -> None:
        self._store = store
        self._ref = DocumentRef(org_id, workspace_id, NS_COORD_EVENTS, KEY_DOCUMENT)
        description = store.describe()
        workspace_root = description.get("workspace_root")
        self._local_backend = (
            LocalFileBackend(str(workspace_root))
            if isinstance(store, LocalDocumentStore) and isinstance(workspace_root, str)
            else None
        )

    def list_events(self, *, since: str | None = None) -> WorkspaceEventsResult:
        if self._local_backend is not None:
            return self._local_backend.list_events(since=since)
        record = self._store.get(self._ref)
        if record is None:
            return WorkspaceEventsResult(events=[])
        raw = record.body.get("events")
        if not isinstance(raw, list):
            return WorkspaceEventsResult(events=[])
        events = [event for event in raw if isinstance(event, dict)]
        if since:
            events = [event for event in events if str(event.get("timestamp", "")) > since]
        return WorkspaceEventsResult.model_validate({"events": events})


def coord_bundle(
    store: DocumentStore,
    *,
    org_id: str,
    workspace_id: str,
) -> BackendBundle:
    """Construct coordination backends over one generic document store."""
    return BackendBundle(
        objectives_backend=_ObjectivesAdapter(store, org_id, workspace_id),
        handoffs_backend=_HandoffsAdapter(store, org_id, workspace_id),
        approvals_backend=_ApprovalsAdapter(store, org_id, workspace_id),
        events_backend=_EventsAdapter(store, org_id, workspace_id),
    )


__all__ = ["coord_bundle"]
