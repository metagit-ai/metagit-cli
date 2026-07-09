#!/usr/bin/env python
"""JSON persistence for task graphs with advisory file locks."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

from metagit.core.taskgraph.models import TaskGraph, TaskGraphIndex, TaskGraphIndexEntry
from metagit.core.taskgraph.paths import graph_file, graphs_dir, index_file, tasks_root

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment,misc]


class TaskGraphStore:
    """Load and save ``TaskGraph`` documents under ``.metagit/tasks/``."""

    def __init__(self, session_root: str) -> None:
        self._session_root = session_root

    def ensure_dirs(self) -> None:
        tasks_root(self._session_root).mkdir(parents=True, exist_ok=True)
        graphs_dir(self._session_root).mkdir(parents=True, exist_ok=True)

    def load(self, graph_id: str) -> TaskGraph | Exception:
        path = graph_file(self._session_root, graph_id)
        try:
            if not path.is_file():
                return FileNotFoundError(f"task graph not found: {graph_id}")
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return ValueError(f"invalid task graph document: {graph_id}")
            return TaskGraph.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 — surface to callers
            return exc

    def save(self, graph: TaskGraph) -> None | Exception:
        path = graph_file(self._session_root, graph.graph_id)
        try:
            self.ensure_dirs()
            with self._file_lock(path):
                serialized = json.dumps(graph.model_dump(mode="json"), indent=2) + "\n"
                path.write_text(serialized, encoding="utf-8")
                with contextlib.suppress(OSError):
                    os.chmod(path, 0o600)
            index_err = self._upsert_index(graph)
            if isinstance(index_err, Exception):
                return index_err
            return None
        except Exception as exc:  # noqa: BLE001
            return exc

    def list_graphs(self) -> list[TaskGraph] | Exception:
        try:
            self.ensure_dirs()
            rows: list[TaskGraph] = []
            for path in sorted(graphs_dir(self._session_root).glob("*.json")):
                loaded = self.load(path.stem)
                if isinstance(loaded, Exception):
                    return loaded
                rows.append(loaded)
            return rows
        except Exception as exc:  # noqa: BLE001
            return exc

    def load_index(self) -> TaskGraphIndex | Exception:
        path = index_file(self._session_root)
        try:
            if not path.is_file():
                return TaskGraphIndex()
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return TaskGraphIndex()
            return TaskGraphIndex.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            return exc

    def _upsert_index(self, graph: TaskGraph) -> None | Exception:
        path = index_file(self._session_root)
        try:
            with self._file_lock(path):
                index = TaskGraphIndex()
                if path.is_file():
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        index = TaskGraphIndex.model_validate(raw)
                entry = TaskGraphIndexEntry(
                    graph_id=graph.graph_id,
                    title=graph.title,
                    status=graph.status,
                    objective_id=graph.objective_id,
                    updated_at=graph.updated_at,
                )
                others = [row for row in index.graphs if row.graph_id != graph.graph_id]
                others.append(entry)
                others.sort(key=lambda row: row.graph_id)
                payload = TaskGraphIndex(graphs=others)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(payload.model_dump(mode="json"), indent=2) + "\n",
                    encoding="utf-8",
                )
                with contextlib.suppress(OSError):
                    os.chmod(path, 0o600)
            return None
        except Exception as exc:  # noqa: BLE001
            return exc

    @contextlib.contextmanager
    def _file_lock(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_suffix(path.suffix + ".lock")
        with lock_path.open("a+", encoding="utf-8") as handle:
            with contextlib.suppress(OSError, AttributeError):
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                with contextlib.suppress(OSError, AttributeError):
                    if fcntl is not None:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = ["TaskGraphStore"]
