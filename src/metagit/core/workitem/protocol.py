#!/usr/bin/env python
"""Board/work-item provider protocol."""

from __future__ import annotations

from typing import Optional, Protocol

from metagit.core.workitem.models import ExternalWorkRef


class BoardProvider(Protocol):
    """Create and fetch work items without loading a full board into agent state."""

    def create_item(
        self,
        *,
        title: str,
        description: str,
        kind: str,
        parent: Optional[ExternalWorkRef] = None,
    ) -> ExternalWorkRef | Exception:
        """Create a work item and return its ref, or an Exception."""

    def get_item(self, ref: ExternalWorkRef) -> ExternalWorkRef | Exception:
        """Refresh a work item URL/id, or an Exception."""
