#!/usr/bin/env python
"""Agent execution manifest persistence."""

from __future__ import annotations

import json
from pathlib import Path

from metagit.core.coordination.models import AgentExecutionManifest
from metagit.core.coordination.paths import agent_manifest_file, agents_dir
from metagit.core.workspace.context_models import utc_now_iso


class AgentManifestService:
    """Read and write AgentExecutionManifest JSON under ``.metagit/agents/``."""

    def __init__(self, session_root: str) -> None:
        self._session_root = str(Path(session_root).expanduser().resolve())

    def write(self, manifest: AgentExecutionManifest) -> AgentExecutionManifest | Exception:
        try:
            payload = manifest.model_copy(
                update={"created_at": manifest.created_at or utc_now_iso()},
            )
            path = agent_manifest_file(self._session_root, payload.agent_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload.model_dump(mode="json"), indent=2) + "\n",
                encoding="utf-8",
            )
            return payload
        except Exception as exc:  # noqa: BLE001
            return exc

    def show(self, agent_id: str) -> AgentExecutionManifest | Exception:
        try:
            path = agent_manifest_file(self._session_root, agent_id)
            if not path.is_file():
                return FileNotFoundError(f"manifest not found for agent: {agent_id}")
            raw = json.loads(path.read_text(encoding="utf-8"))
            return AgentExecutionManifest.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            return exc

    def write_into_worktree(
        self,
        worktree_path: str | Path,
        manifest: AgentExecutionManifest,
    ) -> Path | Exception:
        try:
            target = Path(worktree_path) / ".metagit-agent.json"
            target.write_text(
                json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n",
                encoding="utf-8",
            )
            return target
        except Exception as exc:  # noqa: BLE001
            return exc

    def list_agent_ids(self) -> list[str] | Exception:
        try:
            directory = agents_dir(self._session_root)
            if not directory.is_dir():
                return []
            return sorted(path.stem for path in directory.glob("*.json"))
        except Exception as exc:  # noqa: BLE001
            return exc


__all__ = ["AgentManifestService"]
