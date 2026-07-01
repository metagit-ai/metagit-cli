#!/usr/bin/env python
"""State backend protocols and bundle type."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from metagit.core.context.models import (
    ApprovalRequest,
    HandoffItem,
    Objective,
    WorkspaceEventsResult,
)

StateToken = str | None


class ObjectiveBackend(Protocol):
    """Persist workspace objectives."""

    def load(self) -> tuple[list[Objective], StateToken]:
        """Return objectives and a concurrency token."""

    def save(
        self,
        objectives: list[Objective],
        *,
        expected: StateToken,
    ) -> StateToken:
        """Replace objectives when ``expected`` matches the current token."""


class HandoffBackend(Protocol):
    """Persist workspace handoffs."""

    def load(self) -> tuple[list[HandoffItem], StateToken]:
        """Return handoffs and a concurrency token."""

    def save(
        self,
        handoffs: list[HandoffItem],
        *,
        expected: StateToken,
    ) -> StateToken:
        """Replace handoffs when ``expected`` matches the current token."""

    def append(self, item: HandoffItem) -> HandoffItem:
        """Append one handoff without optimistic concurrency on the prior token."""


class ApprovalBackend(Protocol):
    """Persist the approval queue."""

    def load(self) -> tuple[list[ApprovalRequest], StateToken]:
        """Return approval requests and a concurrency token."""

    def save(
        self,
        requests: list[ApprovalRequest],
        *,
        expected: StateToken,
    ) -> StateToken:
        """Replace requests when ``expected`` matches the current token."""


class EventsBackend(Protocol):
    """Read-only workspace event feed."""

    def list_events(self, *, since: str | None = None) -> WorkspaceEventsResult:
        """Return events optionally filtered after ``since``."""


@dataclass(frozen=True)
class BackendBundle:
    """Resolved backends for one workspace root."""

    objectives_backend: ObjectiveBackend
    handoffs_backend: HandoffBackend
    approvals_backend: ApprovalBackend
    events_backend: EventsBackend

    def objectives(self) -> ObjectiveBackend:
        return self.objectives_backend

    def handoffs(self) -> HandoffBackend:
        return self.handoffs_backend

    def approvals(self) -> ApprovalBackend:
        return self.approvals_backend

    def events(self) -> EventsBackend:
        return self.events_backend
