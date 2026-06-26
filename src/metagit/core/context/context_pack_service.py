#!/usr/bin/env python
"""
Unified context pack assembly for tier 0 (map), tier 1 (map + repo cards),
and tier 2 (tier 1 + session digest, then touches session boundary).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.context.models import ContextPackResult
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.context.repo_card_service import RepoCardService
from metagit.core.context.session_digest_service import SessionDigestService
from metagit.core.context.workspace_map_service import WorkspaceMapService
from metagit.core.mcp.services.session_store import SessionStore


def _estimate_tokens(payload: ContextPackResult) -> int:
    """Rough token estimate: character length of JSON / 4, excluding prior estimate."""
    data = payload.model_dump(mode="python", exclude={"token_estimate"})
    return len(json.dumps(data, default=str)) // 4


class ContextPackService:
    """Build ``ContextPackResult`` envelopes for MCP/CLI context packs."""

    def __init__(
        self,
        map_service: Optional[WorkspaceMapService] = None,
        card_service: Optional[RepoCardService] = None,
    ) -> None:
        self._map = map_service or WorkspaceMapService()
        self._cards = card_service or RepoCardService()

    def pack(
        self,
        config: MetagitConfig,
        config_path: str,
        workspace_root: str,
        *,
        tier: Literal[0, 1, 2],
        session_root: Optional[str] = None,
        project_name: Optional[str] = None,
        repo_name: Optional[str] = None,
        active_project: Optional[str] = None,
        max_cards: int = 50,
        definition_root: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> ContextPackResult:
        """Assemble a context pack for tier 0, 1, or 2 (see module docstring)."""
        resolved_definition_root = definition_root or str(Path(config_path).expanduser().resolve().parent)
        resolved_session_root = session_root or resolved_definition_root
        map_result = self._map.build(
            config=config,
            config_path=config_path,
            workspace_root=workspace_root,
            active_project=active_project,
        )
        if tier == 0:
            base = ContextPackResult(
                tier=0,
                workspace_name=config.name,
                map=map_result,
                cards=None,
                digest=None,
                max_tokens=max_tokens,
            )
        elif tier == 1:
            card_rows = self._cards.build_many(
                config=config,
                workspace_root=workspace_root,
                definition_root=resolved_definition_root,
                project_name=project_name,
                repo_name=repo_name,
                max_cards=max_cards,
            )
            base = ContextPackResult(
                tier=1,
                workspace_name=config.name,
                map=map_result,
                cards=card_rows,
                digest=None,
                max_tokens=max_tokens,
            )
        else:
            card_rows = self._cards.build_many(
                config=config,
                workspace_root=workspace_root,
                definition_root=resolved_definition_root,
                project_name=project_name,
                repo_name=repo_name,
                max_cards=max_cards,
            )
            session_store = SessionStore(workspace_root=resolved_session_root)
            since = session_store.get_last_session_at()
            objectives_list = ObjectiveService(workspace_root=resolved_session_root).list().objectives
            active_oid = next(
                (o.id for o in objectives_list if o.status == "in_progress"),
                None,
            )
            digest = SessionDigestService.build(
                config=config,
                config_path=config_path,
                workspace_root=workspace_root,
                definition_root=resolved_definition_root,
                since=since,
                active_objective_id=active_oid,
            )
            base = ContextPackResult(
                tier=2,
                workspace_name=config.name,
                map=map_result,
                cards=card_rows,
                digest=digest,
                max_tokens=max_tokens,
            )
            session_store.touch_session()
        estimated = _estimate_tokens(base)
        dropped: list[str] = []
        if max_tokens is not None and max_tokens > 0 and estimated > max_tokens:
            if base.cards is not None:
                base.cards = None
                dropped.append("cards")
                estimated = _estimate_tokens(base)
            if estimated > max_tokens and base.digest is not None:
                base.digest = None
                dropped.append("digest")
                estimated = _estimate_tokens(base)
        return base.model_copy(
            update={
                "token_estimate": estimated,
                "dropped_sections": dropped,
            }
        )


__all__ = ["ContextPackService"]
