#!/usr/bin/env python
"""JSON persistence for schedule policy and decisions."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

from metagit.core.scheduler.models import ScheduleDecision, SchedulePolicy
from metagit.core.scheduler.paths import decisions_file, policy_file, schedule_root

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment,misc]


class ScheduleStore:
    """Load/save ``policy.json`` and append ``decisions.jsonl`` under ``.metagit/schedule/``."""

    def __init__(self, session_root: str) -> None:
        self._session_root = session_root

    def ensure_dirs(self) -> None:
        """Create schedule persistence directories if needed."""
        schedule_root(self._session_root).mkdir(parents=True, exist_ok=True)

    def load_policy(self) -> SchedulePolicy | Exception:
        """Load schedule policy, returning defaults when the file is absent."""
        path = policy_file(self._session_root)
        try:
            if not path.is_file():
                return SchedulePolicy()
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return ValueError("invalid schedule policy document")
            return SchedulePolicy.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 — surface to callers
            return exc

    def save_policy(self, policy: SchedulePolicy) -> None | Exception:
        """Persist schedule policy to ``policy.json``."""
        path = policy_file(self._session_root)
        try:
            self.ensure_dirs()
            with self._file_lock(path):
                serialized = json.dumps(policy.model_dump(mode="json"), indent=2) + "\n"
                path.write_text(serialized, encoding="utf-8")
                with contextlib.suppress(OSError):
                    os.chmod(path, 0o600)
            return None
        except Exception as exc:  # noqa: BLE001
            return exc

    def append_decision(self, decision: ScheduleDecision) -> None | Exception:
        """Append one schedule decision to ``decisions.jsonl``."""
        path = decisions_file(self._session_root)
        try:
            self.ensure_dirs()
            line = json.dumps(decision.model_dump(mode="json"), sort_keys=False) + "\n"
            with path.open("a+", encoding="utf-8") as handle:
                if fcntl is not None:
                    with contextlib.suppress(OSError, AttributeError):
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    handle.write(line)
                    handle.flush()
                finally:
                    if fcntl is not None:
                        with contextlib.suppress(OSError, AttributeError):
                            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            with contextlib.suppress(OSError):
                os.chmod(path, 0o600)
            return None
        except Exception as exc:  # noqa: BLE001
            return exc

    def list_decisions(self, *, limit: int | None = None) -> list[ScheduleDecision] | Exception:
        """Load schedule decisions in file order (oldest first)."""
        path = decisions_file(self._session_root)
        try:
            if not path.is_file():
                return []
            rows: list[ScheduleDecision] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                raw = json.loads(stripped)
                if isinstance(raw, dict):
                    rows.append(ScheduleDecision.model_validate(raw))
            if limit is not None and limit >= 0:
                return rows[-limit:] if limit else []
            return rows
        except Exception as exc:  # noqa: BLE001
            return exc

    @contextlib.contextmanager
    def _file_lock(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+", encoding="utf-8") as handle:
            if fcntl is not None:
                with contextlib.suppress(OSError, AttributeError):
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    with contextlib.suppress(OSError, AttributeError):
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = ["ScheduleStore"]
