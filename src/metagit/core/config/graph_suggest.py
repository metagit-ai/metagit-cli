#!/usr/bin/env python
"""Suggest graph.relationships candidates from inferred workspace dependencies."""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.config.graph_models import GraphEndpoint, GraphRelationship
from metagit.core.config.graph_resolver import resolve_graph_endpoint_id
from metagit.core.config.graph_validation import validate_graph_relationships
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.config.patch_service import ConfigPatchService
from metagit.core.mcp.services.cross_project_dependencies import (
    CrossProjectDependencyService,
)
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.utils.repo_walk import sum_scan_stats
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
    workspace_root: str = ""
    candidates: list[SuggestedGraphRelationship] = Field(default_factory=list)
    already_manual: list[str] = Field(default_factory=list)
    stale_manual: list[str] = Field(default_factory=list)
    skipped_low_confidence: int = 0
    operations: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    apply: GraphSuggestApplyResult | None = None
    scan_stats: dict[str, int] | None = None


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
        manual_records = self._manual_relationship_records(
            config=config,
            rows=rows,
            project_names=project_names,
        )
        manual_signatures = {record[1] for record in manual_records}

        allowed_edge_types = {_REQUEST_TO_EDGE_TYPE.get(item, item) for item in selected_types}
        merged_edges: dict[tuple[str, str, str], Any] = {}
        # map_dependencies re-scans every workspace repo on each per-project call, so
        # stats are collected per repo path and summed once instead of accumulated.
        scan_stats_by_repo: dict[str, dict[str, int]] = {}
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
            scan_stats_by_repo.update(result.import_scan_stats_by_repo or {})
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
        inferred_signatures: set[tuple[str, str, str, str, str]] = set()
        skipped_low_confidence = 0
        min_rank = _CONFIDENCE_ORDER[min_confidence]

        for edge in merged_edges.values():
            from_endpoint = node_id_to_endpoint(edge.from_id)
            to_endpoint = node_id_to_endpoint(edge.to_id)
            if from_endpoint is None or to_endpoint is None:
                continue

            rel_type = _EDGE_TO_REL_TYPE.get(edge.type, "related")
            signature = _relationship_signature(from_endpoint, to_endpoint, rel_type)
            inferred_signatures.add(signature)
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
        stale_manual = self._stale_manual_relationships(
            manual_records=manual_records,
            inferred_endpoints={signature[:4] for signature in inferred_signatures},
        )

        return GraphSuggestResult(
            ok=True,
            workspace_name=config.name or "workspace",
            workspace_root=workspace_root,
            candidates=candidates,
            already_manual=sorted(already_manual),
            stale_manual=stale_manual,
            skipped_low_confidence=skipped_low_confidence,
            operations=operations,
            scan_stats=sum_scan_stats(scan_stats_by_repo) or None,
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

        selected = self._filter_candidate_ids(
            candidates=result.candidates,
            candidate_ids=candidate_ids,
        )
        # Rebuild against the document on disk: the caller's in-memory config may
        # carry edges the manifest does not, and a `set` of the whole list must not
        # drop relationships that are only present on disk.
        on_disk = MetagitConfigManager(config_path=config_path).load_config()
        if isinstance(on_disk, Exception):
            result.apply = GraphSuggestApplyResult(
                ok=False,
                saved=False,
                applied_count=0,
                validation_errors=[{"message": str(on_disk)}],
            )
            return result
        result.operations = self._build_operations(config=on_disk, candidates=selected)
        operations = [
            ConfigOperation(
                op=ConfigOpKind(item["op"]),
                path=item["path"],
                value=item.get("value"),
            )
            for item in result.operations
        ]
        validation_errors = self._validate_draft(
            config_path=config_path,
            operations=operations,
        )
        if isinstance(validation_errors, Exception):
            result.apply = GraphSuggestApplyResult(
                ok=False,
                saved=False,
                applied_count=0,
                validation_errors=[{"message": str(validation_errors)}],
            )
            return result
        if validation_errors:
            result.apply = GraphSuggestApplyResult(
                ok=False,
                saved=False,
                applied_count=0,
                validation_errors=validation_errors,
            )
            return result

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

        result.apply = GraphSuggestApplyResult(
            ok=patch_result.ok,
            saved=patch_result.saved,
            applied_count=len(selected),
            validation_errors=patch_result.validation_errors,
        )
        return result

    def _validate_draft(
        self,
        *,
        config_path: str,
        operations: list[ConfigOperation],
    ) -> list[dict[str, str]] | Exception:
        """Validate the document these operations actually produce on disk."""
        draft = self._patch.draft("metagit", config_path, operations)
        if isinstance(draft, Exception):
            return draft
        patched, schema_errors = draft
        if schema_errors:
            return schema_errors
        if not isinstance(patched, MetagitConfig):
            return TypeError("patched config is not a metagit manifest")
        return [{"message": issue} for issue in validate_graph_relationships(patched)]

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

    def _manual_relationship_records(
        self,
        *,
        config: MetagitConfig,
        rows: list[dict[str, Any]],
        project_names: set[str],
    ) -> list[tuple[GraphRelationship, tuple[str, str, str, str, str], str, str]]:
        """Resolve manual graph.relationships entries to signatures and node ids."""
        records: list[tuple[GraphRelationship, tuple[str, str, str, str, str], str, str]] = []
        if config.graph is None:
            return records
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
            signature = _relationship_signature(from_endpoint, to_endpoint, rel.type)
            records.append((rel, signature, from_id, to_id))
        return records

    def _stale_manual_relationships(
        self,
        *,
        manual_records: list[tuple[GraphRelationship, tuple[str, str, str, str, str], str, str]],
        inferred_endpoints: set[tuple[str, str, str, str]],
    ) -> list[str]:
        """Report active manual relationships with no supporting inferred edge in this scan.

        Support is matched on endpoints alone: an inferred edge between the same two
        endpoints backs a manual edge even when the inferred relationship type differs.
        """
        stale: list[str] = []
        for rel, signature, from_id, to_id in manual_records:
            if rel.status != "active" or rel.provenance != "manual":
                continue
            if signature[:4] in inferred_endpoints:
                continue
            stale.append(rel.id or f"{from_id}->{to_id}:{rel.type}")
        return sorted(stale)

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

        # A single `set` of the complete list keeps the written document free of the
        # placeholder slots that `enable` / `append` seed from schema defaults, and
        # removes any index arithmetic coupling to SchemaTreeService.
        existing = (
            [rel.model_dump(mode="json", by_alias=True) for rel in config.graph.relationships] if config.graph else []
        )
        relationships = existing + [self._candidate_value(candidate) for candidate in candidates]
        return [
            {
                "op": "set",
                "path": "graph.relationships",
                "value": relationships,
            }
        ]

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
            status="active",
            provenance="promoted",
        ).model_dump(mode="json", by_alias=True)
