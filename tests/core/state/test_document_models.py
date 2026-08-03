#!/usr/bin/env python
"""Unit tests for DocumentRef and workspace id derivation."""

from __future__ import annotations

from pathlib import Path

from metagit.core.state.document import DocumentRef
from metagit.core.state.plane import (
    KEY_DOCUMENT,
    NS_COORD_OBJECTIVES,
    default_org_id,
    derive_workspace_id,
)


def test_document_ref_fields() -> None:
    ref = DocumentRef(
        org_id="acme",
        workspace_id="ws1",
        namespace=NS_COORD_OBJECTIVES,
        key=KEY_DOCUMENT,
    )
    assert ref.namespace == "coord.objectives"
    assert ref.key == "document"


def test_default_org_id() -> None:
    assert default_org_id() == "_"


def test_derive_workspace_id_stable(tmp_path: Path) -> None:
    root = tmp_path / "ws"
    root.mkdir()
    a = derive_workspace_id(str(root))
    b = derive_workspace_id(str(root.resolve()))
    assert a == b
    assert len(a) == 16
