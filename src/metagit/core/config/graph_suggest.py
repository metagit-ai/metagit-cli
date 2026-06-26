#!/usr/bin/env python
"""Suggest graph.relationships candidates from inferred workspace dependencies."""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.config.graph_models import GraphEndpoint, GraphRelationship
from metagit.core.config.graph_resolver import resolve_graph_endpoint_id
from metagit.core.config.models import MetagitConfig
from metagit.core.config.patch_service import ConfigPatchService
from metagit.core.mcp.services.cross_project_dependencies import (
    CrossProjectDependencyService,
)
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.web.models import ConfigOperation, ConfigOpKind

ConfidenceLevel = Literal["high", "medium", "low", "all"]
MinConfidence = Literal["high", "medium", "all"]

_PROMOTABLE_DEFAULT = frozenset({"imports", "shared_config", "url_match"})
_REQUEST_TO_EDGE_TYPE = {
    "imports": "import",
    "declared": "declared",
    "ref": "ref",
    "shared_config": "shared_config",
    "url_match": "url_match",
}
_EDGE_TO_REL_TYPE = {
    "import": "depends_on",
    "shared_config": "related",
    "url_match": "related",
    "declared": "depends_on",
    "ref": "depends_on",
}
_CONFIDENCE_BY_EDGE = {
    "import": "high",
    "shared_config": "medium",
    "url_match": "medium",
    "declared": "low",
    "ref": "low",
}
_CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1, "all": 0}


class SuggestedGraphRelationship(BaseModel):
    """Candidate relationship to promote into graph.relationships."""

    id: str
    from_endpoint: GraphEndpoint
    to_endpoint: GraphEndpoint
    type: str = "depends_on"
    label: Optional[str] = None
    description: Optional[str] = None
    tags: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: ConfidenceLevel = "medium"
    source_edge_type: str = ""
    evidence: list[str] = Field(default_factory=list)


class GraphSuggestApplyResult(BaseModel):
    """Outcome when applying suggested relationships to the manifest."""

    ok: bool = True
    saved: bool = False
    applied_count: int = 0
    validation_errors: list[dict[str, str]] = Field(default_factory=list)


class GraphSuggestResult(BaseModel):
    """Suggest graph.relationships from inferred cross-project edges."""

    ok: bool = True
    workspace_name: str = ""
    candidates: list[SuggestedGraphRelationship] = Field(default_factory=list)
    already_manual: list[str] = Field(default_factory=list)
    skipped_low_confidence: int = 0
    operations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    apply: GraphSuggestApplyResult | None = None


def node_id_to_endpoint(node_id: str) -> GraphEndpoint | None:
    """Map dependency node id to a graph endpoint."""
    if node_id.startswith("project:"):
        project = node_id.split(":", 1)[1]
        return None if project == "local" else GraphEndpoint(project=project)
    if node_id.startswith("repo:"):
        body = node_id.split(":", 1)[1]
        if "/" not in body:
            return None
        project, repo = body.split("/", 1)
        return GraphEndpoint(project=project, repo=repo)
    return None


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "node"


def _relationship_signature(
    from_endpoint: GraphEndpoint,
    to_endpoint: GraphEndpoint,
    rel_type: str,
) -> tuple[str, str, str, str, str]:
    return (
        from_endpoint.project or "",
        from_endpoint.repo or "",
        to_endpoint.project or "",
        to_endpoint.repo or "",
        rel_type,
    )


class GraphRelationshipSuggestService:
    """Discover inferred edges and propose durable graph.relationships entries."""

    def __init__(
        self,
        dependency_service: Optional[CrossProjectDependencyService] = None,
        patch_service: Optional[ConfigPatchService] = None,
        index_service: Optional[WorkspaceIndexService] = None,
    ) -> None:
        self._dependencies = dependency_service or CrossProjectDependencyService()
        self._patch = patch_service or ConfigPatchService()
        self._index = index_service or WorkspaceIndexService()

    def suggest(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        dependency_types: Optional[list[str]] = None,
        depth: int = 3,
        min_confidence: MinConfidence = "medium",
        include_declared: bool = False,
        candidate_ids: Optional[list[str]] = None,
    ) -> GraphSuggestResult:
        """Return candidate relationships not already present in graph.relationships."""
        if not config.workspace or not config.workspace.projects:
            return GraphSuggestResult(
                ok=False,
                warnings=["workspace_not_configured"],
            )

        selected_types = self._resolve_dependency_types(
            dependency_types=dependency_types,
            include_declared=include_declared,
        )
        rows = self._index.build_index(
            config=config,
            workspace_root=workspace_root,
        )
        project_names = {project.name for project in config.workspace.projects}
        manual_signatures = self._manual_signatures(
            config=config,
            rows=rows,
            project_names=project_names,
        )

        allowed_edge_types = {_REQUEST_TO_EDGE_TYPE.get(item, item) for item in selected_types}
        merged_edges: dict[tuple[str, str, str], Any] = {}
        for project in config.workspace.projects:
            result = self._dependencies.map_dependencies(
                config=config,
                workspace_root=workspace_root,
                source_project=project.name,
                dependency_types=sorted(selected_types),
                depth=max(1, depth),
            )
            if not result.ok:
                continue
            for edge in result.edges:
                if edge.type == "manual":
                    continue
                if edge.type not in allowed_edge_types:
                    continue
                key = (edge.from_id, edge.to_id, edge.type)
                if key not in merged_edges:
                    merged_edges[key] = edge
                    continue
                existing = merged_edges[key]
                combined = list(dict.fromkeys(existing.evidence + edge.evidence))
                existing.evidence = combined

        candidates: list[SuggestedGraphRelationship] = []
        already_manual: list[str] = []
        skipped_low_confidence = 0
        min_rank = _CONFIDENCE_ORDER[min_confidence]

        for edge in merged_edges.values():
            from_endpoint = node_id_to_endpoint(edge.from_id)
            to_endpoint = node_id_to_endpoint(edge.to_id)
            if from_endpoint is None or to_endpoint is None:
                continue

            rel_type = _EDGE_TO_REL_TYPE.get(edge.type, "related")
            signature = _relationship_signature(from_endpoint, to_endpoint, rel_type)
            if signature in manual_signatures:
                already_manual.append(f"{edge.from_id}->{edge.to_id}:{rel_type}")
                continue

            confidence = _CONFIDENCE_BY_EDGE.get(edge.type, "low")
            if _CONFIDENCE_ORDER[confidence] < min_rank:
                skipped_low_confidence += 1
                continue

            rel_id = self._build_relationship_id(
                from_endpoint=from_endpoint,
                to_endpoint=to_endpoint,
                rel_type=rel_type,
            )
            candidate = SuggestedGraphRelationship(
                id=rel_id,
                from_endpoint=from_endpoint,
                to_endpoint=to_endpoint,
                type=rel_type,
                label=rel_type.replace("_", " "),
                description="; ".join(edge.evidence) if edge.evidence else None,
                tags={"source": edge.type},
                metadata={"promoted_from": edge.type, "evidence": edge.evidence},
                confidence=confidence,
                source_edge_type=edge.type,
                evidence=list(edge.evidence),
            )
            candidates.append(candidate)

        candidates.sort(key=lambda item: item.id)
        selected = self._filter_candidate_ids(
            candidates=candidates,
            candidate_ids=candidate_ids,
        )
        operations = self._build_operations(config=config, candidates=selected)

        return GraphSuggestResult(
            ok=True,
            workspace_name=config.name or "workspace",
            candidates=candidates,
            already_manual=sorted(already_manual),
            skipped_low_confidence=skipped_low_confidence,
            operations=operations,
        )

    def suggest_and_apply(
        self,
        config: MetagitConfig,
        workspace_root: str,
        config_path: str,
        *,
        dependency_types: Optional[list[str]] = None,
        depth: int = 3,
        min_confidence: MinConfidence = "medium",
        include_declared: bool = False,
        candidate_ids: Optional[list[str]] = None,
        dry_run: bool = False,
        save: bool = True,
    ) -> GraphSuggestResult:
        """Suggest candidates and optionally patch graph.relationships on disk."""
        result = self.suggest(
            config=config,
            workspace_root=workspace_root,
            dependency_types=dependency_types,
            depth=depth,
            min_confidence=min_confidence,
            include_declared=include_declared,
            candidate_ids=candidate_ids,
        )
        if not result.ok or dry_run or not result.operations:
            result.apply = GraphSuggestApplyResult(
                ok=result.ok,
                saved=False,
                applied_count=0,
            )
            return result

        operations = [
            ConfigOperation(
                op=ConfigOpKind(item["op"]),
                path=item["path"],
                value=item.get("value"),
            )
            for item in result.operations
        ]
        patch_result = self._patch.patch(
            "metagit",
            config_path,
            operations,
            save=save,
        )
        if isinstance(patch_result, Exception):
            result.apply = GraphSuggestApplyResult(
                ok=False,
                saved=False,
                applied_count=0,
                validation_errors=[{"message": str(patch_result)}],
            )
            return result

        selected_count = len(
            self._filter_candidate_ids(
                candidates=result.candidates,
                candidate_ids=candidate_ids,
            )
        )
        result.apply = GraphSuggestApplyResult(
            ok=patch_result.ok,
            saved=patch_result.saved,
            applied_count=selected_count,
            validation_errors=patch_result.validation_errors,
        )
        return result

    def _resolve_dependency_types(
        self,
        *,
        dependency_types: Optional[list[str]],
        include_declared: bool,
    ) -> set[str]:
        selected = {item.lower() for item in dependency_types} if dependency_types else set(_PROMOTABLE_DEFAULT)
        if include_declared:
            selected.update({"declared", "ref"})
        return selected

    def _manual_signatures(
        self,
        *,
        config: MetagitConfig,
        rows: list[dict[str, Any]],
        project_names: set[str],
    ) -> set[tuple[str, str, str, str, str]]:
        signatures: set[tuple[str, str, str, str, str]] = set()
        if config.graph is None:
            return signatures
        for rel in config.graph.relationships:
            from_id = resolve_graph_endpoint_id(
                rel.from_endpoint,
                rows=rows,
                project_names=project_names,
            )
            to_id = resolve_graph_endpoint_id(
                rel.to,
                rows=rows,
                project_names=project_names,
            )
            if not from_id or not to_id:
                continue
            from_endpoint = node_id_to_endpoint(from_id)
            to_endpoint = node_id_to_endpoint(to_id)
            if from_endpoint is None or to_endpoint is None:
                continue
            signatures.add(_relationship_signature(from_endpoint, to_endpoint, rel.type))
        return signatures

    def _build_relationship_id(
        self,
        *,
        from_endpoint: GraphEndpoint,
        to_endpoint: GraphEndpoint,
        rel_type: str,
    ) -> str:
        from_label = (
            f"{from_endpoint.project}-{from_endpoint.repo}" if from_endpoint.repo else str(from_endpoint.project)
        )
        to_label = f"{to_endpoint.project}-{to_endpoint.repo}" if to_endpoint.repo else str(to_endpoint.project)
        return f"{_slug(from_label)}-to-{_slug(to_label)}-{rel_type}"

    def _filter_candidate_ids(
        self,
        *,
        candidates: list[SuggestedGraphRelationship],
        candidate_ids: Optional[list[str]],
    ) -> list[SuggestedGraphRelationship]:
        if not candidate_ids:
            return candidates
        selected = {item.strip() for item in candidate_ids if item.strip()}
        return [candidate for candidate in candidates if candidate.id in selected]

    def _build_operations(
        self,
        *,
        config: MetagitConfig,
        candidates: list[SuggestedGraphRelationship],
    ) -> list[dict[str, Any]]:
        if not candidates:
            return []

        operations: list[dict[str, Any]] = []
        if config.graph is None:
            operations.append({"op": "enable", "path": "graph"})

        base_index = len(config.graph.relationships) if config.graph else 0
        for offset, candidate in enumerate(candidates):
            operations.append({"op": "append", "path": "graph.relationships"})
            operations.append(
                {
                    "op": "set",
                    "path": f"graph.relationships[{base_index + offset}]",
                    "value": self._candidate_value(candidate),
                }
            )
        return operations

    def _candidate_value(
        self,
        candidate: SuggestedGraphRelationship,
    ) -> dict[str, Any]:
        return GraphRelationship(
            id=candidate.id,
            from_endpoint=candidate.from_endpoint,
            to=candidate.to_endpoint,
            type=candidate.type,
            label=candidate.label,
            description=candidate.description,
            tags=dict(candidate.tags),
            metadata=dict(candidate.metadata),
        ).model_dump(mode="json", by_alias=True)
