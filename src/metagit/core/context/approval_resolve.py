#!/usr/bin/env python
"""
Resolve approval decisions and apply action-specific side effects.
"""

from __future__ import annotations

from typing import Literal, Union

from metagit.core.config.models import MetagitConfig
from metagit.core.context.approval_service import ApprovalService
from metagit.core.context.models import ApprovalRequest
from metagit.core.project.source_approval_executor import SourceSyncApprovalExecutor

Decision = Literal["approved", "denied"]


class ApprovalResolveOrchestrator:
    """Resolve approvals and run shared post-approve hooks for all modalities."""

    def resolve(
        self,
        *,
        workspace_root: str,
        config: MetagitConfig,
        config_path: str,
        request_id: str,
        decision: Decision,
        note: str | None = None,
    ) -> Union[ApprovalRequest, Exception]:
        """Resolve a pending approval and apply manifest mutations when approved."""
        service = ApprovalService(workspace_root=workspace_root)
        try:
            row = service.resolve(
                request_id=request_id,
                decision=decision,
                note=note,
            )
        except ValueError as exc:
            return exc

        if row.action == "source_sync_reconcile" and row.status == "approved":
            applied = SourceSyncApprovalExecutor().apply_if_approved(
                approval=row,
                config=config,
                config_path=config_path,
            )
            if isinstance(applied, Exception):
                return applied
        return row
