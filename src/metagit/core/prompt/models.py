#!/usr/bin/env python
"""
Pydantic models for metagit prompt emission.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.workspace.agent_instructions import AgentInstructionLayer

PromptScope = Literal["workspace", "project", "repo"]
PromptKind = Literal[
    "instructions",
    "session-start",
    "catalog-edit",
    "health-preflight",
    "sync-safe",
    "subagent-handoff",
    "layout-change",
    "repo-enrich",
    "context-pack",
    "graph-discover",
    "graph-maintain",
]


class PromptCatalogEntry(BaseModel):
    """Metadata for one built-in prompt kind."""

    kind: PromptKind
    title: str
    description: str
    scopes: list[PromptScope]


class PromptEmitResult(BaseModel):
    """Emitted prompt for agents or humans."""

    ok: bool = True
    kind: PromptKind
    scope: PromptScope
    project_name: Optional[str] = None
    repo_name: Optional[str] = None
    definition_path: str = ""
    instruction_layers: list[AgentInstructionLayer] = Field(default_factory=list)
    text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
