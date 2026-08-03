#!/usr/bin/env python
"""Coord adapters expose BackendBundle over DocumentStore."""

from __future__ import annotations

from metagit.core.context.models import ApprovalRequest, HandoffItem, Objective
from metagit.core.state.adapters.coord import coord_bundle
from metagit.core.state.document import DocumentRef
from metagit.core.state.local_document import LocalDocumentStore
from metagit.core.state.memory import InMemoryDocumentStore
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_EVENTS, NS_COORD_HANDOFFS
from metagit.core.workspace.context_models import utc_now_iso


def test_coord_bundle_objectives_round_trip() -> None:
    store = InMemoryDocumentStore()
    bundle = coord_bundle(store, org_id="_", workspace_id="ws")
    now = utc_now_iso()
    objective = Objective(
        id="o1",
        title="t",
        status="in_progress",
        repos=[],
        created_at=now,
        updated_at=now,
    )

    token = bundle.objectives().save([objective], expected=None)
    rows, loaded = bundle.objectives().load()

    assert len(rows) == 1
    assert rows[0].id == "o1"
    assert loaded == token


def test_coord_bundle_handoffs_append_uses_handoffs_envelope() -> None:
    store = InMemoryDocumentStore()
    bundle = coord_bundle(store, org_id="_", workspace_id="ws")
    now = utc_now_iso()
    item = HandoffItem(
        id="h1",
        title="Continue task",
        created_at=now,
        updated_at=now,
    )

    assert bundle.handoffs().append(item) == item
    rows, _ = bundle.handoffs().load()
    record = store.get(DocumentRef("_", "ws", NS_COORD_HANDOFFS, KEY_DOCUMENT))

    assert [row.id for row in rows] == ["h1"]
    assert record is not None
    assert list(record.body) == ["handoffs"]


def test_coord_handoffs_append_returns_server_normalized_body() -> None:
    """HTTP append must re-validate the store response when it includes id."""

    class _NormalizingStore(InMemoryDocumentStore):
        def append(self, ref, item):  # type: ignore[no-untyped-def]
            _ = super().append(ref, item)
            out = dict(item)
            out["title"] = "server-normalized"
            out["created_by"] = "ops-server"
            return out

    store = _NormalizingStore()
    bundle = coord_bundle(store, org_id="_", workspace_id="ws")
    now = utc_now_iso()
    item = HandoffItem(
        id="h1",
        title="client title",
        created_by="agent",
        created_at=now,
        updated_at=now,
    )

    saved = bundle.handoffs().append(item)

    assert saved.id == "h1"
    assert saved.title == "server-normalized"
    assert saved.created_by == "ops-server"


def test_coord_bundle_approvals_round_trip() -> None:
    store = InMemoryDocumentStore()
    bundle = coord_bundle(store, org_id="org", workspace_id="ws")
    request = ApprovalRequest(
        id="a1",
        action="deploy",
        created_at=utc_now_iso(),
    )

    token = bundle.approvals().save([request], expected=None)
    rows, loaded = bundle.approvals().load()

    assert [row.id for row in rows] == ["a1"]
    assert loaded == token


def test_coord_bundle_events_validates_dicts_and_filters_since() -> None:
    store = InMemoryDocumentStore()
    ref = DocumentRef("_", "ws", NS_COORD_EVENTS, KEY_DOCUMENT)
    store.put(
        ref,
        {
            "events": [
                {
                    "timestamp": "2026-07-31T10:00:00+00:00",
                    "source": "objective",
                    "kind": "pending",
                    "id": "old",
                },
                "not-an-event",
                {
                    "timestamp": "2026-07-31T11:00:00+00:00",
                    "source": "handoff",
                    "kind": "open",
                    "id": "new",
                    "data": {"title": "Continue task"},
                },
            ]
        },
        expected=None,
    )

    result = coord_bundle(store, org_id="_", workspace_id="ws").events().list_events(since="2026-07-31T10:30:00+00:00")

    assert [event.id for event in result.events] == ["new"]


def test_coord_bundle_local_events_use_derived_workspace_feed(tmp_path) -> None:
    store = LocalDocumentStore(str(tmp_path), org_id="_", workspace_id="ws")
    bundle = coord_bundle(store, org_id="_", workspace_id="ws")
    now = utc_now_iso()
    objective = Objective(
        id="derived-event",
        title="Derive this event",
        created_at=now,
        updated_at=now,
    )
    bundle.objectives().save([objective], expected=None)

    result = bundle.events().list_events()

    assert [event.id for event in result.events] == ["derived-event"]
