#!/usr/bin/env python
"""DocumentStore factory for CAS / plane scenarios."""

from __future__ import annotations

from typing import Any, Literal

StateBackend = Literal["local", "memory", "http-stub"]


def build_document_store(
    backend: StateBackend = "memory",
    *,
    http_base_url: str | None = None,
) -> Any | None:
    """Return a DocumentStore for plane CAS scenarios.

    ``local`` returns None (ACL/task graph use on-disk JSON under the workspace).
    ``memory`` returns a fresh InMemoryDocumentStore.
    ``http-stub`` requires ``http_base_url`` from the state conftest stub server.
    """
    if backend == "local":
        return None
    if backend == "memory":
        # Warm context package first to avoid state.base ↔ context.__init__ cycle.
        import metagit.core.context  # noqa: F401
        from metagit.core.state.memory import InMemoryDocumentStore

        return InMemoryDocumentStore()
    if backend == "http-stub":
        if not http_base_url:
            raise ValueError("http-stub backend requires http_base_url")
        import metagit.core.context  # noqa: F401
        from metagit.core.state.http_document import HttpDocumentStore

        return HttpDocumentStore(http_base_url)
    raise ValueError(f"unknown state backend: {backend}")
