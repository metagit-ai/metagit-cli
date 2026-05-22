#!/usr/bin/env python
"""
CRUD-style operations for workspace objectives.
"""

import re
from typing import Optional

from metagit.core.context.models import Objective, ObjectiveListResult, ObjectiveStatus
from metagit.core.context.objective_store import ObjectiveStore
from metagit.core.workspace.context_models import utc_now_iso

_OBJECTIVE_ID_PATTERN = re.compile(r"^[\w.-]+$")


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

    def complete(self, objective_id: str) -> Objective:
        """Mark an objective done."""
        return self._set_status(objective_id=objective_id, status="done")

    def cancel(self, objective_id: str) -> Objective:
        """Mark an objective cancelled."""
        return self._set_status(objective_id=objective_id, status="cancelled")

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
