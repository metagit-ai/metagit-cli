#!/usr/bin/env python
"""
URI registry and parsing for Metagit MCP layered resources.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from metagit.core.mcp.models import McpActivationState
from metagit.core.mcp.resource_models import (
    DynamicUriPattern,
    ParsedResourceUri,
    ResourceCatalogResult,
    ResourceDescriptor,
)
from metagit.core.prompt.models import PromptKind, PromptScope

_STATIC_DESCRIPTORS: list[ResourceDescriptor] = [
    ResourceDescriptor(
        uri="metagit://catalog",
        name="Resource catalog",
        description="Index of resources, read order, and dynamic URI patterns.",
        estimated_tokens=400,
        gate="any",
    ),
    ResourceDescriptor(
        uri="metagit://gate/status",
        name="Gate status",
        description="MCP workspace activation state.",
        estimated_tokens=80,
        gate="any",
    ),
    ResourceDescriptor(
        uri="metagit://workspace/map",
        name="Workspace map (T0)",
        description="Projects, repos, clone existence — tier-0 map only.",
        estimated_tokens=300,
    ),
    ResourceDescriptor(
        uri="metagit://session/meta",
        name="Session metadata",
        description="Active project and project session notes from .metagit/sessions/.",
        estimated_tokens=150,
    ),
    ResourceDescriptor(
        uri="metagit://session/digest",
        name="Session digest (read-only)",
        description="Git activity since last session boundary; does not update the boundary.",
        estimated_tokens=400,
    ),
    ResourceDescriptor(
        uri="metagit://session/digest/summary",
        name="Session digest summary",
        description="Compact digest: first_session, manifest_changed, change counts.",
        estimated_tokens=120,
    ),
    ResourceDescriptor(
        uri="metagit://objectives",
        name="Objectives",
        description="Workspace objectives (id, status, title, repos); optional ?status= filter.",
        estimated_tokens=250,
    ),
    ResourceDescriptor(
        uri="metagit://approvals/pending",
        name="Pending approvals",
        description="Human-in-the-loop approval queue (pending only).",
        estimated_tokens=200,
    ),
    ResourceDescriptor(
        uri="metagit://handoffs/open",
        name="Open handoffs",
        description="Open and claimed multi-agent handoff items.",
        estimated_tokens=200,
    ),
    ResourceDescriptor(
        uri="metagit://events/recent",
        name="Recent workspace events",
        description="Poll feed of objective, approval, handoff changes; optional ?since= ISO cursor.",
        estimated_tokens=300,
    ),
    ResourceDescriptor(
        uri="metagit://prompt/catalog",
        name="Prompt catalog",
        description="Built-in prompt kinds and valid scopes (no prompt bodies).",
        estimated_tokens=200,
    ),
    ResourceDescriptor(
        uri="metagit://workspace/config",
        name="Workspace config",
        description="Manifest summary by default; use ?view=full for entire .metagit.yml.",
        estimated_tokens=250,
    ),
    ResourceDescriptor(
        uri="metagit://workspace/repos/status",
        name="Repos status",
        description="Workspace index rows; optional ?project= filter.",
        estimated_tokens=600,
    ),
    ResourceDescriptor(
        uri="metagit://workspace/health",
        name="Workspace health",
        description="Branch-age and integration staleness signals.",
        estimated_tokens=400,
    ),
    ResourceDescriptor(
        uri="metagit://workspace/context",
        name="Workspace context (alias)",
        description="Deprecated alias of metagit://session/meta.",
        estimated_tokens=150,
    ),
    ResourceDescriptor(
        uri="metagit://workspace/ops-log",
        name="Operations log",
        description="Audit trail of MCP tool calls; optional ?limit=N.",
        estimated_tokens=200,
        gate="any",
    ),
]

_DYNAMIC_PATTERNS: list[DynamicUriPattern] = [
    DynamicUriPattern(
        pattern="metagit://prompt/{scope}/{kind}",
        name="Operational prompt",
        description="Layered checklist; ?instructions=0 for template only.",
        mime_type="text/plain",
        estimated_tokens=350,
        example="metagit://prompt/workspace/session-start?instructions=0",
    ),
    DynamicUriPattern(
        pattern="metagit://project/{project}/summary",
        name="Project summary",
        description="Project row, repo list, missing-clone counts.",
        estimated_tokens=300,
        example="metagit://project/portfolio/summary",
    ),
    DynamicUriPattern(
        pattern="metagit://repo/{project}/{repo}/card",
        name="Repo card",
        description="Single tier-1 repo card with git health and stack hints.",
        estimated_tokens=450,
        example="metagit://repo/portfolio/api-gateway/card",
    ),
]

_READ_ORDER_ACTIVE: list[str] = [
    "metagit://catalog",
    "metagit://workspace/map",
    "metagit://prompt/workspace/session-start?instructions=0",
    "metagit://session/meta",
]

_PROMPT_KINDS: frozenset[str] = frozenset(
    {
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
    }
)

_PROMPT_SCOPES: frozenset[str] = frozenset({"workspace", "project", "repo"})


def parse_resource_uri(uri: str) -> ParsedResourceUri:
    """Parse a metagit:// URI into host, path, and query parameters."""
    parsed = urlparse(uri)
    host = parsed.netloc or ""
    path = parsed.path or ""
    query: dict[str, str] = {}
    for key, values in parse_qs(parsed.query, keep_blank_values=False).items():
        if values:
            query[key] = values[-1]
    return ParsedResourceUri(raw=uri, host=host, path=path, query=query)


def list_static_descriptors(*, gate_state: McpActivationState) -> list[ResourceDescriptor]:
    """Return static resource descriptors appropriate for the gate state."""
    active = gate_state == McpActivationState.ACTIVE
    rows: list[ResourceDescriptor] = []
    for item in _STATIC_DESCRIPTORS:
        if item.gate == "active" and not active:
            continue
        rows.append(item)
    return rows


def build_catalog_payload(*, gate_state: McpActivationState) -> ResourceCatalogResult:
    """Build the metagit://catalog JSON payload."""
    resources = list_static_descriptors(gate_state=gate_state)
    dynamic = list(_DYNAMIC_PATTERNS) if gate_state == McpActivationState.ACTIVE else []
    read_order = list(_READ_ORDER_ACTIVE) if gate_state == McpActivationState.ACTIVE else ["metagit://gate/status"]
    return ResourceCatalogResult(
        gate_state=gate_state,
        read_order=read_order,
        resources=resources,
        dynamic_patterns=dynamic,
        escalation={
            "scoped_work": [
                "metagit://project/{project}/summary",
                "metagit://repo/{project}/{repo}/card",
            ],
            "mutations": "Use MCP tools; read prompt/sync-safe before sync or catalog edits.",
            "session_boundary": "metagit_session_begin and metagit_context_pack tier 2 mutate sessions — not resources.",
        },
    )


def recommended_mcp_resources(
    *,
    project: str | None = None,
    repo: str | None = None,
    prompt_kind: str = "session-start",
    prompt_scope: str = "workspace",
) -> list[str]:
    """Return ordered MCP resource URIs for agent dispatch handoffs."""
    rows = [
        "metagit://catalog",
        "metagit://workspace/map",
    ]
    if project and repo:
        rows.extend(
            [
                f"metagit://project/{project}/summary",
                f"metagit://repo/{project}/{repo}/card",
                (f"metagit://prompt/{prompt_scope}/{prompt_kind}?project={project}&repo={repo}&instructions=0"),
            ]
        )
        return rows
    if project:
        rows.extend(
            [
                f"metagit://project/{project}/summary",
                (f"metagit://prompt/{prompt_scope}/{prompt_kind}?project={project}&instructions=0"),
            ]
        )
        return rows
    rows.extend(
        [
            f"metagit://prompt/workspace/{prompt_kind}?instructions=0",
            "metagit://session/meta",
        ]
    )
    return rows


def _path_segments(parsed: ParsedResourceUri) -> list[str]:
    return [segment for segment in parsed.path.strip("/").split("/") if segment]


def parse_prompt_uri(parsed: ParsedResourceUri) -> tuple[PromptScope, PromptKind] | None:
    """Return scope and kind when URI matches metagit://prompt/{scope}/{kind}."""
    if parsed.host != "prompt":
        return None
    segments = _path_segments(parsed)
    if len(segments) != 2:
        return None
    scope_raw, kind_raw = segments[0], segments[1]
    if scope_raw not in _PROMPT_SCOPES or kind_raw not in _PROMPT_KINDS:
        return None
    return scope_raw, kind_raw  # type: ignore[return-value]


def parse_project_summary_uri(parsed: ParsedResourceUri) -> str | None:
    """Return project name for metagit://project/{project}/summary."""
    if parsed.host != "project":
        return None
    segments = _path_segments(parsed)
    if len(segments) != 2 or segments[1] != "summary":
        return None
    project = segments[0].strip()
    return project or None


def parse_repo_card_uri(parsed: ParsedResourceUri) -> tuple[str, str] | None:
    """Return project and repo names for metagit://repo/{project}/{repo}/card."""
    if parsed.host != "repo":
        return None
    segments = _path_segments(parsed)
    if len(segments) != 3 or segments[2] != "card":
        return None
    project, repo = segments[0].strip(), segments[1].strip()
    if not project or not repo:
        return None
    return project, repo


def query_bool(value: str | None, *, default: bool) -> bool:
    """Parse a query flag as boolean."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"0", "false", "no", "off"}:
        return False
    if normalized in {"1", "true", "yes", "on"}:
        return True
    return default


def query_int(value: str | None, *, default: int | None = None) -> int | None:
    """Parse a positive integer query parameter."""
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except ValueError:
        return default
    return parsed if parsed > 0 else default


__all__ = [
    "build_catalog_payload",
    "list_static_descriptors",
    "parse_project_summary_uri",
    "parse_prompt_uri",
    "parse_repo_card_uri",
    "parse_resource_uri",
    "query_bool",
    "query_int",
    "recommended_mcp_resources",
]
