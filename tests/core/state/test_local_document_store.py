#!/usr/bin/env python
"""LocalDocumentStore path encoding and append tests."""

from __future__ import annotations

from pathlib import Path

from metagit.core.state.local_document import LocalDocumentStore
from metagit.core.state.plane import (
  KEY_DOCUMENT,
  NS_COORD_APPROVALS,
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

  store.put(ref, {"projects": []}, expected=None)

  path = tmp_path / ".metagit" / "state" / "catalog.workspace" / "document.json"
  assert path.is_file()


def test_ref_for_uses_store_identity(tmp_path: Path) -> None:
  store = LocalDocumentStore(
    str(tmp_path),
    org_id="org-test",
    workspace_id="workspace-test",
  )

  ref = store.ref_for("catalog.workspace", "catalog")

  assert ref.org_id == "org-test"
  assert ref.workspace_id == "workspace-test"
