#!/usr/bin/env python
"""
Assemble Metagit MCP layered resource payloads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.context.approval_service import ApprovalService
from metagit.core.context.handoff_service import HandoffService
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.context.repo_card_service import RepoCardService
from metagit.core.context.session_digest_service import SessionDigestService
from metagit.core.context.workspace_map_service import WorkspaceMapService
from metagit.core.mcp.models import McpActivationState, WorkspaceStatus
from metagit.core.mcp.resource_catalog import (
    build_catalog_payload,
    parse_project_summary_uri,
    parse_prompt_uri,
    parse_repo_card_uri,
    parse_resource_uri,
    query_bool,
    query_int,
)
from metagit.core.mcp.resource_models import (
    ConfigSummaryResult,
    ProjectSummaryResult,
    ResourceReadResult,
)
from metagit.core.mcp.services.ops_log import OperationsLogService
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.prompt.models import PromptKind, PromptScope
from metagit.core.prompt.service import PromptService, PromptServiceError
from metagit.core.state.resolver import describe_state_backend, resolve_backend


@dataclass(frozen=True)
class ResourceContext:
    """Inputs required to resolve a resource URI."""

    status: WorkspaceStatus
    config: MetagitConfig | None
    config_path: str
    workspace_root: str
    session_root: str
    definition_root: str
    repos_status: list[dict[str, Any]]
    health_payload: dict[str, Any] | None
    workspace_dedupe: WorkspaceDedupeConfig | None


class ResourceService:
    """Resolve metagit:// resource URIs into MCP read payloads."""

    def __init__(
        self,
        ops_log: OperationsLogService,
        *,
        map_service: WorkspaceMapService | None = None,
        card_service: RepoCardService | None = None,
        prompt_service: PromptService | None = None,
    ) -> None:
        self._ops_log = ops_log
        self._map = map_service or WorkspaceMapService()
        self._cards = card_service or RepoCardService()
        self._prompt = prompt_service or PromptService()

    def read(self, uri: str, context: ResourceContext) -> ResourceReadResult:
        """Return a normalized resource read result for ``uri``."""
        parsed = parse_resource_uri(uri)
        active = context.status.state == McpActivationState.ACTIVE

        if parsed.host == "catalog" and not parsed.path.strip("/"):
            payload = build_catalog_payload(gate_state=context.status.state)
            return self._json(uri, payload.model_dump(mode="json"))

        if parsed.host == "gate" and parsed.path.strip("/") == "status":
            session_root = context.session_root or context.status.root_path or ""
            payload: dict[str, Any] = {
                "state": context.status.state.value,
                "root_path": context.status.root_path,
                "reason": context.status.reason,
            }
            if session_root:
                payload["state_backend"] = describe_state_backend(session_root)
            return self._json(uri, payload)

        if parsed.host == "workspace" and parsed.path.strip("/") == "ops-log":
            limit = query_int(parsed.query.get("limit"))
            entries = self._ops_log.list_entries()
            data = entries[-limit:] if limit is not None else entries
            return self._json(uri, data)

        if not active or context.config is None:
            return ResourceReadResult(uri=uri, error="Resource requires an active workspace gate")

        prompt_target = parse_prompt_uri(parsed)
        if prompt_target is not None:
            return self._read_prompt(uri, parsed, context, scope=prompt_target[0], kind=prompt_target[1])

        project_name = parse_project_summary_uri(parsed)
        if project_name is not None:
            return self._read_project_summary(uri, context, project_name=project_name)

        repo_target = parse_repo_card_uri(parsed)
        if repo_target is not None:
            return self._read_repo_card(
                uri,
                context,
                project_name=repo_target[0],
                repo_name=repo_target[1],
            )

        if parsed.host == "workspace":
            segment = parsed.path.strip("/")
            if segment == "map":
                return self._read_map(uri, context)
            if segment == "config":
                return self._read_config(uri, parsed, context)
            if segment == "repos/status":
                return self._read_repos_status(uri, parsed, context)
            if segment == "health":
                return self._json(uri, context.health_payload or {})
            if segment == "context":
                return self._read_session_meta(uri, context, deprecated_alias=True)

        if parsed.host == "session":
            segment = parsed.path.strip("/")
            if segment == "digest/summary":
                return self._read_session_digest(uri, context, summary=True)
            if segment == "digest":
                return self._read_session_digest(uri, context, summary=False)
            if segment == "meta":
                return self._read_session_meta(uri, context)

        if parsed.host == "objectives" and not parsed.path.strip("/"):
            return self._read_objectives(uri, parsed, context)

        if parsed.host == "approvals" and parsed.path.strip("/") == "pending":
            return self._read_approvals_pending(uri, context)

        if parsed.host == "handoffs" and parsed.path.strip("/") == "open":
            return self._read_handoffs_open(uri, context)

        if parsed.host == "events" and parsed.path.strip("/") == "recent":
            return self._read_events_recent(uri, parsed, context)

        if parsed.host == "prompt" and parsed.path.strip("/") == "catalog":
            entries = self._prompt.list_entries()
            return self._json(
                uri,
                {
                    "entries": [item.model_dump(mode="json") for item in entries],
                },
            )

        return ResourceReadResult(uri=uri, error="Unknown resource URI")

    def _read_map(self, uri: str, context: ResourceContext) -> ResourceReadResult:
        store = SessionStore(workspace_root=context.session_root)
        meta = store.get_workspace_meta()
        map_result = self._map.build(
            config=context.config,  # type: ignore[arg-type]
            config_path=context.config_path,
            workspace_root=context.workspace_root,
            active_project=meta.active_project,
        )
        return self._json(uri, map_result.model_dump(mode="json"))

    def _read_session_meta(
        self,
        uri: str,
        context: ResourceContext,
        *,
        deprecated_alias: bool = False,
    ) -> ResourceReadResult:
        store = SessionStore(workspace_root=context.session_root)
        meta = store.get_workspace_meta()
        session = store.get_project_session(project_name=meta.active_project) if meta.active_project else None
        data: dict[str, Any] = {
            "active_project": meta.active_project,
            "last_switch_at": meta.last_switch_at,
            "session": session.model_dump(mode="json") if session else None,
        }
        if deprecated_alias:
            data["deprecated"] = True
            data["prefer_uri"] = "metagit://session/meta"
        return self._json(uri, data)

    def _read_config(
        self,
        uri: str,
        parsed: Any,
        context: ResourceContext,
    ) -> ResourceReadResult:
        view = (parsed.query.get("view") or "summary").strip().lower()
        config = context.config
        if config is None:
            return ResourceReadResult(uri=uri, error="config unavailable")
        if view == "full":
            return self._json(uri, config.model_dump(exclude_none=True))
        projects: list[dict[str, Any]] = []
        repo_count = 0
        if config.workspace:
            for project in config.workspace.projects:
                count = len(project.repos)
                repo_count += count
                projects.append(
                    {
                        "name": project.name,
                        "repo_count": count,
                        "protected": bool(project.protected),
                    }
                )
        summary = ConfigSummaryResult(
            name=config.name,
            kind=str(config.kind),
            project_count=len(projects),
            repo_count=repo_count,
            projects=projects,
        )
        return self._json(uri, summary.model_dump(mode="json"))

    def _read_repos_status(
        self,
        uri: str,
        parsed: Any,
        context: ResourceContext,
    ) -> ResourceReadResult:
        rows = list(context.repos_status)
        project_filter = parsed.query.get("project")
        if project_filter:
            rows = [row for row in rows if row.get("project_name") == project_filter]
        if query_bool(parsed.query.get("summary"), default=False):
            return self._json(uri, self._repos_status_summary(rows))
        return self._json(uri, rows)

    @staticmethod
    def _repos_status_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        by_project: dict[str, dict[str, int]] = {}
        by_status: dict[str, int] = {}
        missing_clone = 0
        for row in rows:
            project_name = str(row.get("project_name") or "unknown")
            bucket = by_project.setdefault(
                project_name,
                {"repo_count": 0, "missing_clone": 0},
            )
            bucket["repo_count"] += 1
            if not row.get("exists"):
                missing_clone += 1
                bucket["missing_clone"] += 1
            status_key = str(row.get("status") or "unknown")
            by_status[status_key] = by_status.get(status_key, 0) + 1
        return {
            "view": "summary",
            "project_count": len(by_project),
            "repo_count": len(rows),
            "missing_clone": missing_clone,
            "by_project": [{"project_name": name, **counts} for name, counts in sorted(by_project.items())],
            "by_status": by_status,
        }

    def _read_session_digest(
        self,
        uri: str,
        context: ResourceContext,
        *,
        summary: bool,
    ) -> ResourceReadResult:
        config = context.config
        if config is None:
            return ResourceReadResult(uri=uri, error="config unavailable")
        store = SessionStore(workspace_root=context.session_root)
        since = store.get_last_session_at()
        objectives_list = ObjectiveService(workspace_root=context.session_root).list().objectives
        active_oid = next(
            (item.id for item in objectives_list if item.status == "in_progress"),
            None,
        )
        digest = SessionDigestService.build(
            config=config,
            config_path=context.config_path,
            workspace_root=context.workspace_root,
            definition_root=context.definition_root,
            since=since,
            active_objective_id=active_oid,
        )
        if summary:
            payload = {
                "view": "summary",
                "since": digest.since,
                "first_session": digest.first_session,
                "manifest_changed": digest.manifest_changed,
                "active_objective_id": digest.active_objective_id,
                "repos_with_changes": sum(1 for row in digest.repo_changes if row.commit_count > 0),
                "total_commits": sum(row.commit_count for row in digest.repo_changes),
            }
            return self._json(uri, payload)
        return self._json(uri, digest.model_dump(mode="json"))

    def _read_objectives(
        self,
        uri: str,
        parsed: Any,
        context: ResourceContext,
    ) -> ResourceReadResult:
        objectives = ObjectiveService(workspace_root=context.session_root).list().objectives
        status_filter = parsed.query.get("status")
        if status_filter:
            objectives = [item for item in objectives if item.status == status_filter]
        include_notes = query_bool(parsed.query.get("full"), default=False)
        rows: list[dict[str, Any]] = []
        for item in objectives:
            row: dict[str, Any] = {
                "id": item.id,
                "status": item.status,
                "title": item.title,
                "repos": list(item.repos),
            }
            if include_notes:
                row.update(
                    {
                        "acceptance": item.acceptance,
                        "human_notes": item.human_notes,
                        "agent_notes": item.agent_notes,
                    }
                )
            rows.append(row)
        return self._json(uri, rows)

    def _read_approvals_pending(self, uri: str, context: ResourceContext) -> ResourceReadResult:
        pending = ApprovalService(workspace_root=context.session_root).list(status="pending").requests
        return self._json(
            uri,
            [item.model_dump(mode="json") for item in pending],
        )

    def _read_handoffs_open(self, uri: str, context: ResourceContext) -> ResourceReadResult:
        service = HandoffService(workspace_root=context.session_root)
        rows = [item for item in service.list().handoffs if item.status in {"open", "claimed"}]
        return self._json(
            uri,
            [item.model_dump(mode="json") for item in rows],
        )

    def _read_events_recent(
        self,
        uri: str,
        parsed: Any,
        context: ResourceContext,
    ) -> ResourceReadResult:
        since = parsed.query.get("since")
        result = resolve_backend(context.session_root).events().list_events(since=since)
        return self._json(uri, result.model_dump(mode="json"))

    def _read_project_summary(
        self,
        uri: str,
        context: ResourceContext,
        *,
        project_name: str,
    ) -> ResourceReadResult:
        config = context.config
        if config is None or not config.workspace:
            return ResourceReadResult(uri=uri, error="no workspace block in manifest")
        project = next(
            (item for item in config.workspace.projects if item.name == project_name),
            None,
        )
        if project is None:
            return ResourceReadResult(uri=uri, error=f"project {project_name!r} not found")

        index_rows = [row for row in context.repos_status if row.get("project_name") == project_name]
        missing_clone = sum(1 for row in index_rows if not row.get("exists"))
        status_counts: dict[str, int] = {}
        repo_rows: list[dict[str, Any]] = []
        for row in index_rows:
            status_key = str(row.get("status") or "unknown")
            status_counts[status_key] = status_counts.get(status_key, 0) + 1
            repo_rows.append(
                {
                    "repo_name": row.get("repo_name"),
                    "status": row.get("status"),
                    "exists": row.get("exists"),
                }
            )

        summary = ProjectSummaryResult(
            project_name=project.name,
            description=project.description,
            tags=[f"{key}={value}" for key, value in sorted((project.tags or {}).items())],
            protected=bool(project.protected),
            repo_count=len(repo_rows),
            repos=repo_rows,
            health_summary={
                "missing_clone": missing_clone,
                **{f"status_{key}": value for key, value in sorted(status_counts.items())},
            },
        )
        return self._json(uri, summary.model_dump(mode="json"))

    def _read_repo_card(
        self,
        uri: str,
        context: ResourceContext,
        *,
        project_name: str,
        repo_name: str,
    ) -> ResourceReadResult:
        config = context.config
        if config is None:
            return ResourceReadResult(uri=uri, error="config unavailable")
        try:
            card = self._cards.build_one(
                config=config,
                workspace_root=context.workspace_root,
                project_name=project_name,
                repo_name=repo_name,
                definition_root=context.definition_root,
            )
        except ValueError as exc:
            return ResourceReadResult(uri=uri, error=str(exc))
        return self._json(uri, card.model_dump(mode="json"))

    def _read_prompt(
        self,
        uri: str,
        parsed: Any,
        context: ResourceContext,
        *,
        scope: PromptScope,
        kind: PromptKind,
    ) -> ResourceReadResult:
        config = context.config
        if config is None:
            return ResourceReadResult(uri=uri, error="config unavailable")
        include_instructions = query_bool(parsed.query.get("instructions"), default=True)
        project_name = parsed.query.get("project")
        repo_name = parsed.query.get("repo")
        try:
            emitted = self._prompt.emit(
                config,
                kind=kind,
                scope=scope,
                definition_path=context.config_path,
                workspace_root=context.workspace_root,
                project_name=project_name,
                repo_name=repo_name,
                include_instructions=include_instructions,
                workspace_dedupe=context.workspace_dedupe,
            )
        except PromptServiceError as exc:
            return ResourceReadResult(uri=uri, error=str(exc))
        return ResourceReadResult(uri=uri, mime_type="text/plain", text=emitted.text)

    def _json(self, uri: str, data: Any) -> ResourceReadResult:
        return ResourceReadResult(
            uri=uri,
            mime_type="application/json",
            data=data,
        )


def resource_json_text(result: ResourceReadResult) -> str:
    """Serialize a resource read result for MCP contents[].text."""
    if result.error:
        return json.dumps({"uri": result.uri, "error": result.error})
    if result.mime_type == "text/plain" and result.text is not None:
        return result.text
    return json.dumps(
        {
            "uri": result.uri,
            "schema_version": "1.0",
            "data": result.data,
        }
    )


__all__ = ["ResourceContext", "ResourceService", "resource_json_text"]
