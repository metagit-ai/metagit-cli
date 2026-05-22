#!/usr/bin/env python
"""
Unit tests for metagit.core.context.objective_service.ObjectiveService.
"""

import json
from pathlib import Path

import pytest

from metagit.core.context.models import Objective
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.context.objective_store import ObjectiveStore
from metagit.core.workspace.context_models import utc_now_iso


def _sample_objective(**kwargs: object) -> Objective:
    now = utc_now_iso()
    base = {
        "id": "alpha-one",
        "title": "Ship feature",
        "repos": ["demo/repo-a"],
        "created_at": now,
        "updated_at": now,
    }
    base.update(kwargs)
    return Objective.model_validate(base)


def test_list_returns_empty_when_no_file(tmp_path: Path) -> None:
    service = ObjectiveService(workspace_root=str(tmp_path))
    result = service.list()
    assert result.objectives == []


def test_upsert_persists_under_sessions(tmp_path: Path) -> None:
    service = ObjectiveService(workspace_root=str(tmp_path))
    obj = _sample_objective()
    saved = service.upsert(obj)

    store_path = ObjectiveStore(workspace_root=str(tmp_path)).path
    assert store_path.is_file()
    raw = json.loads(store_path.read_text(encoding="utf-8"))
    assert "objectives" in raw
    assert len(raw["objectives"]) == 1
    assert raw["objectives"][0]["id"] == saved.id


def test_get_and_list_roundtrip(tmp_path: Path) -> None:
    service = ObjectiveService(workspace_root=str(tmp_path))
    service.upsert(_sample_objective(id="one", title="First"))

    fetched = service.get("one")
    assert fetched is not None
    assert fetched.title == "First"

    assert len(service.list().objectives) == 1


def test_upsert_updates_existing_keeps_created_at(tmp_path: Path) -> None:
    service = ObjectiveService(workspace_root=str(tmp_path))
    first = service.upsert(_sample_objective(id="same", title="Old title"))
    second = service.upsert(
        _sample_objective(
            id="same",
            title="New title",
            repos=["demo/repo-b"],
            created_at="should-be-ignored",
            updated_at="should-be-ignored",
        )
    )

    assert second.created_at == first.created_at
    assert second.title == "New title"
    assert second.repos == ["demo/repo-b"]
    assert len(service.list().objectives) == 1


def test_complete_and_cancel(tmp_path: Path) -> None:
    service = ObjectiveService(workspace_root=str(tmp_path))
    service.upsert(_sample_objective(id="job", title="Work"))

    done = service.complete("job")
    assert done.status == "done"

    service.upsert(
        _sample_objective(id="job2", title="Other"),
    )
    cancelled = service.cancel("job2")
    assert cancelled.status == "cancelled"


def test_get_complete_cancel_reject_bad_id_slug(tmp_path: Path) -> None:
    service = ObjectiveService(workspace_root=str(tmp_path))
    with pytest.raises(ValueError):
        service.get("bad id")
    with pytest.raises(ValueError):
        service.complete("bad id")
    with pytest.raises(ValueError):
        service.cancel("../x")


def test_complete_missing_raises(tmp_path: Path) -> None:
    service = ObjectiveService(workspace_root=str(tmp_path))
    with pytest.raises(ValueError, match="not found"):
        service.complete("missing-id")


def test_objective_model_rejects_invalid_id() -> None:
    with pytest.raises(ValueError):
        _sample_objective(id="spaces not allowed")


def test_objective_model_rejects_blank_title() -> None:
    with pytest.raises(ValueError):
        _sample_objective(title="   ")


def test_objective_model_rejects_non_string_repo_entries() -> None:
    with pytest.raises(ValueError):
        Objective.model_validate(
            {
                "id": "x",
                "title": "t",
                "repos": [1],
                "created_at": utc_now_iso(),
                "updated_at": utc_now_iso(),
            }
        )
