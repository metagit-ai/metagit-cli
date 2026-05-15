#!/usr/bin/env python
"""
Minimal MCP stdio runtime for Metagit tools and resources.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.mcp.gate import WorkspaceGate
from metagit.core.mcp.models import McpActivationState, WorkspaceStatus
from metagit.core.mcp.resources import ResourcePublisher
from metagit.core.mcp.root_resolver import WorkspaceRootResolver
from metagit.core.mcp.services.bootstrap_sampling import BootstrapSamplingService
from metagit.core.mcp.services.discovery_context import DiscoveryContextService
from metagit.core.mcp.services.ops_log import OperationsLogService
from metagit.core.mcp.services.project_context import ProjectContextService
from metagit.core.mcp.services.repo_ops import RepoOperationsService
from metagit.core.mcp.services.workspace_snapshot import WorkspaceSnapshotService
from metagit.core.mcp.services.upstream_hints import UpstreamHintService
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.mcp.services.workspace_search import WorkspaceSearchService
from metagit.core.mcp.services.workspace_semantic_search import (
    WorkspaceSemanticSearchService,
)
from metagit.core.mcp.services.cross_project_dependencies import (
    CrossProjectDependencyService,
)
from metagit.core.mcp.services.workspace_health import WorkspaceHealthService
from metagit.core.mcp.services.workspace_sync import WorkspaceSyncService
from metagit.core.mcp.services.workspace_template import WorkspaceTemplateService
from metagit.core.mcp.tool_registry import ToolRegistry
from metagit.core.project.search_service import ManagedRepoSearchService
from metagit.core.mcp.tools.bootstrap_plan_only import (
    metagit_bootstrap_config_plan_only,
)
from metagit.core.mcp.tools.workspace_status import metagit_workspace_status


class InvalidToolArgumentsError(Exception):
    """Raised when tool call arguments are invalid."""


class MetagitMcpRuntime:
    """MCP runtime over stdio transport."""

    def __init__(self, root: Optional[str] = None) -> None:
        self._root_override = root
        self._resolver = WorkspaceRootResolver()
        self._gate = WorkspaceGate()
        self._registry = ToolRegistry()
        self._index_service = WorkspaceIndexService()
        self._search_service = WorkspaceSearchService()
        self._semantic_search = WorkspaceSemanticSearchService()
        self._workspace_sync = WorkspaceSyncService()
        self._cross_project_deps = CrossProjectDependencyService()
        self._workspace_health = WorkspaceHealthService()
        self._workspace_template = WorkspaceTemplateService()
        self._managed_repo_search = ManagedRepoSearchService()
        self._hints_service = UpstreamHintService()
        self._repo_ops = RepoOperationsService()
        self._project_context = ProjectContextService()
        self._workspace_snapshot = WorkspaceSnapshotService()
        self._discovery_service = DiscoveryContextService()
        self._bootstrap_service = BootstrapSamplingService(sampling_supported=False)
        self._ops_log = OperationsLogService()
        self._resources = ResourcePublisher(ops_log=self._ops_log)
        self._initialized = False
        self._sampling_supported = False
        self._next_server_request_id = 10_000
        self._last_init_params: dict[str, Any] = {}
        self._tool_schemas: dict[str, dict[str, Any]] = {
            "metagit_workspace_status": {"type": "object", "properties": {}},
            "metagit_bootstrap_config_plan_only": {"type": "object", "properties": {}},
            "metagit_workspace_index": {"type": "object", "properties": {}},
            "metagit_workspace_search": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "preset": {"type": "string"},
                    "max_results": {"type": "integer", "minimum": 1},
                    "repos": {"type": "array", "items": {"type": "string"}},
                    "paths": {"type": "array", "items": {"type": "string"}},
                    "exclude": {"type": "array", "items": {"type": "string"}},
                    "context_lines": {"type": "integer", "minimum": 0},
                    "include_paths": {"type": "boolean"},
                    "intent": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_workspace_semantic_search": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "repos": {"type": "array", "items": {"type": "string"}},
                    "task_context": {"type": "string"},
                    "goal": {"type": "string"},
                    "limit_per_repo": {"type": "integer", "minimum": 1},
                    "timeout_seconds": {"type": "integer", "minimum": 5},
                },
                "additionalProperties": False,
            },
            "metagit_repo_search": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "project": {"type": "string"},
                    "exact": {"type": "boolean"},
                    "synced_only": {"type": "boolean"},
                    "limit": {"type": "integer", "minimum": 1},
                    "sort": {
                        "type": "string",
                        "enum": ["score", "project", "name"],
                    },
                    "status": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "has_url": {"type": "boolean"},
                    "sync_enabled": {"type": "boolean"},
                    "tags": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "additionalProperties": False,
            },
            "metagit_workspace_sync": {
                "type": "object",
                "properties": {
                    "repos": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["fetch", "pull", "clone"],
                    },
                    "only_if": {
                        "type": "string",
                        "enum": ["any", "missing", "dirty", "behind_origin"],
                    },
                    "allow_mutation": {"type": "boolean"},
                    "max_parallel": {"type": "integer", "minimum": 1},
                    "dry_run": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_upstream_hints": {
                "type": "object",
                "required": ["blocker"],
                "properties": {"blocker": {"type": "string"}},
                "additionalProperties": False,
            },
            "metagit_repo_inspect": {
                "type": "object",
                "required": ["repo_path"],
                "properties": {"repo_path": {"type": "string"}},
                "additionalProperties": False,
            },
            "metagit_repo_sync": {
                "type": "object",
                "required": ["repo_path"],
                "properties": {
                    "repo_path": {"type": "string"},
                    "mode": {
                        "type": "string",
                        "enum": ["fetch", "pull", "clone"],
                    },
                    "allow_mutation": {"type": "boolean"},
                    "origin_url": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_bootstrap_config": {
                "type": "object",
                "properties": {"confirm_write": {"type": "boolean"}},
                "additionalProperties": False,
            },
            "metagit_project_context_switch": {
                "type": "object",
                "required": ["project_name"],
                "properties": {
                    "project_name": {"type": "string"},
                    "setup_env": {"type": "boolean"},
                    "restore_session": {"type": "boolean"},
                    "save_previous": {"type": "boolean"},
                    "primary_repo": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_workspace_state_snapshot": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "project_name": {"type": "string"},
                    "include_all_projects": {"type": "boolean"},
                    "include_env_state": {"type": "boolean"},
                    "link_session": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_workspace_state_restore": {
                "type": "object",
                "required": ["snapshot_id"],
                "properties": {
                    "snapshot_id": {"type": "string"},
                    "switch_project": {"type": "boolean"},
                    "restore_session": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_cross_project_dependencies": {
                "type": "object",
                "required": ["source_project"],
                "properties": {
                    "source_project": {"type": "string"},
                    "dependency_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "declared",
                                "imports",
                                "shared_config",
                                "url_match",
                                "ref",
                            ],
                        },
                    },
                    "depth": {"type": "integer", "minimum": 1},
                    "include_external_repos": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_workspace_health_check": {
                "type": "object",
                "properties": {
                    "check_git_status": {"type": "boolean"},
                    "check_dependencies": {"type": "boolean"},
                    "check_stale_branches": {"type": "boolean"},
                    "check_gitnexus": {"type": "boolean"},
                    "project_name": {"type": "string"},
                    "branch_head_warning_days": {"type": "number", "minimum": 0},
                    "branch_head_critical_days": {"type": "number", "minimum": 0},
                    "integration_stale_days": {"type": "number", "minimum": 0},
                },
                "additionalProperties": False,
            },
            "metagit_workspace_discover": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string"},
                    "pattern": {"type": "string"},
                    "repos": {"type": "array", "items": {"type": "string"}},
                    "project_scope": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "exclude_generated": {"type": "boolean"},
                    "max_results": {"type": "integer", "minimum": 1},
                    "categorize": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_project_template_apply": {
                "type": "object",
                "required": ["template", "target_projects"],
                "properties": {
                    "template": {"type": "string"},
                    "target_projects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                    "dry_run": {"type": "boolean"},
                    "confirm_apply": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_session_update": {
                "type": "object",
                "required": ["project_name"],
                "properties": {
                    "project_name": {"type": "string"},
                    "recent_repos": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "primary_repo_path": {"type": "string"},
                    "agent_notes": {"type": "string"},
                    "env_overrides": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "additionalProperties": False,
            },
        }

    def status_snapshot(self) -> dict[str, Any]:
        """Return a one-shot runtime status snapshot."""
        status, _ = self._resolve_status_and_config()
        return {
            "state": status.state.value,
            "root": status.root_path,
            "tools": len(self._registry.list_tools(status=status)),
        }

    def run_stdio(self) -> None:
        """Run JSON-RPC message loop over stdio framing."""
        while True:
            request = self._read_message()
            if request is None:
                return

            response = self._handle_request(request=request)
            if response is not None:
                self._write_message(response)

    def _handle_request(self, request: dict[str, Any]) -> Optional[dict[str, Any]]:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "notifications/initialized":
            self._initialized = True
            return None

        try:
            if method == "initialize":
                self._last_init_params = params
                result = self._handle_initialize()
            elif method == "tools/list":
                result = self._handle_tools_list()
            elif method == "tools/call":
                result = self._handle_tools_call(params=params)
            elif method == "resources/list":
                result = self._handle_resources_list()
            elif method == "resources/read":
                result = self._handle_resources_read(params=params)
            elif method == "ping":
                result = {}
            else:
                return self._error_response(
                    request_id=request_id,
                    code=-32601,
                    message=f"Method not found: {method}",
                )
        except InvalidToolArgumentsError as exc:
            return self._error_response(
                request_id=request_id,
                code=-32602,
                message=str(exc),
                data={"kind": "invalid_arguments"},
            )
        except Exception as exc:
            return self._error_response(
                request_id=request_id,
                code=-32000,
                message=str(exc),
            )

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    def _handle_initialize(self) -> dict[str, Any]:
        # MCP clients advertise capabilities at initialize time.
        # We use this to decide whether server-driven sampling can be requested.
        params = self._last_init_params
        client_capabilities = params.get("capabilities", {}) if params else {}
        self._sampling_supported = "sampling" in client_capabilities
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "metagit-mcp", "version": "0.1.0"},
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"listChanged": False},
            },
        }

    def _handle_tools_list(self) -> dict[str, Any]:
        status, _ = self._resolve_status_and_config()
        tool_names = self._registry.list_tools(status=status)
        tools: list[dict[str, Any]] = []
        for name in tool_names:
            tools.append(
                {
                    "name": name,
                    "description": f"Metagit MCP tool: {name}",
                    "inputSchema": self._tool_schemas.get(
                        name, {"type": "object", "properties": {}}
                    ),
                }
            )
        return {"tools": tools}

    def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        arguments = params.get("arguments", {}) or {}
        status, config = self._resolve_status_and_config()
        allowed = set(self._registry.list_tools(status=status))
        if name not in allowed:
            raise InvalidToolArgumentsError(
                f"Tool not available in current state: {name}"
            )

        result = self._dispatch_tool(
            name=name,
            arguments=arguments,
            status=status,
            config=config,
        )
        self._ops_log.append(action="tool_call", detail=name)
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    def _handle_resources_list(self) -> dict[str, Any]:
        status, _ = self._resolve_status_and_config()
        resources = []
        if status.state == McpActivationState.ACTIVE:
            resources.extend(
                [
                    {
                        "uri": "metagit://workspace/config",
                        "name": "Workspace Config",
                    },
                    {
                        "uri": "metagit://workspace/repos/status",
                        "name": "Workspace Repos Status",
                    },
                    {
                        "uri": "metagit://workspace/health",
                        "name": "Workspace Health",
                    },
                    {
                        "uri": "metagit://workspace/context",
                        "name": "Workspace Context",
                    },
                ]
            )
        resources.append(
            {"uri": "metagit://workspace/ops-log", "name": "Operations Log"}
        )
        return {"resources": resources}

    def _handle_resources_read(self, params: dict[str, Any]) -> dict[str, Any]:
        uri = params.get("uri")
        if not uri:
            raise ValueError("uri is required")
        status, config = self._resolve_status_and_config()
        repos = self._build_repo_index(status=status, config=config)
        health_payload = None
        if uri == "metagit://workspace/health" and config and status.root_path:
            health_payload = self._workspace_health.check(
                config=config,
                workspace_root=status.root_path,
            ).model_dump(mode="json")
        payload = self._resources.get_resource(
            uri=uri,
            config=config,
            repos_status=repos,
            workspace_root=status.root_path,
            health_payload=health_payload,
        )
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(payload),
                }
            ]
        }

    def _dispatch_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        status: WorkspaceStatus,
        config: Any,
    ) -> dict[str, Any]:
        if name == "metagit_workspace_status":
            return metagit_workspace_status(status)

        if name == "metagit_bootstrap_config_plan_only":
            return metagit_bootstrap_config_plan_only(reason=status.reason)

        if name == "metagit_workspace_index":
            return {"repos": self._build_repo_index(status=status, config=config)}

        if name == "metagit_workspace_search":
            repos = self._build_repo_index(status=status, config=config)
            raw_repos = arguments.get("repos")
            repo_selectors = (
                [str(item) for item in raw_repos]
                if isinstance(raw_repos, list)
                else None
            )
            repo_paths = self._search_service.filter_repo_paths(
                repo_rows=repos,
                repos=repo_selectors,
            )
            query = str(arguments.get("query", "")).strip()
            if not query:
                raise InvalidToolArgumentsError("query is required")
            raw_paths = arguments.get("paths")
            raw_exclude = arguments.get("exclude")
            return {
                "hits": self._search_service.search(
                    query=query,
                    repo_paths=repo_paths,
                    preset=arguments.get("preset"),
                    max_results=int(arguments.get("max_results", 25)),
                    paths=[str(item) for item in raw_paths]
                    if isinstance(raw_paths, list)
                    else None,
                    exclude=[str(item) for item in raw_exclude]
                    if isinstance(raw_exclude, list)
                    else None,
                    context_lines=int(arguments.get("context_lines", 0)),
                    include_paths=bool(arguments.get("include_paths", False)),
                    intent=arguments.get("intent"),
                )
            }

        if name == "metagit_workspace_semantic_search":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "semantic workspace search requires an active workspace"
                )
            repos = self._build_repo_index(status=status, config=config)
            raw_sem_repos = arguments.get("repos")
            sem_selectors = (
                [str(item) for item in raw_sem_repos]
                if isinstance(raw_sem_repos, list)
                else None
            )
            repo_paths = self._search_service.filter_repo_paths(
                repo_rows=repos,
                repos=sem_selectors,
            )
            sem_query = str(arguments.get("query", "")).strip()
            if not sem_query:
                raise InvalidToolArgumentsError("query is required")
            limit_sem = int(arguments.get("limit_per_repo", 5))
            if limit_sem < 1:
                raise InvalidToolArgumentsError("limit_per_repo must be at least 1")
            timeout_sem = int(arguments.get("timeout_seconds", 120))
            if timeout_sem < 5:
                raise InvalidToolArgumentsError("timeout_seconds must be at least 5")
            return self._semantic_search.search_across_repos(
                query=sem_query,
                repo_paths=repo_paths,
                task_context=arguments.get("task_context"),
                goal=arguments.get("goal"),
                limit_per_repo=limit_sem,
                timeout_seconds=timeout_sem,
            )

        if name == "metagit_repo_search":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "managed repo search requires an active workspace"
                )
            query = str(arguments.get("query", "")).strip()
            if not query:
                raise InvalidToolArgumentsError("query is required")
            raw_tags = arguments.get("tags")
            tag_filter: dict[str, str] | None = None
            if isinstance(raw_tags, dict) and raw_tags:
                tag_filter = {str(k): str(v) for k, v in raw_tags.items()}
            limit_raw = arguments.get("limit", 10)
            try:
                limit_val = int(limit_raw)
            except (TypeError, ValueError) as exc:
                raise InvalidToolArgumentsError("limit must be an integer") from exc
            if limit_val < 1:
                raise InvalidToolArgumentsError("limit must be at least 1")
            raw_status = arguments.get("status")
            status_filter = (
                [str(item) for item in raw_status]
                if isinstance(raw_status, list)
                else None
            )
            sort_val = str(arguments.get("sort", "score"))
            if sort_val not in {"score", "project", "name"}:
                raise InvalidToolArgumentsError("sort must be score, project, or name")
            has_url = arguments.get("has_url")
            has_url_val = bool(has_url) if isinstance(has_url, bool) else None
            sync_enabled = arguments.get("sync_enabled")
            sync_enabled_val = (
                bool(sync_enabled) if isinstance(sync_enabled, bool) else None
            )
            result = self._managed_repo_search.search(
                config=config,
                workspace_root=status.root_path,
                query=query,
                project=arguments.get("project"),
                exact=bool(arguments.get("exact", False)),
                synced_only=bool(arguments.get("synced_only", False)),
                tags=tag_filter,
                status=status_filter,
                has_url=has_url_val,
                sync_enabled=sync_enabled_val,
                sort=sort_val,
                limit=limit_val,
            )
            return result.model_dump(mode="json")

        if name == "metagit_upstream_hints":
            blocker = str(arguments.get("blocker", "")).strip()
            if not blocker:
                raise InvalidToolArgumentsError("blocker is required")
            repos = self._build_repo_index(status=status, config=config)
            return {
                "hints": self._hints_service.rank(blocker=blocker, repo_context=repos)
            }

        if name == "metagit_repo_inspect":
            repo_path = str(arguments.get("repo_path", "")).strip()
            if not repo_path:
                raise InvalidToolArgumentsError("repo_path is required")
            return self._repo_ops.inspect(repo_path=repo_path)

        if name == "metagit_repo_sync":
            return self._repo_ops.sync(
                repo_path=str(arguments.get("repo_path", "")),
                mode=str(arguments.get("mode", "fetch")),
                allow_mutation=bool(arguments.get("allow_mutation", False)),
                origin_url=arguments.get("origin_url"),
            )

        if name == "metagit_workspace_sync":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "workspace sync requires an active workspace"
                )
            repos = self._build_repo_index(status=status, config=config)
            raw_repos = arguments.get("repos")
            repo_selectors = (
                [str(item) for item in raw_repos]
                if isinstance(raw_repos, list)
                else ["all"]
            )
            only_if = str(arguments.get("only_if", "any"))
            if only_if not in {"any", "missing", "dirty", "behind_origin"}:
                raise InvalidToolArgumentsError(
                    "only_if must be any, missing, dirty, or behind_origin"
                )
            max_parallel_raw = arguments.get("max_parallel", 4)
            try:
                max_parallel = int(max_parallel_raw)
            except (TypeError, ValueError) as exc:
                raise InvalidToolArgumentsError(
                    "max_parallel must be an integer"
                ) from exc
            if max_parallel < 1:
                raise InvalidToolArgumentsError("max_parallel must be at least 1")
            return self._workspace_sync.sync_many(
                repo_rows=repos,
                repos=repo_selectors,
                mode=str(arguments.get("mode", "fetch")),
                only_if=only_if,
                allow_mutation=bool(arguments.get("allow_mutation", False)),
                max_parallel=max_parallel,
                dry_run=bool(arguments.get("dry_run", False)),
            )

        if name == "metagit_project_context_switch":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "project context requires an active workspace"
                )
            project_name = str(arguments.get("project_name", "")).strip()
            if not project_name:
                raise InvalidToolArgumentsError("project_name is required")
            bundle = self._project_context.switch(
                config=config,
                workspace_root=status.root_path,
                project_name=project_name,
                setup_env=bool(arguments.get("setup_env", True)),
                restore_session=bool(arguments.get("restore_session", True)),
                save_previous=bool(arguments.get("save_previous", True)),
                primary_repo=arguments.get("primary_repo"),
            )
            return bundle.model_dump(mode="json")

        if name == "metagit_workspace_state_snapshot":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "workspace snapshot requires an active workspace"
                )
            return self._workspace_snapshot.create(
                config=config,
                workspace_root=status.root_path,
                label=arguments.get("label"),
                project_name=arguments.get("project_name"),
                include_all_projects=bool(arguments.get("include_all_projects", False)),
                include_env_state=bool(arguments.get("include_env_state", True)),
                link_session=bool(arguments.get("link_session", True)),
            )

        if name == "metagit_workspace_state_restore":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "workspace snapshot restore requires an active workspace"
                )
            snapshot_id = str(arguments.get("snapshot_id", "")).strip()
            if not snapshot_id:
                raise InvalidToolArgumentsError("snapshot_id is required")
            result = self._workspace_snapshot.restore(
                config=config,
                workspace_root=status.root_path,
                snapshot_id=snapshot_id,
                switch_project=bool(arguments.get("switch_project", True)),
                restore_session=bool(arguments.get("restore_session", True)),
            )
            return result.model_dump(mode="json")

        if name == "metagit_workspace_health_check":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "workspace health check requires an active workspace"
                )
            raw_warn = arguments.get("branch_head_warning_days")
            raw_crit = arguments.get("branch_head_critical_days")
            raw_integration = arguments.get("integration_stale_days")
            try:
                branch_warn = float(raw_warn) if raw_warn is not None else 180.0
                branch_crit = float(raw_crit) if raw_crit is not None else 365.0
                integration_td = (
                    float(raw_integration) if raw_integration is not None else 90.0
                )
            except (TypeError, ValueError) as exc:
                raise InvalidToolArgumentsError(
                    "branch age thresholds must be numbers"
                ) from exc
            if branch_warn < 0 or branch_crit < 0 or integration_td < 0:
                raise InvalidToolArgumentsError(
                    "branch age thresholds must be non-negative"
                )
            result = self._workspace_health.check(
                config=config,
                workspace_root=status.root_path,
                check_git_status=bool(arguments.get("check_git_status", True)),
                check_dependencies=bool(arguments.get("check_dependencies", True)),
                check_stale_branches=bool(arguments.get("check_stale_branches", True)),
                check_gitnexus=bool(arguments.get("check_gitnexus", True)),
                project_name=arguments.get("project_name"),
                branch_head_warning_days=branch_warn,
                branch_head_critical_days=branch_crit,
                integration_stale_days=integration_td,
            )
            return result.model_dump(mode="json")

        if name == "metagit_workspace_discover":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "workspace discover requires an active workspace"
                )
            intent = arguments.get("intent")
            pattern = arguments.get("pattern")
            if not intent and not pattern:
                raise InvalidToolArgumentsError("intent or pattern is required")
            repos = self._build_repo_index(status=status, config=config)
            raw_repos = arguments.get("repos")
            raw_scope = arguments.get("project_scope")
            selectors = (
                [str(item) for item in raw_repos]
                if isinstance(raw_repos, list)
                else (
                    [str(item) for item in raw_scope]
                    if isinstance(raw_scope, list)
                    else None
                )
            )
            repo_paths = self._search_service.filter_repo_paths(
                repo_rows=repos,
                repos=selectors,
            )
            return self._search_service.discover_files(
                repo_paths=repo_paths,
                intent=str(intent) if intent else None,
                pattern=str(pattern) if pattern else None,
                exclude_generated=bool(arguments.get("exclude_generated", True)),
                max_results=int(arguments.get("max_results", 200)),
                categorize=bool(arguments.get("categorize", True)),
            )

        if name == "metagit_project_template_apply":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "template apply requires an active workspace"
                )
            template = str(arguments.get("template", "")).strip()
            raw_targets = arguments.get("target_projects")
            if not template:
                raise InvalidToolArgumentsError("template is required")
            if not isinstance(raw_targets, list) or not raw_targets:
                raise InvalidToolArgumentsError("target_projects is required")
            return self._workspace_template.apply(
                config=config,
                workspace_root=status.root_path,
                template=template,
                target_projects=[str(item) for item in raw_targets],
                dry_run=bool(arguments.get("dry_run", True)),
                confirm_apply=bool(arguments.get("confirm_apply", False)),
            )

        if name == "metagit_cross_project_dependencies":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "cross-project dependencies require an active workspace"
                )
            source_project = str(arguments.get("source_project", "")).strip()
            if not source_project:
                raise InvalidToolArgumentsError("source_project is required")
            raw_types = arguments.get("dependency_types")
            dependency_types = (
                [str(item) for item in raw_types]
                if isinstance(raw_types, list)
                else None
            )
            depth_raw = arguments.get("depth", 2)
            try:
                depth_val = int(depth_raw)
            except (TypeError, ValueError) as exc:
                raise InvalidToolArgumentsError("depth must be an integer") from exc
            if depth_val < 1:
                raise InvalidToolArgumentsError("depth must be at least 1")
            result = self._cross_project_deps.map_dependencies(
                config=config,
                workspace_root=status.root_path,
                source_project=source_project,
                dependency_types=dependency_types,
                depth=depth_val,
                include_external_repos=bool(
                    arguments.get("include_external_repos", False)
                ),
            )
            return result.model_dump(mode="json")

        if name == "metagit_session_update":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError(
                    "session update requires an active workspace"
                )
            project_name = str(arguments.get("project_name", "")).strip()
            if not project_name:
                raise InvalidToolArgumentsError("project_name is required")
            recent = arguments.get("recent_repos")
            recent_repos = (
                [str(item) for item in recent] if isinstance(recent, list) else None
            )
            env_raw = arguments.get("env_overrides")
            env_overrides = (
                {str(k): str(v) for k, v in env_raw.items()}
                if isinstance(env_raw, dict)
                else None
            )
            try:
                return self._project_context.update_session(
                    config=config,
                    workspace_root=status.root_path,
                    project_name=project_name,
                    recent_repos=recent_repos,
                    primary_repo_path=arguments.get("primary_repo_path"),
                    agent_notes=arguments.get("agent_notes"),
                    env_overrides=env_overrides,
                )
            except ValueError as exc:
                raise InvalidToolArgumentsError(str(exc)) from exc

        if name == "metagit_bootstrap_config":
            root = status.root_path or str(Path.cwd())
            context = self._discovery_service.build_context(repo_root=root)
            if self._sampling_supported:
                sampling_payload = self._request_client_sampling(context=context)
                if sampling_payload and sampling_payload.get("content"):
                    sampled_text = self._extract_sampling_text(sampling_payload)
                    if sampled_text:

                        def sampler(_payload: dict[str, str]) -> str:
                            _ = _payload
                            return sampled_text

                        sampled_service = BootstrapSamplingService(
                            sampling_supported=True,
                            sampler=sampler,
                        )
                        return sampled_service.generate(
                            context=context,
                            confirm_write=bool(arguments.get("confirm_write", False)),
                        )
            return self._bootstrap_service.generate(
                context=context,
                confirm_write=bool(arguments.get("confirm_write", False)),
            )

        raise ValueError(f"Unsupported tool: {name}")

    def _resolve_status_and_config(self) -> tuple[WorkspaceStatus, Any]:
        resolved_root = self._resolver.resolve(
            cwd=os.getcwd(), cli_root=self._root_override
        )
        status = self._gate.evaluate(root_path=resolved_root)
        config = None
        if status.state == McpActivationState.ACTIVE and status.root_path:
            manager = MetagitConfigManager(
                config_path=Path(status.root_path) / ".metagit.yml"
            )
            loaded = manager.load_config()
            config = None if isinstance(loaded, Exception) else loaded
        return status, config

    def _build_repo_index(
        self, status: WorkspaceStatus, config: Any
    ) -> list[dict[str, Any]]:
        if (
            status.state != McpActivationState.ACTIVE
            or not config
            or not status.root_path
        ):
            return []
        return self._index_service.build_index(
            config=config, workspace_root=status.root_path
        )

    def _error_response(
        self,
        request_id: Any,
        code: int,
        message: str,
        data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        error: dict[str, Any] = {"code": code, "message": message}
        if data:
            error["data"] = data
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error,
        }

    def _read_message(self) -> Optional[dict[str, Any]]:
        """Read one MCP-framed JSON-RPC message from stdin."""
        content_length: Optional[int] = None

        while True:
            header_line = sys.stdin.buffer.readline()
            if not header_line:
                return None
            if header_line in {b"\n", b"\r\n"}:
                break

            header_text = header_line.decode("utf-8").strip()
            if not header_text:
                continue
            if ":" not in header_text:
                continue
            key, value = header_text.split(":", 1)
            if key.lower().strip() == "content-length":
                content_length = int(value.strip())

        if content_length is None:
            return None

        body = sys.stdin.buffer.read(content_length)
        if not body:
            return None
        return json.loads(body.decode("utf-8"))

    def _write_message(self, payload: dict[str, Any]) -> None:
        """Write one MCP-framed JSON-RPC message to stdout."""
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        sys.stdout.buffer.write(header)
        sys.stdout.buffer.write(body)
        sys.stdout.buffer.flush()

    def _request_client_sampling(self, context: dict[str, str]) -> dict[str, Any]:
        """Request client sampling synchronously when supported."""
        request_id = self._next_server_request_id
        self._next_server_request_id += 1
        sampling_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "sampling/createMessage",
            "params": {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                "Create a valid .metagit.yml from this context. "
                                "Output YAML only.\n"
                                f"{context}"
                            ),
                        },
                    }
                ],
                "maxTokens": 1400,
            },
        }
        self._write_message(sampling_request)

        while True:
            inbound = self._read_message()
            if inbound is None:
                return {}

            if inbound.get("id") == request_id:
                if "result" in inbound:
                    return inbound["result"]
                return {}

            # Handle regular inbound requests while waiting on sampling response.
            response = self._handle_request(request=inbound)
            if response is not None:
                self._write_message(response)

    def _extract_sampling_text(self, sampling_result: dict[str, Any]) -> Optional[str]:
        """Extract sampled text from sampling/createMessage result."""
        content = sampling_result.get("content")
        if isinstance(content, dict):
            if content.get("type") == "text":
                return content.get("text")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    return item.get("text")
        return None
