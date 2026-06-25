#!/usr/bin/env python
"""HTTP handlers for workspace ops routes (health, prune, sync)."""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any, BinaryIO, Callable
from urllib.parse import parse_qs

from pydantic import ValidationError

from metagit.core.appconfig import load_config as load_appconfig
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.context.approval_resolve import ApprovalResolveOrchestrator
from metagit.core.context.approval_service import ApprovalService
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.context.session_begin_service import SessionBeginService
from metagit.core.context.session_digest_service import SessionDigestService
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.mcp.services.source_sync import run_mcp_source_sync
from metagit.core.mcp.services.workspace_health import WorkspaceHealthService
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.mcp.services.workspace_sync import WorkspaceSyncService
from metagit.core.project.source_manifest_sync import SourceManifestSyncService
from metagit.core.project.manager import project_manager_from_app
from metagit.core.utils.common import open_editor
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.web.graph_service import WorkspaceGraphService
from metagit.core.web.job_store import SyncJobStore
from metagit.core.web.pipeline_status_service import (
    PipelineQueryOptions,
    PipelineStatusService,
)
from metagit.core.web.models import (
    ApprovalResolveRequest,
    ObjectiveEditRequest,
    ObjectiveStatusPatchRequest,
    ObjectiveUpsertRequest,
    OpenPathRequest,
    SessionBeginRequest,
    SourceSyncRequest,
    SyncJobRequest,
)
from metagit.core.workspace.root_resolver import (
    resolve_definition_root,
    resolve_session_root,
)

JsonResponder = Callable[[int, dict[str, Any]], None]

_SYNC_JOB_PATH = re.compile(
    r"^/v3/ops/sync/(?P<job_id>[0-9a-f]{32})$",
)
_SYNC_EVENTS_PATH = re.compile(
    r"^/v3/ops/sync/(?P<job_id>[0-9a-f]{32})/events$",
)
_OBJECTIVE_ITEM_PATH = re.compile(r"^/v3/ops/objectives/(?P<id>[\w.-]+)$")
_APPROVAL_RESOLVE_PATH = re.compile(
    r"^/v3/ops/approvals/(?P<id>[0-9a-f]{32})/resolve$",
)

_JOB_STORE = SyncJobStore()


class OpsWebHandler:
    """Route workspace health, prune, and sync operations for the web HTTP API."""

    def __init__(
        self,
        *,
        root: str,
        config_path: str,
        appconfig_path: str,
        workspace_root: str,
        job_store: SyncJobStore | None = None,
    ) -> None:
        self._root = str(Path(root).resolve())
        self._config_path = str(Path(config_path).resolve())
        self._appconfig_path = str(Path(appconfig_path).resolve())
        self._workspace_root = str(Path(workspace_root).resolve())
        self._job_store = job_store or _JOB_STORE
        self._health = WorkspaceHealthService()
        self._index = WorkspaceIndexService()
        self._sync = WorkspaceSyncService()
        self._graph = WorkspaceGraphService()
        self._pipelines = PipelineStatusService()
        self._logger = UnifiedLogger(
            LoggerConfig(log_level="ERROR", minimal_console=True)
        )

    def handle(
        self,
        method: str,
        path: str,
        query: str,
        body: bytes,
        respond: JsonResponder,
    ) -> bool:
        """Dispatch JSON ops routes; return True when handled."""
        parsed_path = path if path.startswith("/") else f"/{path}"

        if method == "GET" and parsed_path == "/v3/ops/graph":
            self._get_graph(query, respond)
            return True

        if method == "GET" and parsed_path == "/v3/ops/pipelines/providers":
            self._get_pipeline_providers(respond)
            return True

        if method == "GET" and parsed_path == "/v3/ops/pipelines/status":
            self._get_pipeline_status(query, respond)
            return True

        if method == "GET" and parsed_path == "/v3/ops/objectives":
            self._get_objectives(respond)
            return True

        if method == "POST" and parsed_path == "/v3/ops/objectives":
            self._post_objectives(body, respond)
            return True

        if method == "GET" and parsed_path == "/v3/ops/session":
            self._get_session(respond)
            return True

        if method == "POST" and parsed_path == "/v3/ops/session/begin":
            self._post_session_begin(body, respond)
            return True

        if method == "GET" and parsed_path == "/v3/ops/approvals":
            self._get_approvals(query, respond)
            return True

        approve_match = _APPROVAL_RESOLVE_PATH.match(parsed_path)
        if method == "POST" and approve_match is not None:
            self._post_approval_resolve(
                approve_match.group("id"),
                body,
                respond,
            )
            return True

        obj_match = _OBJECTIVE_ITEM_PATH.match(parsed_path)
        if method == "PATCH" and obj_match is not None:
            self._patch_objective(obj_match.group("id"), body, respond)
            return True

        if method == "POST" and parsed_path == "/v3/ops/health":
            self._post_health(body, respond)
            return True

        if method == "POST" and parsed_path == "/v3/ops/prune/preview":
            self._post_prune_preview(body, respond)
            return True

        if method == "POST" and parsed_path == "/v3/ops/prune":
            self._post_prune(body, respond)
            return True

        if method == "POST" and parsed_path == "/v3/ops/sync":
            self._post_sync(body, respond)
            return True

        if method == "POST" and parsed_path == "/v3/ops/source-sync":
            self._post_source_sync(body, respond)
            return True

        if method == "POST" and parsed_path == "/v3/ops/open":
            self._post_open(body, respond)
            return True

        status_match = _SYNC_JOB_PATH.match(parsed_path)
        if method == "GET" and status_match is not None:
            self._get_sync_status(status_match.group("job_id"), respond)
            return True

        return False

    def sync_events_job_id(self, method: str, path: str) -> str | None:
        """Return job id when path is a sync SSE events route."""
        if method != "GET":
            return None
        parsed_path = path if path.startswith("/") else f"/{path}"
        events_match = _SYNC_EVENTS_PATH.match(parsed_path)
        return None if events_match is None else events_match.group("job_id")

    def stream_sync_events(self, job_id: str, stream: BinaryIO) -> None:
        """Write server-sent events for a sync job until it finishes."""
        self._stream_sync_events(job_id, stream)

    def _get_objectives(self, respond: JsonResponder) -> None:
        svc = ObjectiveService(workspace_root=self._root)
        result = svc.list()
        respond(200, result.model_dump(mode="json"))

    def _post_objectives(self, body: bytes, respond: JsonResponder) -> None:
        payload = self._parse_body(body, respond, required=True)
        if payload is None:
            return
        try:
            req = ObjectiveUpsertRequest.model_validate(payload)
        except ValidationError as exc:
            respond(
                400,
                {"ok": False, "error": {"kind": "invalid_body", "message": str(exc)}},
            )
            return
        svc = ObjectiveService(workspace_root=self._root)
        saved = svc.upsert_partial(
            {
                "id": req.id,
                "title": req.title.strip(),
                "status": req.status,
                "repos": list(req.repos),
                "acceptance": req.acceptance,
                "human_notes": req.human_notes,
                "agent_notes": req.agent_notes,
            }
        )
        respond(200, saved.model_dump(mode="json"))

    def _patch_objective(
        self,
        objective_id: str,
        body: bytes,
        respond: JsonResponder,
    ) -> None:
        payload = self._parse_body(body, respond, required=True)
        if payload is None:
            return
        try:
            if set(payload.keys()) == {"status"}:
                req = ObjectiveStatusPatchRequest.model_validate(payload)
                svc = ObjectiveService(workspace_root=self._root)
                try:
                    if req.status == "done":
                        saved = svc.complete(objective_id=objective_id)
                    else:
                        saved = svc.cancel(objective_id=objective_id)
                except ValueError as exc:
                    respond(
                        404,
                        {
                            "ok": False,
                            "error": {"kind": "not_found", "message": str(exc)},
                        },
                    )
                    return
                respond(200, saved.model_dump(mode="json"))
                return

            req = ObjectiveEditRequest.model_validate(payload)
        except ValidationError as exc:
            respond(
                400,
                {"ok": False, "error": {"kind": "invalid_body", "message": str(exc)}},
            )
            return
        svc = ObjectiveService(workspace_root=self._root)
        try:
            updates: dict[str, Any] = {}
            if req.status is not None:
                updates["status"] = req.status
            if req.title is not None:
                updates["title"] = req.title
            if req.repos is not None:
                updates["repos"] = list(req.repos)
            if req.acceptance is not None:
                updates["acceptance"] = req.acceptance
            if req.human_notes is not None:
                updates["human_notes"] = req.human_notes
            if req.agent_notes is not None:
                updates["agent_notes"] = req.agent_notes
            if not updates:
                respond(
                    400,
                    {
                        "ok": False,
                        "error": {
                            "kind": "invalid_body",
                            "message": "at least one editable field is required",
                        },
                    },
                )
                return
            saved = svc.edit(objective_id=objective_id, updates=updates)
        except ValueError as exc:
            respond(
                404,
                {
                    "ok": False,
                    "error": {"kind": "not_found", "message": str(exc)},
                },
            )
            return
        respond(200, saved.model_dump(mode="json"))

    def _get_session(self, respond: JsonResponder) -> None:
        config = self._load_metagit(respond)
        if config is None:
            return
        definition_root = resolve_definition_root(self._config_path)
        session_root = resolve_session_root(self._root)
        session_store = SessionStore(workspace_root=session_root)
        since = session_store.get_last_session_at()
        objectives = ObjectiveService(workspace_root=session_root).list().objectives
        active_objective_id = next(
            (
                objective.id
                for objective in objectives
                if objective.status == "in_progress"
            ),
            None,
        )
        digest = SessionDigestService.build(
            config=config,
            config_path=self._config_path,
            workspace_root=self._workspace_root,
            since=since,
            active_objective_id=active_objective_id,
            definition_root=definition_root,
        )
        respond(200, digest.model_dump(mode="json"))

    def _post_session_begin(self, body: bytes, respond: JsonResponder) -> None:
        config = self._load_metagit(respond)
        if config is None:
            return
        payload = self._parse_body(body, respond, required=False)
        if payload is None:
            return
        try:
            req = SessionBeginRequest.model_validate(payload)
        except ValidationError as exc:
            respond(
                400,
                {"ok": False, "error": {"kind": "invalid_body", "message": str(exc)}},
            )
            return
        definition_root = resolve_definition_root(self._config_path)
        session_root = resolve_session_root(self._root)
        result = SessionBeginService().begin(
            config=config,
            config_path=self._config_path,
            workspace_root=self._workspace_root,
            session_root=session_root,
            definition_root=definition_root,
            project_name=req.project_name,
            repo_name=req.repo_name,
            max_tokens=req.max_tokens,
        )
        respond(200, result.model_dump(mode="json"))

    def _get_approvals(self, query: str, respond: JsonResponder) -> None:
        params = parse_qs(query.lstrip("?"))
        raw_status = (params.get("status") or ["pending"])[0].strip().lower()
        svc = ApprovalService(workspace_root=self._root)
        if raw_status in ("", "pending"):
            result = svc.list(status="pending")
        elif raw_status == "all":
            result = svc.list(status=None)
        elif raw_status in ("approved", "denied"):
            result = svc.list(status=raw_status)
        else:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_query",
                        "message": "status must be pending, approved, denied, or all",
                    },
                },
            )
            return
        respond(200, result.model_dump(mode="json"))

    def _post_approval_resolve(
        self,
        approval_id: str,
        body: bytes,
        respond: JsonResponder,
    ) -> None:
        payload = self._parse_body(body, respond, required=True)
        if payload is None:
            return
        try:
            req = ApprovalResolveRequest.model_validate(payload)
        except ValidationError as exc:
            respond(
                400,
                {"ok": False, "error": {"kind": "invalid_body", "message": str(exc)}},
            )
            return
        config = self._load_metagit(respond)
        if config is None:
            return
        saved = ApprovalResolveOrchestrator().resolve(
            workspace_root=self._root,
            config=config,
            config_path=self._config_path,
            request_id=approval_id,
            decision=req.decision,
            note=req.note,
        )
        if isinstance(saved, Exception):
            respond(
                400,
                {
                    "ok": False,
                    "error": {"kind": "resolve_error", "message": str(saved)},
                },
            )
            return
        respond(200, saved.model_dump(mode="json"))

    def _post_open(self, body: bytes, respond: JsonResponder) -> None:
        payload = self._parse_body(body, respond, required=True)
        if payload is None:
            return
        try:
            req = OpenPathRequest.model_validate(payload)
        except ValidationError as exc:
            respond(
                400,
                {"ok": False, "error": {"kind": "invalid_body", "message": str(exc)}},
            )
            return
        config = self._load_metagit(respond)
        if config is None:
            return
        app_config = self._load_appconfig(respond)
        if app_config is None:
            return
        resolved = str(Path(req.path.strip()).resolve())
        definition_root = resolve_definition_root(self._config_path)
        rows = self._index.build_index(
            config=config,
            workspace_root=self._workspace_root,
            definition_root=definition_root,
        )
        allowed_paths = {
            str(Path(str(row.get("repo_path", ""))).resolve())
            for row in rows
            if row.get("repo_path")
        }
        if resolved not in allowed_paths:
            respond(
                403,
                {
                    "ok": False,
                    "error": {
                        "kind": "forbidden_path",
                        "message": "path is not a managed workspace repository",
                    },
                },
            )
            return
        if not Path(resolved).exists():
            respond(
                404,
                {
                    "ok": False,
                    "error": {
                        "kind": "missing_path",
                        "message": f"path does not exist: {resolved}",
                    },
                },
            )
            return
        editor = (req.editor or app_config.editor or "code").strip() or "code"
        opened = open_editor(editor, resolved)
        if isinstance(opened, Exception):
            respond(
                500,
                {
                    "ok": False,
                    "error": {"kind": "open_failed", "message": str(opened)},
                },
            )
            return
        respond(
            200,
            {
                "ok": True,
                "path": resolved,
                "editor": editor,
            },
        )

    def _post_health(self, body: bytes, respond: JsonResponder) -> None:
        config = self._load_metagit(respond)
        if config is None:
            return
        app_config = self._load_appconfig(respond)
        if app_config is None:
            return
        payload = self._parse_body(body, respond, required=False) or {}
        project_raw = payload.get("project")
        project_name = str(project_raw).strip() if project_raw else None
        if project_name == "":
            project_name = None
        dedupe = (
            app_config.workspace.dedupe if app_config.workspace is not None else None
        )
        result = self._health.check(
            config=config,
            workspace_root=self._workspace_root,
            check_git_status=bool(payload.get("check_git_status", True)),
            check_dependencies=bool(payload.get("check_dependencies", True)),
            check_stale_branches=bool(payload.get("check_stale_branches", True)),
            check_gitnexus=bool(payload.get("check_gitnexus", True)),
            project_name=project_name,
            dedupe=dedupe,
        )
        respond(200, result.model_dump(mode="json"))

    def _get_pipeline_providers(self, respond: JsonResponder) -> None:
        app_config = self._load_appconfig(respond)
        if app_config is None:
            return
        payload = self._pipelines.provider_diagnostics(app_config)
        respond(200, payload)

    def _get_pipeline_status(self, query: str, respond: JsonResponder) -> None:
        config = self._load_metagit(respond)
        if config is None:
            return
        app_config = self._load_appconfig(respond)
        if app_config is None:
            return
        params = parse_qs(query.lstrip("?"))

        raw_project = (params.get("project") or [""])[0].strip() or None
        raw_provider = (params.get("provider") or [""])[0].strip().lower() or None
        raw_status = (params.get("status") or [""])[0].strip().lower() or None
        raw_limit = (params.get("limit") or ["200"])[0].strip() or "200"
        try:
            limit = max(1, min(int(raw_limit), 1000))
        except ValueError:
            limit = 200
        include_unsynced = (params.get("include_unsynced") or ["true"])[
            0
        ].strip().lower() != "false"
        repo_filters = tuple(
            value.strip() for value in params.get("repo", []) if value.strip()
        )

        result = self._pipelines.pipeline_status(
            config=config,
            app_config=app_config,
            workspace_root=self._workspace_root,
            definition_root=resolve_definition_root(self._config_path),
            options=PipelineQueryOptions(
                project=raw_project,
                provider=raw_provider,
                status=raw_status,
                repos=repo_filters,
                include_unsynced=include_unsynced,
                limit=limit,
            ),
        )
        respond(200, result)

    def _get_graph(self, query: str, respond: JsonResponder) -> None:
        config = self._load_metagit(respond)
        if config is None:
            return
        params = parse_qs(query.lstrip("?"))
        include_inferred = (
            params.get("include_inferred", ["true"])[0].lower() != "false"
        )
        include_structure = (
            params.get("include_structure", ["true"])[0].lower() != "false"
        )
        view = self._graph.build_view(
            config,
            self._workspace_root,
            include_inferred=include_inferred,
            include_structure=include_structure,
        )
        respond(200, view.model_dump(mode="json"))

    def _post_prune_preview(self, body: bytes, respond: JsonResponder) -> None:
        payload = self._parse_body(body, respond, required=True)
        if payload is None:
            return
        project = str(payload.get("project", "")).strip()
        if not project:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_body",
                        "message": "project is required",
                    },
                },
            )
            return
        if project == "local":
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_project",
                        "message": "local project is not supported for prune",
                    },
                },
            )
            return
        config = self._load_metagit(respond)
        if config is None:
            return
        app_config = self._load_appconfig(respond)
        if app_config is None:
            return
        include_hidden = bool(payload.get("include_hidden", False))
        ignore_hidden = (
            False if include_hidden else bool(app_config.workspace.ui_ignore_hidden)
        )
        try:
            project_manager = project_manager_from_app(
                app_config,
                self._logger,
                metagit_config=config,
                project_name=project,
            )
        except Exception as exc:
            respond(
                500,
                {
                    "ok": False,
                    "error": {"kind": "project_error", "message": str(exc)},
                },
            )
            return
        candidates = project_manager.list_unmanaged_sync_directories(
            config,
            project,
            ignore_hidden=ignore_hidden,
        )
        respond(
            200,
            {
                "ok": True,
                "candidates": [
                    {"path": str(path.resolve()), "name": path.name}
                    for path in candidates
                ],
            },
        )

    def _post_prune(self, body: bytes, respond: JsonResponder) -> None:
        payload = self._parse_body(body, respond, required=True)
        if payload is None:
            return
        project = str(payload.get("project", "")).strip()
        if not project:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_body",
                        "message": "project is required",
                    },
                },
            )
            return
        raw_paths = payload.get("paths")
        if not isinstance(raw_paths, list) or not raw_paths:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_body",
                        "message": "paths must be a non-empty list",
                    },
                },
            )
            return
        dry_run = bool(payload.get("dry_run", False))
        force = bool(payload.get("force", False))
        config = self._load_metagit(respond)
        if config is None:
            return
        app_config = self._load_appconfig(respond)
        if app_config is None:
            return
        try:
            project_manager = project_manager_from_app(
                app_config,
                self._logger,
                metagit_config=config,
                project_name=project,
            )
        except Exception as exc:
            respond(
                500,
                {
                    "ok": False,
                    "error": {"kind": "project_error", "message": str(exc)},
                },
            )
            return
        project_sync = (Path(self._workspace_root) / project).resolve()
        resolved_paths: list[Path] = []
        for item in raw_paths:
            candidate = Path(str(item)).expanduser()
            resolved = (
                candidate.resolve()
                if candidate.is_absolute()
                else (project_sync / candidate).resolve()
            )
            if project_sync != resolved and project_sync not in resolved.parents:
                respond(
                    400,
                    {
                        "ok": False,
                        "error": {
                            "kind": "invalid_path",
                            "message": f"path must be under project sync folder: {item}",
                        },
                    },
                )
                return
            if not resolved.exists():
                respond(
                    400,
                    {
                        "ok": False,
                        "error": {
                            "kind": "missing_path",
                            "message": f"path does not exist: {resolved}",
                        },
                    },
                )
                return
            resolved_paths.append(resolved)

        if dry_run or not force:
            respond(
                200,
                {
                    "ok": True,
                    "dry_run": dry_run,
                    "force": force,
                    "removed": [],
                    "paths": [str(path) for path in resolved_paths],
                },
            )
            return

        removed: list[str] = []
        errors: list[dict[str, str]] = []
        for path in resolved_paths:
            try:
                project_manager.remove_sync_directory(path)
                removed.append(str(path))
            except OSError as exc:
                errors.append({"path": str(path), "message": str(exc)})
        respond(
            200 if not errors else 500,
            {
                "ok": len(errors) == 0,
                "dry_run": False,
                "force": True,
                "removed": removed,
                "errors": errors,
            },
        )

    def _post_source_sync(self, body: bytes, respond: JsonResponder) -> None:
        payload = self._parse_body(body, respond, required=True)
        if payload is None:
            return
        try:
            request = SourceSyncRequest.model_validate(payload)
        except ValidationError as exc:
            respond(
                400,
                {"ok": False, "error": {"kind": "invalid_body", "message": str(exc)}},
            )
            return
        config = self._load_metagit(respond)
        if config is None:
            return
        app_config = self._load_appconfig(respond)
        if app_config is None:
            return
        arguments = {
            "project_name": request.project_name,
            "from_manifest": request.from_manifest,
            "source_id": request.source_id,
            "apply": request.apply,
            "force": request.force,
            "sync": request.sync,
            "requested_by": request.requested_by,
        }
        result = run_mcp_source_sync(
            app_config=app_config,
            logger=self._logger,
            config=config,
            config_path=self._config_path,
            arguments=arguments,
        )
        status = 200 if result.get("ok", False) else 422
        respond(status, {"ok": result.get("ok", False), **result})

    def _post_sync(self, body: bytes, respond: JsonResponder) -> None:
        config = self._load_metagit(respond)
        if config is None:
            return
        payload = self._parse_body(body, respond, required=True)
        if payload is None:
            return
        try:
            request = SyncJobRequest.model_validate(payload)
        except ValidationError as exc:
            respond(
                400,
                {
                    "ok": False,
                    "error": {"kind": "invalid_body", "message": str(exc)},
                },
            )
            return
        job_id = self._job_store.create_job()
        thread = threading.Thread(
            target=self._run_sync_job,
            args=(job_id, config, request),
            daemon=True,
        )
        thread.start()
        status = self._job_store.get(job_id)
        respond(
            202,
            {
                "ok": True,
                "job_id": job_id,
                "status": status.model_dump(mode="json") if status else None,
            },
        )

    def _get_sync_status(self, job_id: str, respond: JsonResponder) -> None:
        status = self._job_store.get(job_id)
        if status is None:
            respond(
                404,
                {
                    "ok": False,
                    "error": {"kind": "not_found", "message": "Unknown sync job"},
                },
            )
            return
        respond(200, status.model_dump(mode="json"))

    def _stream_sync_events(self, job_id: str, stream: BinaryIO) -> None:
        while True:
            events = self._job_store.drain_events(job_id)
            for event in events:
                payload = json.dumps(event, separators=(",", ":"))
                stream.write(f"data: {payload}\n\n".encode("utf-8"))
                stream.flush()
            status = self._job_store.get(job_id)
            if status is None:
                payload = json.dumps(
                    {"type": "error", "message": "Unknown sync job"},
                    separators=(",", ":"),
                )
                stream.write(f"data: {payload}\n\n".encode("utf-8"))
                stream.flush()
                return
            if status.state in ("completed", "failed"):
                return
            time.sleep(0.05)

    def _run_sync_job(
        self,
        job_id: str,
        config: MetagitConfig,
        request: SyncJobRequest,
    ) -> None:
        self._job_store.mark_running(job_id)
        self._job_store.append_event(job_id, {"type": "started", "job_id": job_id})
        if request.refresh_sources:
            project_name = (request.project_name or "").strip()
            if not project_name:
                self._job_store.fail(
                    job_id,
                    "project_name is required when refresh_sources is true",
                )
                self._job_store.append_event(
                    job_id,
                    {
                        "type": "failed",
                        "job_id": job_id,
                        "error": "project_name is required when refresh_sources is true",
                    },
                )
                return
            app_config = self._load_appconfig_silent()
            if app_config is None:
                self._job_store.fail(job_id, "failed to load app config")
                return
            manifest_result = SourceManifestSyncService().sync_project(
                app_config=app_config,
                logger=self._logger,
                config=config,
                config_path=self._config_path,
                project_name=project_name,
                apply=True,
                sync_clones=False,
                session_root=resolve_session_root(self._root),
                requested_by="web",
            )
            if not manifest_result.ok:
                message = (
                    manifest_result.errors[0].message
                    if manifest_result.errors
                    else "manifest source sync failed"
                )
                self._job_store.fail(job_id, message)
                self._job_store.append_event(
                    job_id,
                    {"type": "failed", "job_id": job_id, "error": message},
                )
                return
            reloaded = self._load_metagit_silent()
            if reloaded is None:
                self._job_store.fail(job_id, "failed to reload manifest after refresh")
                return
            config = reloaded
            self._job_store.append_event(
                job_id,
                {
                    "type": "refresh_sources",
                    "job_id": job_id,
                    "project_name": project_name,
                },
            )
        rows = self._index.build_index(
            config=config,
            workspace_root=self._workspace_root,
        )
        try:
            payload = self._sync.sync_many(
                rows,
                repos=request.repos,
                mode=request.mode,
                allow_mutation=request.allow_mutation,
                max_parallel=request.max_parallel,
                dry_run=request.dry_run,
            )
        except Exception as exc:
            self._job_store.fail(job_id, str(exc))
            self._job_store.append_event(
                job_id,
                {"type": "failed", "job_id": job_id, "error": str(exc)},
            )
            return
        if not payload.get("ok", False):
            error = str(payload.get("error", "sync failed"))
            self._job_store.fail(job_id, error)
            self._job_store.append_event(
                job_id,
                {"type": "failed", "job_id": job_id, "error": error},
            )
            return
        summary = payload.get("summary")
        results = payload.get("results")
        self._job_store.complete(
            job_id,
            summary=dict(summary) if isinstance(summary, dict) else {},
            results=list(results) if isinstance(results, list) else [],
        )
        self._job_store.append_event(
            job_id,
            {
                "type": "completed",
                "job_id": job_id,
                "summary": summary if isinstance(summary, dict) else {},
            },
        )

    def _load_metagit(self, respond: JsonResponder) -> MetagitConfig | None:
        loaded = self._load_metagit_silent()
        if loaded is None:
            respond(
                500,
                {
                    "ok": False,
                    "error": {
                        "kind": "config_error",
                        "message": "failed to load .metagit.yml",
                    },
                },
            )
            return None
        return loaded

    def _load_metagit_silent(self) -> MetagitConfig | None:
        manager = MetagitConfigManager(self._config_path)
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            return None
        return loaded

    def _load_appconfig(self, respond: JsonResponder) -> AppConfig | None:
        loaded = self._load_appconfig_silent()
        if loaded is None:
            respond(
                500,
                {
                    "ok": False,
                    "error": {
                        "kind": "config_error",
                        "message": "failed to load app config",
                    },
                },
            )
            return None
        return loaded

    def _load_appconfig_silent(self) -> AppConfig | None:
        loaded = load_appconfig(self._appconfig_path)
        if isinstance(loaded, Exception):
            return None
        return loaded

    def _parse_body(
        self,
        body: bytes,
        respond: JsonResponder,
        *,
        required: bool,
    ) -> dict[str, Any] | None:
        if not body:
            if required:
                respond(
                    400,
                    {
                        "ok": False,
                        "error": {
                            "kind": "invalid_body",
                            "message": "JSON body required",
                        },
                    },
                )
                return None
            return {}
        try:
            parsed = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            respond(
                400,
                {"ok": False, "error": {"kind": "invalid_json", "message": str(exc)}},
            )
            return None
        if not isinstance(parsed, dict):
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_body",
                        "message": "expected JSON object",
                    },
                },
            )
            return None
        return parsed
