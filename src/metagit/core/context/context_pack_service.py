#!/usr/bin/env python
"""
Unified context pack assembly for tier 0 (map) and tier 1 (map + repo cards).
"""

from __future__ import annotations

import json
from typing import Literal, Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.context.models import ContextPackResult
from metagit.core.context.repo_card_service import RepoCardService
from metagit.core.context.workspace_map_service import WorkspaceMapService


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
        tier: Literal[0, 1],
        project_name: Optional[str] = None,
        repo_name: Optional[str] = None,
        active_project: Optional[str] = None,
        max_cards: int = 50,
    ) -> ContextPackResult:
        """Assemble a context pack for ``tier`` 0 (map only) or 1 (map + cards)."""
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
            )
        else:
            card_rows = self._cards.build_many(
                config=config,
                workspace_root=workspace_root,
                project_name=project_name,
                repo_name=repo_name,
                max_cards=max_cards,
            )
            base = ContextPackResult(
                tier=1,
                workspace_name=config.name,
                map=map_result,
                cards=card_rows,
            )
        return base.model_copy(update={"token_estimate": _estimate_tokens(base)})


__all__ = ["ContextPackService"]
