#!/usr/bin/env python
"""LocalDocumentStore path encoding and append tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from metagit.core.state.document import DocumentRef
from metagit.core.state.errors import StateBackendError
from metagit.core.state.local_document import LocalDocumentStore
from metagit.core.state.plane import (
  KEY_DOCUMENT,
  NS_COORD_APPROVALS,
  NS_COORD_EVENTS,
  NS_COORD_HANDOFFS,
  NS_COORD_OBJECTIVES,
  default_org_id,
)


def test_coord_objectives_uses_legacy_path(tmp_path: Path) -> None:
  store = LocalDocumentStore(str(tmp_path), org_id=default_org_id())
  ref = store.ref_for(NS_COORD_OBJECTIVES, KEY_DOCUMENT)

  store.put(ref, {"objectives": [{"id": "o1"}]}, expected=None)

  legacy = tmp_path / ".metagit" / "sessions" / "objectives.json"
  assert legacy.is_file()
  record = store.get(ref)
  assert record is not None
  assert record.body["objectives"][0]["id"] == "o1"


def test_coord_handoffs_append_uses_legacy_envelope(tmp_path: Path) -> None:
  store = LocalDocumentStore(str(tmp_path))
  ref = store.ref_for(NS_COORD_HANDOFFS, KEY_DOCUMENT)

  store.append(ref, {"id": "h1"})
  store.append(ref, {"id": "h2"})

  legacy = tmp_path / ".metagit" / "sessions" / "handoffs.json"
  assert legacy.is_file()
  record = store.get(ref)
  assert record is not None
  assert record.body == {"handoffs": [{"id": "h1"}, {"id": "h2"}]}


def test_coord_approvals_uses_legacy_path(tmp_path: Path) -> None:
  store = LocalDocumentStore(str(tmp_path))
  ref = store.ref_for(NS_COORD_APPROVALS, KEY_DOCUMENT)

  store.put(ref, {"requests": []}, expected=None)

  legacy = tmp_path / ".metagit" / "approvals" / "pending.json"
  assert legacy.is_file()


def test_generic_namespace_uses_state_dir(tmp_path: Path) -> None:
  store = LocalDocumentStore(str(tmp_path))
  ref = store.ref_for("catalog.workspace", KEY_DOCUMENT)

  body = {"projects": [{"id": "project-1"}]}
  token = store.put(ref, body, expected=None)

  path = tmp_path / ".metagit" / "state" / "catalog.workspace" / "document.json"
  assert path.is_file()
  record = store.get(ref)
  assert record is not None
  assert record.body == body
  assert record.token == token


@pytest.mark.parametrize(
  ("namespace", "key"),
  [
    ("../escape", KEY_DOCUMENT),
    ("/absolute", KEY_DOCUMENT),
    ("catalog/workspace", KEY_DOCUMENT),
    ("catalog\\workspace", KEY_DOCUMENT),
    ("catalog.workspace", "../escape"),
    ("catalog.workspace", "/absolute"),
    ("catalog.workspace", "nested/key"),
    ("catalog.workspace", "nested\\key"),
  ],
)
def test_invalid_document_ref_paths_are_rejected(
  tmp_path: Path,
  namespace: str,
  key: str,
) -> None:
  store = LocalDocumentStore(str(tmp_path))
  ref = DocumentRef(
    org_id=default_org_id(),
    workspace_id="workspace-test",
    namespace=namespace,
    key=key,
  )

  with pytest.raises(StateBackendError):
    store.put(ref, {"value": "unsafe"}, expected=None)


def test_events_document_is_read_only(tmp_path: Path) -> None:
  store = LocalDocumentStore(str(tmp_path))
  ref = store.ref_for(NS_COORD_EVENTS, KEY_DOCUMENT)

  with pytest.raises(StateBackendError, match="read-only"):
    store.put(ref, {"events": []}, expected=None)

  assert not (tmp_path / ".metagit" / "sessions" / "events.json").exists()


def test_ref_for_uses_store_identity(tmp_path: Path) -> None:
  store = LocalDocumentStore(
    str(tmp_path),
    org_id="org-test",
    workspace_id="workspace-test",
  )

  ref = store.ref_for("catalog.workspace", "catalog")

  assert ref.org_id == "org-test"
  assert ref.workspace_id == "workspace-test"
