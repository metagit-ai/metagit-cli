#!/usr/bin/env python
"""
Compose a deterministic session-start envelope for CLI and MCP callers.
"""

from __future__ import annotations

from typing import Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.context.approval_service import ApprovalService
from metagit.core.context.context_pack_service import ContextPackService
from metagit.core.context.models import SessionBeginResult
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.prompt.service import PromptService, PromptServiceError


class SessionBeginService:
    """Build one payload for session bootstrap in agent workflows."""

    def __init__(self) -> None:
        self._pack = ContextPackService()
        self._prompt = PromptService()

    def begin(
        self,
        *,
        config: MetagitConfig,
        config_path: str,
        workspace_root: str,
        session_root: str,
        definition_root: str,
        project_name: Optional[str] = None,
        repo_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> SessionBeginResult:
        store = SessionStore(workspace_root=session_root)
        meta = store.get_workspace_meta()
        active_project = project_name or meta.active_project

        pack = self._pack.pack(
            config=config,
            config_path=config_path,
            workspace_root=workspace_root,
            session_root=session_root,
            definition_root=definition_root,
            tier=2,
            project_name=active_project,
            repo_name=repo_name,
            max_tokens=max_tokens,
        )

        warnings: list[str] = []
        if pack.dropped_sections:
            warnings.append(
                "token budget reached; dropped: " + ", ".join(pack.dropped_sections)
            )

        prompt_text = ""
        try:
            prompt_text = self._prompt.emit(
                config,
                kind="session-start",
                scope="workspace",
                definition_path=config_path,
                workspace_root=workspace_root,
                include_instructions=True,
            ).text
        except PromptServiceError as exc:
            warnings.append(f"session-start prompt unavailable: {exc}")

        objectives = ObjectiveService(workspace_root=session_root).list().objectives
        approvals = ApprovalService(workspace_root=session_root).list(
            status="pending"
        ).requests

        project_session = None
        if active_project:
            try:
                project_session = store.get_project_session(project_name=active_project)
            except ValueError:
                warnings.append(
                    f"active project is not a valid session key: {active_project}"
                )

        session_payload = {
            "workspace_meta": meta.model_dump(mode="json"),
            "project_session": (
                project_session.model_dump(mode="json") if project_session else None
            ),
        }

        return SessionBeginResult(
            workspace_name=config.name,
            active_project=active_project,
            session=session_payload,
            objectives=objectives,
            approvals=approvals,
            handoffs=[],
            pack=pack,
            prompt=prompt_text,
            warnings=warnings,
        )
