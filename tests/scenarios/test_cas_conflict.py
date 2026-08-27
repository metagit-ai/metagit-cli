#!/usr/bin/env python
"""S5 — remote-state CAS conflict via InMemoryDocumentStore."""

from __future__ import annotations

from pathlib import Path

import pytest

# Warm context before state.document / memory imports (circular package init).
import metagit.core.context  # noqa: F401
from metagit.core.state.document import DocumentRef
from metagit.core.state.errors import StateConflictError
from metagit.core.state.plane import KEY_DOCUMENT, NS_COORD_OBJECTIVES, default_org_id

from tests.scenarios.harness.diagnostics import ScenarioDiagnostics, assert_scenario
from tests.scenarios.harness.workspace import ScenarioWorkspace


def _objectives_ref(workspace_id: str = "ws-scenario") -> DocumentRef:
    return DocumentRef(
        org_id=default_org_id(),
        workspace_id=workspace_id,
        namespace=NS_COORD_OBJECTIVES,
        key=KEY_DOCUMENT,
    )


def test_cas_conflict_memory_store(tmp_path: Path, record_property) -> None:
    ws = ScenarioWorkspace.bootstrap(tmp_path, ready_nodes=0, state_backend="memory")
    diag = ScenarioDiagnostics(ws)
    store = ws.document_store()
    assert store is not None
    ref = _objectives_ref()

    token0 = store.put(ref, {"objectives": [{"id": "seed"}], "version": 0}, expected=None)
    record_a = store.get(ref)
    record_b = store.get(ref)
    assert record_a is not None and record_b is not None
    assert record_a.token == token0 == record_b.token
    diag.record(agent_id="agent-a", action="store.get", outcome="ok")
    diag.record(agent_id="agent-b", action="store.get", outcome="ok")

    token1 = store.put(
        ref,
        {"objectives": [{"id": "from-a"}], "version": 1},
        expected=token0,
    )
    diag.record(agent_id="agent-a", action="store.put", outcome="ok")

    with pytest.raises(StateConflictError):
        store.put(
            ref,
            {"objectives": [{"id": "from-b"}], "version": 1},
            expected=token0,
        )
    diag.record(agent_id="agent-b", action="store.put", outcome="conflict")

    fresh = store.get(ref)
    assert fresh is not None
    token2 = store.put(
        ref,
        {"objectives": [{"id": "from-b"}], "version": 2},
        expected=fresh.token,
    )
    diag.record(agent_id="agent-b", action="store.put", outcome="ok")

    final = store.get(ref)
    assert final is not None
    assert_scenario(
        final.body == {"objectives": [{"id": "from-b"}], "version": 2},
        diag,
        message="final document must match last successful writer",
        record_property=record_property,
    )
    assert_scenario(
        final.token == token2 != token1,
        diag,
        message="CAS tokens must advance after each successful put",
        record_property=record_property,
    )
    assert "objectives" in final.body


@pytest.mark.scenario_http
@pytest.mark.nightly
def test_cas_conflict_http_stub_placeholder() -> None:
    pytest.skip("HTTP stub CAS variant reserved for nightly; reuse tests/core/state/conftest.py")
