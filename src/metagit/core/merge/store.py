#!/usr/bin/env python
"""JSON persistence for merge requests with advisory file locks."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

from metagit.core.merge.models import MergeQueue, MergeQueueEntry, MergeRequest
from metagit.core.merge.paths import merge_file, merges_root, queue_file

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment,misc]


class MergeStore:
    """Load and save ``MergeRequest`` documents under ``.metagit/merges/``."""

    def __init__(self, session_root: str) -> None:
        self._session_root = session_root

    def ensure_dirs(self) -> None:
        """Create merge persistence directories if needed."""
        merges_root(self._session_root).mkdir(parents=True, exist_ok=True)

    def load(self, merge_id: str) -> MergeRequest | Exception:
        """Load one merge request document by id."""
        path = merge_file(self._session_root, merge_id)
        try:
            if not path.is_file():
                return FileNotFoundError(f"merge request not found: {merge_id}")
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return ValueError(f"invalid merge request document: {merge_id}")
            return MergeRequest.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 — surface to callers
            return exc

    def save(self, request: MergeRequest) -> None | Exception:
        """Save one merge request document and upsert it into ``queue.json``."""
        path = merge_file(self._session_root, request.merge_id)
        try:
            self.ensure_dirs()
            with self._file_lock(path):
                serialized = json.dumps(request.model_dump(mode="json"), indent=2) + "\n"
                path.write_text(serialized, encoding="utf-8")
                with contextlib.suppress(OSError):
                    os.chmod(path, 0o600)
            queue_err = self._upsert_queue(request)
            if isinstance(queue_err, Exception):
                return queue_err
            return None
        except Exception as exc:  # noqa: BLE001
            return exc

    def list_merges(self) -> list[MergeRequest] | Exception:
        """Load all merge request documents in deterministic id order."""
        try:
            self.ensure_dirs()
            rows: list[MergeRequest] = []
            for path in sorted(merges_root(self._session_root).glob("*.json")):
                if path.name == "queue.json":
                    continue
                loaded = self.load(path.stem)
                if isinstance(loaded, Exception):
                    return loaded
                rows.append(loaded)
            return rows
        except Exception as exc:  # noqa: BLE001
            return exc

    def load_queue(self) -> MergeQueue | Exception:
        """Load the merge queue index, returning an empty queue when absent."""
        path = queue_file(self._session_root)
        try:
            if not path.is_file():
                return MergeQueue()
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return MergeQueue()
            return MergeQueue.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            return exc

    def save_queue(self, queue: MergeQueue) -> None | Exception:
        """Save the merge queue index."""
        path = queue_file(self._session_root)
        try:
            self.ensure_dirs()
            with self._file_lock(path):
                serialized = json.dumps(queue.model_dump(mode="json"), indent=2) + "\n"
                path.write_text(serialized, encoding="utf-8")
                with contextlib.suppress(OSError):
                    os.chmod(path, 0o600)
            return None
        except Exception as exc:  # noqa: BLE001
            return exc

    def _upsert_queue(self, request: MergeRequest) -> None | Exception:
        path = queue_file(self._session_root)
        try:
            with self._file_lock(path):
                queue = MergeQueue()
                if path.is_file():
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        queue = MergeQueue.model_validate(raw)
                entry = MergeQueueEntry(
                    merge_id=request.merge_id,
                    repository=request.repository,
                    status=request.status,
                    updated_at=request.updated_at,
                )
                others = [row for row in queue.merges if row.merge_id != request.merge_id]
                others.append(entry)
                others.sort(key=lambda row: row.merge_id)
                payload = MergeQueue(merges=others)
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


__all__ = ["MergeStore"]
