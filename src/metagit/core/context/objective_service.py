#!/usr/bin/env python
"""
CRUD-style operations for workspace objectives.
"""

import re
from pathlib import Path
from typing import Any, Optional

from metagit.core.context.models import Objective, ObjectiveListResult, ObjectiveStatus
from metagit.core.context.objective_store import ObjectiveStore
from metagit.core.state.retry import with_state_retry
from metagit.core.workspace.context_models import utc_now_iso

_OBJECTIVE_ID_PATTERN = re.compile(r"^[\w.-]+$")
_SKIP_MERGE_KEYS = frozenset({"id", "created_at", "updated_at"})
_HUMAN_NOTE_KEYS = ("left_off", "next", "blockers")


def _append_agent_note(existing: Optional[str], new: str) -> str:
    """Append a progress note, preserving prior agent_notes."""
    addition = new.strip()
    if not addition:
        return existing or ""
    if not existing or not str(existing).strip():
        return addition
    return f"{str(existing).rstrip()}\n{addition}"


def _stringify_note_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (list, tuple, set)):
        parts = [str(item).strip() for item in value if str(item).strip()]
        if not parts:
            return None
        return "; ".join(parts)
    text = str(value).strip()
    return text or None


def _synthesize_human_notes(data: dict[str, Any]) -> Optional[str]:
    left_off = _stringify_note_value(data.get("left_off"))
    next_steps = _stringify_note_value(data.get("next"))
    blockers = _stringify_note_value(data.get("blockers"))
    lines: list[str] = []
    if left_off:
        lines.append(f"LEFT OFF: {left_off}")
    if next_steps:
        lines.append(f"NEXT: {next_steps}")
    if blockers:
        lines.append(f"BLOCKERS: {blockers}")
    if not lines:
        return None
    return "\n".join(lines)


def _append_human_notes(existing: Optional[str], addition: Optional[str]) -> Optional[str]:
    if not addition:
        return existing
    existing_text = existing.strip() if isinstance(existing, str) else ""
    if not existing_text:
        return addition
    return f"{existing_text}\n{addition}"


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
        self._workspace_root = Path(workspace_root).expanduser().resolve()
        self._store = ObjectiveStore(workspace_root=workspace_root)

    def _normalize_repo_entry(self, repo: str) -> str:
        value = repo.strip()
        if not value:
            return repo

        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            return repo

        resolved = candidate.resolve(strict=False)
        try:
            relative = resolved.relative_to(self._workspace_root)
        except ValueError:
            return resolved.as_posix()

        if not relative.parts:
            return "."
        return f"./{relative.as_posix()}"

    def _normalize_repos(self, repos: Any) -> Any:
        if not isinstance(repos, list):
            return repos
        normalized: list[Any] = []
        for repo in repos:
            if isinstance(repo, str):
                normalized.append(self._normalize_repo_entry(repo))
                continue
            normalized.append(repo)
        return normalized

    def list(self) -> ObjectiveListResult:
        """Return all objectives."""
        return ObjectiveListResult(objectives=self._store.load_objectives())

    def select_resume_candidate(self, filter_text: str | None = None) -> Optional[Objective]:
        """Pick the best objective to resume, preferring active and recently updated."""
        objectives = self._store.load_objectives()
        needle = (filter_text or "").strip().lower()

        def _matches(row: Objective) -> bool:
            if not needle:
                return True
            haystacks = [
                row.id,
                row.title,
                "\n".join(row.repos or []),
                row.human_notes or "",
                row.agent_notes or "",
            ]
            return any(needle in value.lower() for value in haystacks)

        candidates = [row for row in objectives if _matches(row)]
        if not candidates:
            return None

        return max(
            candidates,
            key=lambda row: (
                1 if row.status == "in_progress" else 0,
                row.updated_at,
                row.created_at,
                row.id,
            ),
        )

    def get(self, objective_id: str) -> Optional[Objective]:
        """Return an objective by id, or None when not found."""
        self._validate_objective_id(objective_id=objective_id)
        for objective in self._store.load_objectives():
            if objective.id == objective_id:
                return objective
        return None

    def upsert(self, objective: Objective) -> Objective:
        """Insert or replace an objective by id."""

        def _run() -> Objective:
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

        return with_state_retry(_run)

    def upsert_partial(self, partial: dict[str, Any]) -> Objective:
        """Create or deep-merge an objective from a partial payload."""

        def _run() -> Objective:
            data = normalize_objective_partial(partial)
            synthesized_human_notes = _synthesize_human_notes(data)
            if "repos" in data:
                data["repos"] = self._normalize_repos(data.get("repos"))
            obj_id = str(data.get("id", "")).strip()
            if not obj_id:
                raise ValueError("objective id is required")
            self._validate_objective_id(objective_id=obj_id)

            objectives = self._store.load_objectives()
            existing = next((row for row in objectives if row.id == obj_id), None)
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
                        "human_notes": _append_human_notes(
                            data.get("human_notes") if isinstance(data.get("human_notes"), str) else None,
                            synthesized_human_notes,
                        ),
                        "agent_notes": data.get("agent_notes"),
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                objectives.append(created)
                self._store.save_objectives(objectives=objectives)
                return created

            merged = existing.model_dump(mode="json")
            for key, value in data.items():
                if key in _SKIP_MERGE_KEYS:
                    continue
                if key in _HUMAN_NOTE_KEYS:
                    continue
                if key == "agent_notes" and isinstance(value, str):
                    merged["agent_notes"] = _append_agent_note(
                        merged.get("agent_notes") if isinstance(merged.get("agent_notes"), str) else None,
                        value,
                    )
                    continue
                if key == "title":
                    if value is not None and str(value).strip():
                        merged["title"] = str(value).strip()
                    continue
                merged[key] = value
            merged["human_notes"] = _append_human_notes(
                merged.get("human_notes") if isinstance(merged.get("human_notes"), str) else None,
                synthesized_human_notes,
            )
            merged["updated_at"] = now
            updated = Objective.model_validate(merged)
            for index, row in enumerate(objectives):
                if row.id == obj_id:
                    objectives[index] = updated
                    self._store.save_objectives(objectives=objectives)
                    return updated
            raise ValueError(f"Objective not found: {obj_id}")

        return with_state_retry(_run)

    def complete(self, objective_id: str) -> Objective:
        """Mark an objective done."""
        return self._set_status(objective_id=objective_id, status="done")

    def cancel(self, objective_id: str) -> Objective:
        """Mark an objective cancelled."""
        return self._set_status(objective_id=objective_id, status="cancelled")

    def edit(self, objective_id: str, updates: dict[str, Any]) -> Objective:
        """Apply a partial objective update and refresh ``updated_at``."""

        def _run() -> Objective:
            data = dict(updates)
            synthesized_human_notes = _synthesize_human_notes(data)
            if "repos" in data:
                data["repos"] = self._normalize_repos(data.get("repos"))

            self._validate_objective_id(objective_id=objective_id)
            objectives = self._store.load_objectives()
            existing = next((row for row in objectives if row.id == objective_id), None)
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
            for key, value in data.items():
                if key not in allowed_keys or value is None:
                    continue
                if key == "title":
                    stripped = str(value).strip()
                    if not stripped:
                        continue
                    merged[key] = stripped
                    continue
                merged[key] = value

            merged["human_notes"] = _append_human_notes(
                merged.get("human_notes") if isinstance(merged.get("human_notes"), str) else None,
                synthesized_human_notes,
            )

            merged["updated_at"] = now
            updated = Objective.model_validate(merged)
            for index, row in enumerate(objectives):
                if row.id == objective_id:
                    objectives[index] = updated
                    self._store.save_objectives(objectives=objectives)
                    return updated
            raise ValueError(f"Objective not found: {objective_id}")

        return with_state_retry(_run)

    def _set_status(self, objective_id: str, status: ObjectiveStatus) -> Objective:
        def _run() -> Objective:
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

        return with_state_retry(_run)

    @staticmethod
    def _validate_objective_id(*, objective_id: str) -> None:
        if not _OBJECTIVE_ID_PATTERN.match(objective_id):
            raise ValueError("objective id must match slug pattern [alphanumeric, underscore, dot, hyphen]")
