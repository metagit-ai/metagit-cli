#!/usr/bin/env python
"""
CRUD-style operations for workspace objectives.
"""

import re
from typing import Any, Optional

from metagit.core.context.models import Objective, ObjectiveListResult, ObjectiveStatus
from metagit.core.context.objective_store import ObjectiveStore
from metagit.core.workspace.context_models import utc_now_iso

_OBJECTIVE_ID_PATTERN = re.compile(r"^[\w.-]+$")
_SKIP_MERGE_KEYS = frozenset({"id", "created_at", "updated_at"})


def _append_agent_note(existing: Optional[str], new: str) -> str:
    """Append a progress note, preserving prior agent_notes."""
    addition = new.strip()
    if not addition:
        return existing or ""
    if not existing or not str(existing).strip():
        return addition
    return f"{str(existing).rstrip()}\n{addition}"


def normalize_objective_partial(partial: dict[str, Any]) -> dict[str, Any]:
    """Map generic ``notes`` input to ``agent_notes`` when needed."""
    data = dict(partial)
    if "notes" in data:
        note_val = data.pop("notes")
        if "agent_notes" not in data and note_val is not None:
            data["agent_notes"] = note_val
    return data


class ObjectiveService:
    """List, fetch, upsert, and resolve objectives for a workspace."""

    def __init__(self, workspace_root: str) -> None:
        self._store = ObjectiveStore(workspace_root=workspace_root)

    def list(self) -> ObjectiveListResult:
        """Return all objectives."""
        return ObjectiveListResult(objectives=self._store.load_objectives())

    def get(self, objective_id: str) -> Optional[Objective]:
        """Return an objective by id, or None when not found."""
        self._validate_objective_id(objective_id=objective_id)
        for objective in self._store.load_objectives():
            if objective.id == objective_id:
                return objective
        return None

    def upsert(self, objective: Objective) -> Objective:
        """Insert or replace an objective by id."""
        objectives = self._store.load_objectives()
        now = utc_now_iso()
        for index, existing in enumerate(objectives):
            if existing.id == objective.id:
                updated = objective.model_copy(
                    update={
                        "created_at": existing.created_at,
                        "updated_at": now,
                    }
                )
                objectives[index] = updated
                self._store.save_objectives(objectives=objectives)
                return updated

        created = objective.model_copy(
            update={
                "created_at": now,
                "updated_at": now,
            }
        )
        objectives.append(created)
        self._store.save_objectives(objectives=objectives)
        return created

    def upsert_partial(self, partial: dict[str, Any]) -> Objective:
        """Create or deep-merge an objective from a partial payload."""
        data = normalize_objective_partial(partial)
        obj_id = str(data.get("id", "")).strip()
        if not obj_id:
            raise ValueError("objective id is required")
        self._validate_objective_id(objective_id=obj_id)

        existing = self.get(obj_id)
        now = utc_now_iso()
        if existing is None:
            title = str(data.get("title") or "").strip()
            if not title:
                raise ValueError("objective title is required for new objectives")
            created = Objective.model_validate(
                {
                    "id": obj_id,
                    "title": title,
                    "status": data.get("status") or "pending",
                    "repos": data.get("repos") if data.get("repos") is not None else [],
                    "acceptance": data.get("acceptance"),
                    "human_notes": data.get("human_notes"),
                    "agent_notes": data.get("agent_notes"),
                    "created_at": now,
                    "updated_at": now,
                }
            )
            objectives = self._store.load_objectives()
            objectives.append(created)
            self._store.save_objectives(objectives=objectives)
            return created

        merged = existing.model_dump(mode="json")
        for key, value in data.items():
            if key in _SKIP_MERGE_KEYS:
                continue
            if key == "agent_notes" and isinstance(value, str):
                merged["agent_notes"] = _append_agent_note(
                    merged.get("agent_notes")
                    if isinstance(merged.get("agent_notes"), str)
                    else None,
                    value,
                )
                continue
            if key == "title":
                if value is not None and str(value).strip():
                    merged["title"] = str(value).strip()
                continue
            merged[key] = value
        merged["updated_at"] = now
        updated = Objective.model_validate(merged)
        objectives = self._store.load_objectives()
        for index, row in enumerate(objectives):
            if row.id == obj_id:
                objectives[index] = updated
                self._store.save_objectives(objectives=objectives)
                return updated
        raise ValueError(f"Objective not found: {obj_id}")

    def complete(self, objective_id: str) -> Objective:
        """Mark an objective done."""
        return self._set_status(objective_id=objective_id, status="done")

    def cancel(self, objective_id: str) -> Objective:
        """Mark an objective cancelled."""
        return self._set_status(objective_id=objective_id, status="cancelled")

    def edit(self, objective_id: str, updates: dict[str, Any]) -> Objective:
        """Apply a partial objective update and refresh ``updated_at``."""
        self._validate_objective_id(objective_id=objective_id)
        existing = self.get(objective_id)
        if existing is None:
            raise ValueError(f"Objective not found: {objective_id}")

        merged = existing.model_dump(mode="json")
        now = utc_now_iso()
        allowed_keys = {
            "status",
            "title",
            "repos",
            "acceptance",
            "human_notes",
            "agent_notes",
        }
        for key, value in updates.items():
            if key not in allowed_keys or value is None:
                continue
            if key == "title":
                stripped = str(value).strip()
                if not stripped:
                    continue
                merged[key] = stripped
                continue
            merged[key] = value

        merged["updated_at"] = now
        updated = Objective.model_validate(merged)
        objectives = self._store.load_objectives()
        for index, row in enumerate(objectives):
            if row.id == objective_id:
                objectives[index] = updated
                self._store.save_objectives(objectives=objectives)
                return updated
        raise ValueError(f"Objective not found: {objective_id}")

    def _set_status(self, objective_id: str, status: ObjectiveStatus) -> Objective:
        self._validate_objective_id(objective_id=objective_id)
        objectives = self._store.load_objectives()
        now = utc_now_iso()
        for index, objective in enumerate(objectives):
            if objective.id == objective_id:
                updated = objective.model_copy(
                    update={
                        "status": status,
                        "updated_at": now,
                    }
                )
                objectives[index] = updated
                self._store.save_objectives(objectives=objectives)
                return updated
        raise ValueError(f"Objective not found: {objective_id}")

    @staticmethod
    def _validate_objective_id(*, objective_id: str) -> None:
        if not _OBJECTIVE_ID_PATTERN.match(objective_id):
            raise ValueError(
                "objective id must match slug pattern "
                "[alphanumeric, underscore, dot, hyphen]"
            )
