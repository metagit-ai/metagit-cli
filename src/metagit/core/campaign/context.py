#!/usr/bin/env python
"""Assemble provenance-aware campaign context from MetaGit and optional providers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from metagit import __version__
from metagit.core.campaign.context_models import (
    CONTEXT_INCLUDE_CHOICES,
    CONTEXT_SCHEMA_VERSION,
    DEFAULT_CONTEXT_INCLUDES,
    CampaignContextResult,
    CampaignEnvelope,
    ContextLimits,
    EverRoomContextSlice,
    MetagitTechnicalContext,
    ProvenanceEntry,
    TechnicalRelationship,
    TechnicalRepository,
)
from metagit.core.campaign.everroom_provider import EverRoomCampaignContextProvider
from metagit.core.campaign.models import CampaignDocument
from metagit.core.campaign.service import CampaignService
from metagit.core.config.models import MetagitConfig
from metagit.core.integrations.everroom.client import EverRoomHttpClient
from metagit.core.integrations.everroom.source_identity import canonical_git_identity, identities_match
from metagit.core.mcp.services.repo_git_stats import inspect_repo_state
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.workspace.agent_instructions import AgentInstructionsResolver
from metagit.core.workspace.layout_resolver import find_project, find_repo


class CampaignContextService:
    """Resolve MetaGit technical scope plus optional EverRoom Room context."""

    def __init__(
        self,
        *,
        campaign_service: CampaignService,
        config: MetagitConfig,
        workspace_root: Path,
        definition_root: Path,
        endpoint: str = "http://127.0.0.1:3210",
        token: str = "",
        timeout_seconds: float = 8.0,
        client: Optional[EverRoomHttpClient] = None,
    ) -> None:
        self._campaigns = campaign_service
        self._config = config
        self._workspace_root = workspace_root
        self._definition_root = definition_root
        self._endpoint = endpoint
        self._token = token
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._index = WorkspaceIndexService()
        self._instructions = AgentInstructionsResolver()

    def resolve(
        self,
        slug: str,
        *,
        include: Optional[list[str]] = None,
        limits: Optional[ContextLimits] = None,
    ) -> CampaignContextResult:
        campaign = self._campaigns.load(slug)
        if campaign is None:
            raise ValueError(f"Unknown campaign: {slug!r}")
        selected = _normalize_includes(include)
        caps = limits or ContextLimits()
        technical = self._metagit_context(campaign, include=selected, limits=caps)
        everroom = EverRoomContextSlice(status="NOT_CONFIGURED")
        warnings: list[str] = []
        provider = campaign.everroom_provider()
        if provider is not None:
            client = self._client or EverRoomHttpClient(
                endpoint=provider.endpoint or self._endpoint,
                token=self._token,
                timeout_seconds=self._timeout_seconds,
            )
            bound = CampaignDocument.model_validate(campaign.model_dump())
            bound_provider = bound.everroom_provider()
            if bound_provider is not None and not bound_provider.endpoint:
                bound_provider.endpoint = self._endpoint
            adapter = EverRoomCampaignContextProvider(
                campaign=bound,
                config=bound.everroom_provider() or provider,
                client=client,
            )
            resolved = adapter.resolve(include=selected, limits=caps)
            everroom = resolved.slice
            if resolved.warning:
                warnings.append(resolved.warning)
            if everroom.status == "AVAILABLE":
                _apply_source_mappings(technical, everroom)
        provenance = [
            ProvenanceEntry(source="metagit", section="campaign"),
            ProvenanceEntry(source="metagit", section="technical"),
        ]
        if provider is not None:
            provenance.append(ProvenanceEntry(source="everroom", section="context"))
        return CampaignContextResult(
            context_schema_version=CONTEXT_SCHEMA_VERSION,
            campaign=CampaignEnvelope(
                id=campaign.slug,
                title=campaign.title,
                objective=campaign.goal,
                status=campaign.status,
                reference_impl=campaign.reference_impl,
            ),
            metagit=technical,
            everroom=everroom,
            provenance=provenance,
            includes=sorted(selected),
            warnings=warnings,
        )

    def _metagit_context(
        self,
        campaign: CampaignDocument,
        *,
        include: set[str],
        limits: ContextLimits,
    ) -> MetagitTechnicalContext:
        index_rows = {
            f"{row['project_name']}/{row['repo_name']}": row
            for row in self._index.build_index(
                self._config,
                str(self._workspace_root),
                definition_root=str(self._definition_root),
            )
        }
        repositories: list[TechnicalRepository] = []
        components: list[str] = []
        dirty = 0
        instructions: list[str] = []
        for entry in campaign.repos[: limits.repositories]:
            key = f"{entry.project}/{entry.repo}"
            project = find_project(self._config, entry.project)
            repo = find_repo(project, entry.repo) if project is not None else None
            url = str(repo.url) if repo is not None and repo.url else None
            identity = canonical_git_identity(url)
            row = index_rows.get(key, {})
            git_state: dict[str, object] = {}
            if "git_state" in include:
                repo_path = row.get("repo_path")
                if isinstance(repo_path, str) and repo_path:
                    git_state = inspect_repo_state(repo_path)
                    if git_state.get("dirty") is True:
                        dirty += 1
                elif row.get("exists") is False:
                    git_state = {"ok": False, "missing": True}
            elif row.get("exists") and isinstance(row.get("repo_path"), str):
                inspected = inspect_repo_state(str(row["repo_path"]))
                if inspected.get("dirty") is True:
                    dirty += 1
            repo_components = [item.name for item in (repo.components if repo is not None else [])]
            components.extend(f"{key}/{name}" for name in repo_components[: limits.components])
            if "instructions" in include and project is not None and repo is not None:
                composed = self._instructions.resolve(self._config, project=project, repo=repo)
                if composed.effective:
                    instructions.append(composed.effective[: limits.instructions_chars])
            repositories.append(
                TechnicalRepository(
                    project=entry.project,
                    repo=entry.repo,
                    role=entry.role,
                    status=entry.status,
                    url=url,
                    identity=identity,
                    components=repo_components,
                    git=git_state,
                ),
            )
        relationships: list[TechnicalRelationship] = []
        if "relationships" in include:
            relationships = _campaign_relationships(self._config, campaign, limits.relationships)
        return MetagitTechnicalContext(
            repository_count=len(campaign.repos),
            component_count=len(components),
            relationship_count=len(relationships),
            dirty_repository_count=dirty,
            repositories=repositories if "repositories" in include or "summary" in include else [],
            components=components[: limits.components] if "repositories" in include else [],
            relationships=relationships,
            instructions=instructions,
        )


def generated_document_id(slug: str) -> str:
    """Stable EverRoom document id for MetaGit-generated campaign context."""
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in slug)[:80]
    return f"metagit-campaign-{cleaned}"


def generated_document_markdown(result: CampaignContextResult) -> str:
    """One-way projection of MetaGit campaign state into a generated Room document."""
    lines = [
        "# Campaign Context",
        "",
        "Generated by MetaGit. This document is a derived technical projection.",
        "It is not authoritative over EverRoom evidence, decisions, or human-authored notes.",
        "",
        f"- Campaign ID: `{result.campaign.id}`",
        f"- Generated timestamp: `{datetime.now(timezone.utc).isoformat()}`",
        f"- MetaGit version: `{__version__}`",
        f"- Context schema: `{result.context_schema_version}`",
        "",
        "## Objective",
        "",
        result.campaign.objective or "_No campaign objective recorded._",
        "",
        "## Campaign Status",
        "",
        result.campaign.status,
        "",
        "## Technical Scope",
        "",
        "### Repositories",
        "",
    ]
    if not result.metagit.repositories:
        lines.append("- _None_")
    for repo in result.metagit.repositories:
        identity = repo.identity or "unmapped remote"
        lines.append(f"- `{repo.project}/{repo.repo}` ({repo.status}; {identity})")
    lines.extend(["", "### Components", ""])
    if not result.metagit.components:
        lines.append("- _None catalogued on campaign repos_")
    for component in result.metagit.components:
        lines.append(f"- `{component}`")
    lines.extend(["", "### Technical Relationships", ""])
    if not result.metagit.relationships:
        lines.append("- _None declared for campaign repos_")
    for rel in result.metagit.relationships:
        label = f" ({rel.label})" if rel.label else ""
        lines.append(f"- `{rel.from_ref}` {rel.type} `{rel.to_ref}`{label}")
    lines.extend(
        [
            "",
            "## Current MetaGit State",
            "",
            f"- Repositories: {result.metagit.repository_count}",
            f"- Components: {result.metagit.component_count}",
            f"- Relationships: {result.metagit.relationship_count}",
            f"- Dirty repositories: {result.metagit.dirty_repository_count}",
            "",
        ],
    )
    return "\n".join(lines) + "\n"


def _normalize_includes(include: Optional[list[str]]) -> set[str]:
    if not include:
        return set(DEFAULT_CONTEXT_INCLUDES)
    selected = {item.strip() for item in include if item and item.strip()}
    unknown = selected - set(CONTEXT_INCLUDE_CHOICES)
    if unknown:
        raise ValueError(f"Unknown campaign context include(s): {', '.join(sorted(unknown))}")
    selected.add("summary")
    return selected


def _campaign_relationships(
    config: MetagitConfig,
    campaign: CampaignDocument,
    limit: int,
) -> list[TechnicalRelationship]:
    if not config.graph or not config.graph.relationships:
        return []
    members = {f"{entry.project}/{entry.repo}" for entry in campaign.repos}
    collected: list[TechnicalRelationship] = []
    for rel in config.graph.relationships:
        from_ref = _endpoint_ref(rel.from_endpoint)
        to_ref = _endpoint_ref(rel.to)
        if from_ref not in members and to_ref not in members:
            continue
        collected.append(
            TechnicalRelationship(
                relationship_id=rel.id,
                type=rel.type,
                from_ref=from_ref,
                to_ref=to_ref,
                label=rel.label,
            ),
        )
        if len(collected) >= limit:
            break
    return collected


def _endpoint_ref(endpoint: object) -> str:
    project = getattr(endpoint, "project", None) or ""
    repo = getattr(endpoint, "repo", None) or ""
    component = getattr(endpoint, "component", None)
    if project and repo and component:
        return f"{project}/{repo}/{component}"
    if project and repo:
        return f"{project}/{repo}"
    return repo or project or "unknown"


def _apply_source_mappings(technical: MetagitTechnicalContext, everroom: EverRoomContextSlice) -> None:
    haystacks: list[tuple[str, str]] = []
    for source in everroom.sources:
        source_id = str(source.get("id") or "")
        haystack = str(source.get("identity") or "")
        haystacks.append((source_id, haystack))
    for repo in technical.repositories:
        mapped_id: Optional[str] = None
        if repo.identity:
            for source_id, haystack in haystacks:
                if identities_match(repo.identity, haystack):
                    mapped_id = source_id
                    break
        repo.everroom_source = mapped_id
        repo.mapping = "mapped" if mapped_id else "unmapped"
