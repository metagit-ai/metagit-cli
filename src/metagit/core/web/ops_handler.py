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
from metagit.core.context.approval_service import ApprovalService
from metagit.core.context.models import Objective
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.mcp.services.workspace_health import WorkspaceHealthService
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.mcp.services.workspace_sync import WorkspaceSyncService
from metagit.core.project.manager import project_manager_from_app
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.workspace.context_models import utc_now_iso
from metagit.core.web.graph_service import WorkspaceGraphService
from metagit.core.web.job_store import SyncJobStore
from metagit.core.web.models import (
    ApprovalResolveRequest,
    ObjectiveStatusPatchRequest,
    ObjectiveUpsertRequest,
    SyncJobRequest,
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

        if method == "GET" and parsed_path == "/v3/ops/objectives":
            self._get_objectives(respond)
            return True

        if method == "POST" and parsed_path == "/v3/ops/objectives":
            self._post_objectives(body, respond)
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
        svc = ObjectiveService(workspace_root=self._workspace_root)
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
        now = utc_now_iso()
        objective = Objective(
            id=req.id,
            title=req.title.strip(),
            status=req.status,
            repos=list(req.repos),
            acceptance=req.acceptance,
            human_notes=req.human_notes,
            agent_notes=req.agent_notes,
            created_at=now,
            updated_at=now,
        )
        svc = ObjectiveService(workspace_root=self._workspace_root)
        saved = svc.upsert(objective)
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
            req = ObjectiveStatusPatchRequest.model_validate(payload)
        except ValidationError as exc:
            respond(
                400,
                {"ok": False, "error": {"kind": "invalid_body", "message": str(exc)}},
            )
            return
        svc = ObjectiveService(workspace_root=self._workspace_root)
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

    def _get_approvals(self, query: str, respond: JsonResponder) -> None:
        params = parse_qs(query.lstrip("?"))
        raw_status = (params.get("status") or ["pending"])[0].strip().lower()
        svc = ApprovalService(workspace_root=self._workspace_root)
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
        svc = ApprovalService(workspace_root=self._workspace_root)
        try:
            saved = svc.resolve(
                request_id=approval_id,
                decision=req.decision,
                note=req.note,
            )
        except ValueError as exc:
            respond(
                400,
                {
                    "ok": False,
                    "error": {"kind": "resolve_error", "message": str(exc)},
                },
            )
            return
        respond(200, saved.model_dump(mode="json"))

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
        manager = MetagitConfigManager(self._config_path)
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            respond(
                500,
                {
                    "ok": False,
                    "error": {"kind": "config_error", "message": str(loaded)},
                },
            )
            return None
        return loaded

    def _load_appconfig(self, respond: JsonResponder) -> AppConfig | None:
        loaded = load_appconfig(self._appconfig_path)
        if isinstance(loaded, Exception):
            respond(
                500,
                {
                    "ok": False,
                    "error": {"kind": "config_error", "message": str(loaded)},
                },
            )
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
