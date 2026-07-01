#!/usr/bin/env python
"""
Approval queue: enqueue mutating operations and resolve human/agent decisions.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from metagit.core.context.approval_store import ApprovalStore
from metagit.core.context.models import (
    ApprovalListResult,
    ApprovalRequest,
    ApprovalStatus,
)
from metagit.core.state.retry import with_state_retry
from metagit.core.workspace.context_models import utc_now_iso

Decision = Literal["approved", "denied"]


class ApprovalService:
    """Create, list, and resolve approval rows for a workspace."""

    def __init__(self, workspace_root: str, store: Optional[ApprovalStore] = None) -> None:
        self._store = store or ApprovalStore(workspace_root=workspace_root)

    def request(
        self,
        action: str,
        payload: dict[str, Any],
        requested_by: str,
        idempotency_key: Optional[str] = None,
    ) -> ApprovalRequest:
        """Append a new pending approval and persist it."""

        def _run() -> ApprovalRequest:
            rows = self._store.load_requests()
            if idempotency_key:
                existing = next(
                    (
                        row
                        for row in rows
                        if row.status == "pending"
                        and row.action == action
                        and row.idempotency_key == idempotency_key
                        and row.requested_by == requested_by
                    ),
                    None,
                )
                if existing is not None:
                    return existing

            pending = ApprovalRequest(
                id=uuid.uuid4().hex,
                action=action,
                status="pending",
                requested_by=requested_by,
                idempotency_key=idempotency_key,
                payload=dict(payload),
                created_at=utc_now_iso(),
            )
            rows.append(pending)
            self._store.save_requests(rows)
            return pending

        return with_state_retry(_run)

    def list(self, status: Optional[ApprovalStatus] = None) -> ApprovalListResult:
        """Return stored requests, optionally filtered by ``status``."""
        rows = self._store.load_requests()
        if status is not None:
            rows = [row for row in rows if row.status == status]
        return ApprovalListResult(ok=True, requests=list(rows))

    def resolve(
        self,
        request_id: str,
        decision: Decision,
        note: Optional[str] = None,
    ) -> ApprovalRequest:
        """Mark a pending request approved or denied."""

        def _run() -> ApprovalRequest:
            rows = self._store.load_requests()
            idx = next((i for i, row in enumerate(rows) if row.id == request_id), None)
            if idx is None:
                raise ValueError(f"Approval request not found: {request_id}")
            row = rows[idx]
            if row.status != "pending":
                raise ValueError(f"Approval request is not pending: {request_id}")
            resolved = row.model_copy(
                update={
                    "status": decision,
                    "resolved_at": utc_now_iso(),
                    "resolver_note": note,
                }
            )
            rows[idx] = resolved
            self._store.save_requests(rows)
            return resolved

        return with_state_retry(_run)
