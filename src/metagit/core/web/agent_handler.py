#!/usr/bin/env python
"""HTTP handlers for agent template catalog routes (v3 API)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from metagit.core.agent.models import AgentOverlayInitMode, AgentOverlayScope
from metagit.core.agent.service import AgentService
from metagit.core.web.models import (
    AgentDispatchQuery,
    AgentOverlayInitRequest,
    AgentPreviewQuery,
    AgentTemplatePathParams,
)

JsonResponder = Callable[[int, dict[str, Any]], None]

_TEMPLATE_PATH = re.compile(
    r"^/v3/agents/templates/(?P<template_id>[\w.-]+)$",
)
_PREVIEW_PATH = re.compile(
    r"^/v3/agents/templates/(?P<template_id>[\w.-]+)/preview$",
)
_OVERLAY_INIT_PATH = re.compile(
    r"^/v3/agents/templates/(?P<template_id>[\w.-]+)/overlay/init$",
)
_DISPATCH_PATH = re.compile(
    r"^/v3/agents/templates/(?P<template_id>[\w.-]+)/dispatch-plan$",
)


class AgentWebHandler:
    """Route agent catalog, detail, preview, and overlay operations."""

    def __init__(self, *, manifest_root: str) -> None:
        self._manifest_root = Path(resolve_manifest_root(manifest_root))

    def handle(
        self,
        method: str,
        path: str,
        query: str,
        body: bytes,
        respond: JsonResponder,
    ) -> bool:
        """Dispatch agent routes; return True when handled."""
        parsed_path = urlparse(path).path

        overlay_init_match = _OVERLAY_INIT_PATH.match(parsed_path)
        if method == "POST" and overlay_init_match is not None:
            self._respond_overlay_init(
                overlay_init_match.group("template_id"),
                body,
                respond,
            )
            return True

        if method != "GET":
            return False

        if parsed_path in {"/v3/agents/catalog", "/v3/agents/templates"}:
            self._respond_catalog(respond)
            return True

        preview_match = _PREVIEW_PATH.match(parsed_path)
        if preview_match is not None:
            self._respond_preview(
                preview_match.group("template_id"),
                query,
                respond,
            )
            return True

        dispatch_match = _DISPATCH_PATH.match(parsed_path)
        if dispatch_match is not None:
            self._respond_dispatch_plan(
                dispatch_match.group("template_id"),
                query,
                respond,
            )
            return True

        detail_match = _TEMPLATE_PATH.match(parsed_path)
        if detail_match is not None:
            self._respond_detail(detail_match.group("template_id"), respond)
            return True

        return False

    def _service(self) -> AgentService:
        return AgentService(manifest_root=self._manifest_root)

    def _respond_catalog(self, respond: JsonResponder) -> None:
        envelope = self._service().catalog.list_catalog(
            manifest_root=self._manifest_root,
        )
        respond(200, {"ok": True, "catalog": envelope.model_dump(mode="json")})

    def _respond_detail(self, template_id: str, respond: JsonResponder) -> None:
        detail = self._service().template_detail(template_id)
        if detail is None:
            respond(
                404,
                {
                    "ok": False,
                    "error": {
                        "kind": "not_found",
                        "message": f"Unknown agent template: {template_id}",
                    },
                },
            )
            return
        respond(200, {"ok": True, "template": detail.model_dump(mode="json")})

    def _respond_overlay_init(
        self,
        template_id: str,
        body: bytes,
        respond: JsonResponder,
    ) -> None:
        try:
            AgentTemplatePathParams(template_id=template_id)
        except ValidationError as exc:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "validation_error",
                        "message": str(exc),
                    },
                },
            )
            return

        payload: dict[str, Any] = {}
        if body:
            try:
                loaded = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                respond(
                    400,
                    {
                        "ok": False,
                        "error": {
                            "kind": "validation_error",
                            "message": f"Invalid JSON body: {exc}",
                        },
                    },
                )
                return
            if not isinstance(loaded, dict):
                respond(
                    400,
                    {
                        "ok": False,
                        "error": {
                            "kind": "validation_error",
                            "message": "Request body must be a JSON object",
                        },
                    },
                )
                return
            payload = loaded

        try:
            request = AgentOverlayInitRequest.model_validate(payload)
        except ValidationError as exc:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "validation_error",
                        "message": str(exc),
                    },
                },
            )
            return

        service = self._service()
        try:
            result = service.init_overlay(
                template_id,
                scope=AgentOverlayScope(request.scope),
                mode=AgentOverlayInitMode(request.mode),
                force=request.force,
                dry_run=request.dry_run,
            )
        except Exception as exc:
            respond(
                409 if "already exists" in str(exc).lower() else 400,
                {
                    "ok": False,
                    "error": {
                        "kind": "overlay_init_failed",
                        "message": str(exc),
                    },
                },
            )
            return

        respond(200, {"ok": True, "overlay": result.model_dump(mode="json")})

    def _respond_preview(
        self,
        template_id: str,
        query: str,
        respond: JsonResponder,
    ) -> None:
        params = parse_qs(query)
        vendor = (params.get("vendor") or ["claude_code"])[0]
        answers_raw = (params.get("answers") or [None])[0]
        answers: dict[str, str] | None = None
        if answers_raw:
            try:
                loaded = json.loads(answers_raw)
            except json.JSONDecodeError as exc:
                respond(
                    400,
                    {
                        "ok": False,
                        "error": {
                            "kind": "validation_error",
                            "message": f"Invalid answers JSON: {exc}",
                        },
                    },
                )
                return
            if not isinstance(loaded, dict):
                respond(
                    400,
                    {
                        "ok": False,
                        "error": {
                            "kind": "validation_error",
                            "message": "answers query param must be a JSON object",
                        },
                    },
                )
                return
            answers = {str(key): str(value) for key, value in loaded.items()}
        try:
            preview_query = AgentPreviewQuery(vendor=vendor)
        except ValidationError as exc:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "validation_error",
                        "message": str(exc),
                    },
                },
            )
            return
        try:
            AgentTemplatePathParams(template_id=template_id)
        except ValidationError as exc:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "validation_error",
                        "message": str(exc),
                    },
                },
            )
            return

        service = self._service()
        directory_name = self._manifest_root.name
        preview = service.preview(
            template_id,
            vendor=preview_query.vendor,
            directory_name=directory_name,
            git_remote_url=None,
            answers=answers,
            no_prompt=True,
        )
        respond(200, {"ok": True, "preview": preview.model_dump(mode="json")})

    def _respond_dispatch_plan(
        self,
        template_id: str,
        query: str,
        respond: JsonResponder,
    ) -> None:
        params = parse_qs(query)
        vendor = (params.get("vendor") or ["claude_code"])[0]
        scope = (params.get("scope") or ["project"])[0]
        project = (params.get("project") or [None])[0]
        repo = (params.get("repo") or [None])[0]
        task = (params.get("task") or [None])[0]
        try:
            AgentTemplatePathParams(template_id=template_id)
            dispatch_query = AgentDispatchQuery(
                vendor=vendor,
                scope=scope,  # type: ignore[arg-type]
                project=project,
                repo=repo,
                task=task,
            )
        except ValidationError as exc:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "validation_error",
                        "message": str(exc),
                    },
                },
            )
            return

        service = self._service()
        try:
            plan = service.dispatch_plan(
                template_id,
                vendor=dispatch_query.vendor,
                scope=dispatch_query.scope,
                project=dispatch_query.project,
                repo=dispatch_query.repo,
                task=dispatch_query.task,
            )
        except Exception as exc:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "dispatch_plan_failed",
                        "message": str(exc),
                    },
                },
            )
            return
        respond(200, {"ok": True, "plan": plan.model_dump(mode="json")})


def resolve_manifest_root(root: str) -> str:
    """Normalize manifest root path for overlay resolution."""
    path = Path(root).expanduser().resolve()
    if path.is_file():
        return str(path.parent)
    return str(path)
