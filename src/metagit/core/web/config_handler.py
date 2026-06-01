#!/usr/bin/env python
"""HTTP handlers for metagit and appconfig schema tree routes (v3 API)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Literal
from urllib.parse import urlparse

from pydantic import ValidationError

from metagit.core.appconfig import load_config as load_appconfig
from metagit.core.appconfig import save_config as save_appconfig
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.web.config_preview import (
    PreviewStyle,
    read_disk_text,
    render_appconfig_yaml,
    render_metagit_yaml,
)
from metagit.core.web.models import (
    ConfigPatchRequest,
    ConfigPreviewRequest,
    ConfigPreviewResponse,
    ConfigTreeResponse,
)
from metagit.core.web.schema_tree import SchemaTreeService

JsonResponder = Callable[[int, dict[str, Any]], None]

ConfigTarget = Literal["metagit", "appconfig"]
ValidateTarget = Literal["metagit", "appconfig", "both"]


class ConfigWebHandler:
    """Route config tree and patch operations for the local web HTTP API."""

    def __init__(
        self,
        *,
        metagit_config_path: str,
        appconfig_path: str,
    ) -> None:
        self._metagit_config_path = str(Path(metagit_config_path).resolve())
        self._appconfig_path = str(Path(appconfig_path).resolve())
        self._schema = SchemaTreeService()

    def handle(
        self,
        method: str,
        path: str,
        query: str,
        body: bytes,
        respond: JsonResponder,
    ) -> bool:
        """Dispatch config routes; return True when handled."""
        parsed_path = urlparse(path).path

        if method == "GET" and parsed_path == "/v3/config/metagit/tree":
            self._respond_metagit_tree(respond, saved=False)
            return True

        if method == "GET" and parsed_path == "/v3/config/appconfig/tree":
            self._respond_appconfig_tree(respond, saved=False)
            return True

        if method == "PATCH" and parsed_path == "/v3/config/metagit":
            self._patch_metagit(body, respond)
            return True

        if method == "PATCH" and parsed_path == "/v3/config/appconfig":
            self._patch_appconfig(body, respond)
            return True

        if method == "POST" and parsed_path == "/v3/config/validate":
            self._validate_configs(body, respond)
            return True

        if method == "GET" and parsed_path == "/v3/config/metagit/preview":
            self._preview_metagit(query, b"", respond)
            return True

        if method == "GET" and parsed_path == "/v3/config/appconfig/preview":
            self._preview_appconfig(query, b"", respond)
            return True

        if method == "POST" and parsed_path == "/v3/config/metagit/preview":
            self._preview_metagit(query, body, respond)
            return True

        if method == "POST" and parsed_path == "/v3/config/appconfig/preview":
            self._preview_appconfig(query, body, respond)
            return True

        return False

    def _respond_metagit_tree(
        self,
        respond: JsonResponder,
        *,
        config: MetagitConfig | None = None,
        validation_errors: list[dict[str, str]] | None = None,
        saved: bool,
    ) -> None:
        loaded = config
        errors = list(validation_errors or [])
        if loaded is None:
            loaded_result = self._load_metagit(respond)
            if loaded_result is None:
                return
            loaded = loaded_result
        response = self._tree_response(
            target="metagit",
            config_path=self._metagit_config_path,
            config=loaded,
            model_class=MetagitConfig,
            validation_errors=errors,
            saved=saved,
            mask_secrets=False,
        )
        respond(200, response.model_dump(mode="json"))

    def _respond_appconfig_tree(
        self,
        respond: JsonResponder,
        *,
        config: AppConfig | None = None,
        validation_errors: list[dict[str, str]] | None = None,
        saved: bool,
    ) -> None:
        loaded = config
        errors = list(validation_errors or [])
        if loaded is None:
            loaded_result = self._load_appconfig(respond)
            if loaded_result is None:
                return
            loaded = loaded_result
        response = self._tree_response(
            target="appconfig",
            config_path=self._appconfig_path,
            config=loaded,
            model_class=AppConfig,
            validation_errors=errors,
            saved=saved,
            mask_secrets=True,
        )
        respond(200, response.model_dump(mode="json"))

    def _patch_metagit(self, body: bytes, respond: JsonResponder) -> None:
        loaded = self._load_metagit(respond)
        if loaded is None:
            return
        patch = self._parse_patch(body, respond)
        if patch is None:
            return
        updated, validation_errors = self._schema.apply_operations(
            loaded,
            MetagitConfig,
            patch.operations,
        )
        saved = False
        if patch.save:
            if validation_errors:
                response = self._tree_response(
                    target="metagit",
                    config_path=self._metagit_config_path,
                    config=updated,
                    model_class=MetagitConfig,
                    validation_errors=validation_errors,
                    saved=False,
                    mask_secrets=False,
                )
                respond(422, response.model_dump(mode="json"))
                return
            manager = MetagitConfigManager(self._metagit_config_path)
            save_result = manager.save_config(
                updated,
                auto_format=patch.auto_format,
            )
            if isinstance(save_result, Exception):
                respond(
                    500,
                    {
                        "ok": False,
                        "error": {"kind": "save_error", "message": str(save_result)},
                    },
                )
                return
            saved = True
        self._respond_metagit_tree(
            respond,
            config=updated,
            validation_errors=validation_errors,
            saved=saved,
        )

    def _patch_appconfig(self, body: bytes, respond: JsonResponder) -> None:
        loaded = self._load_appconfig(respond)
        if loaded is None:
            return
        patch = self._parse_patch(body, respond)
        if patch is None:
            return
        updated, validation_errors = self._schema.apply_operations(
            loaded,
            AppConfig,
            patch.operations,
        )
        saved = False
        if patch.save:
            if validation_errors:
                response = self._tree_response(
                    target="appconfig",
                    config_path=self._appconfig_path,
                    config=updated,
                    model_class=AppConfig,
                    validation_errors=validation_errors,
                    saved=False,
                    mask_secrets=True,
                )
                respond(422, response.model_dump(mode="json"))
                return
            save_result = save_appconfig(
                self._appconfig_path,
                updated,
                auto_format=patch.auto_format,
            )
            if isinstance(save_result, Exception):
                respond(
                    500,
                    {
                        "ok": False,
                        "error": {"kind": "save_error", "message": str(save_result)},
                    },
                )
                return
            saved = True
        self._respond_appconfig_tree(
            respond,
            config=updated,
            validation_errors=validation_errors,
            saved=saved,
        )

    def _validate_configs(self, body: bytes, respond: JsonResponder) -> None:
        payload = self._parse_body(body, respond, required=False) or {}
        target_raw = payload.get("target", "both")
        if target_raw not in {"metagit", "appconfig", "both"}:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_target",
                        "message": "target must be metagit, appconfig, or both",
                    },
                },
            )
            return
        target: ValidateTarget = target_raw
        results: list[dict[str, Any]] = []
        targets: list[ConfigTarget] = (
            ["metagit", "appconfig"] if target == "both" else [target]
        )
        for item in targets:
            if item == "metagit":
                errors = self._validation_errors_for_metagit()
            else:
                errors = self._validation_errors_for_appconfig()
            results.append(
                {
                    "target": item,
                    "ok": len(errors) == 0,
                    "validation_errors": errors,
                }
            )
        respond(
            200,
            {
                "ok": all(entry["ok"] for entry in results),
                "results": results,
            },
        )

    def _validation_errors_for_metagit(self) -> list[dict[str, str]]:
        manager = MetagitConfigManager(self._metagit_config_path)
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            return [{"path": "", "message": str(loaded)}]
        try:
            MetagitConfig.model_validate(loaded.model_dump(mode="python"))
        except ValidationError as exc:
            return [
                {
                    "path": self._format_error_path(err.get("loc", ())),
                    "message": err.get("msg", "validation error"),
                }
                for err in exc.errors()
            ]
        return []

    def _validation_errors_for_appconfig(self) -> list[dict[str, str]]:
        loaded = load_appconfig(self._appconfig_path)
        if isinstance(loaded, Exception):
            return [{"path": "", "message": str(loaded)}]
        try:
            AppConfig.model_validate(loaded.model_dump(mode="python"))
        except ValidationError as exc:
            return [
                {
                    "path": self._format_error_path(err.get("loc", ())),
                    "message": err.get("msg", "validation error"),
                }
                for err in exc.errors()
            ]
        return []

    def _preview_metagit(
        self,
        query: str,
        body: bytes,
        respond: JsonResponder,
    ) -> None:
        request = self._parse_preview_request(query, body, respond)
        if request is None:
            return
        if request.style == "disk" and request.operations:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_preview",
                        "message": "disk preview cannot include draft operations",
                    },
                },
            )
            return
        loaded = self._load_metagit(respond)
        if loaded is None:
            return
        config = loaded
        validation_errors: list[dict[str, str]] = []
        draft = bool(request.operations)
        if draft:
            config, validation_errors = self._schema.apply_operations(
                loaded,
                MetagitConfig,
                request.operations,
            )
        if request.style == "disk":
            yaml_text = read_disk_text(self._metagit_config_path)
        else:
            yaml_text = render_metagit_yaml(config, style=request.style)
        response = ConfigPreviewResponse(
            ok=len(validation_errors) == 0,
            target="metagit",
            config_path=self._metagit_config_path,
            style=request.style,
            yaml=yaml_text,
            draft=draft,
            validation_errors=validation_errors,
        )
        respond(200, response.model_dump(mode="json"))

    def _preview_appconfig(
        self,
        query: str,
        body: bytes,
        respond: JsonResponder,
    ) -> None:
        request = self._parse_preview_request(query, body, respond)
        if request is None:
            return
        if request.style == "disk" and request.operations:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_preview",
                        "message": "disk preview cannot include draft operations",
                    },
                },
            )
            return
        loaded = self._load_appconfig(respond)
        if loaded is None:
            return
        config = loaded
        validation_errors: list[dict[str, str]] = []
        draft = bool(request.operations)
        if draft:
            config, validation_errors = self._schema.apply_operations(
                loaded,
                AppConfig,
                request.operations,
            )
        if request.style == "disk":
            yaml_text = read_disk_text(self._appconfig_path)
        else:
            yaml_text = render_appconfig_yaml(
                config,
                config_path=self._appconfig_path,
                style=request.style,
                mask_secrets=True,
            )
        response = ConfigPreviewResponse(
            ok=len(validation_errors) == 0,
            target="appconfig",
            config_path=self._appconfig_path,
            style=request.style,
            yaml=yaml_text,
            draft=draft,
            validation_errors=validation_errors,
        )
        respond(200, response.model_dump(mode="json"))

    def _parse_preview_request(
        self,
        query: str,
        body: bytes,
        respond: JsonResponder,
    ) -> ConfigPreviewRequest | None:
        from urllib.parse import parse_qs

        params = parse_qs(query, keep_blank_values=True)
        style_raw = (params.get("style") or ["normalized"])[0]
        if style_raw not in {"normalized", "minimal", "disk"}:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_style",
                        "message": "style must be normalized, minimal, or disk",
                    },
                },
            )
            return None
        style: PreviewStyle = style_raw
        if not body:
            return ConfigPreviewRequest(style=style, operations=[])
        payload = self._parse_body(body, respond, required=False)
        if payload is None:
            return None
        try:
            parsed = ConfigPreviewRequest.model_validate(
                {"style": payload.get("style", style), **payload}
            )
        except ValidationError as exc:
            respond(
                400,
                {
                    "ok": False,
                    "error": {"kind": "invalid_body", "message": str(exc)},
                },
            )
            return None
        if parsed.style not in {"normalized", "minimal", "disk"}:
            respond(
                400,
                {
                    "ok": False,
                    "error": {
                        "kind": "invalid_style",
                        "message": "style must be normalized, minimal, or disk",
                    },
                },
            )
            return None
        return parsed

    def _tree_response(
        self,
        *,
        target: ConfigTarget,
        config_path: str,
        config: MetagitConfig | AppConfig,
        model_class: type[MetagitConfig] | type[AppConfig],
        validation_errors: list[dict[str, str]],
        saved: bool,
        mask_secrets: bool,
    ) -> ConfigTreeResponse:
        tree = self._schema.build_tree(
            config,
            model_class,
            mask_secrets=mask_secrets,
        )
        return ConfigTreeResponse(
            ok=len(validation_errors) == 0,
            target=target,
            config_path=config_path,
            tree=tree,
            validation_errors=validation_errors,
            saved=saved,
        )

    def _load_metagit(self, respond: JsonResponder) -> MetagitConfig | None:
        manager = MetagitConfigManager(self._metagit_config_path)
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

    def _parse_patch(
        self,
        body: bytes,
        respond: JsonResponder,
    ) -> ConfigPatchRequest | None:
        payload = self._parse_body(body, respond, required=True)
        if payload is None:
            return None
        try:
            return ConfigPatchRequest.model_validate(payload)
        except ValidationError as exc:
            respond(
                400,
                {
                    "ok": False,
                    "error": {"kind": "invalid_body", "message": str(exc)},
                },
            )
            return None

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

    @staticmethod
    def _format_error_path(loc: tuple[Any, ...]) -> str:
        parts: list[str] = []
        for item in loc:
            if isinstance(item, int):
                parts.append(f"[{item}]")
            else:
                if parts:
                    parts.append(f".{item}")
                else:
                    parts.append(str(item))
        return "".join(parts)
