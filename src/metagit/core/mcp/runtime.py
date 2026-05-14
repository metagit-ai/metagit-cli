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
from metagit.core.mcp.services.repo_ops import RepoOperationsService
from metagit.core.mcp.services.upstream_hints import UpstreamHintService
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.mcp.services.workspace_search import WorkspaceSearchService
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
        self._managed_repo_search = ManagedRepoSearchService()
        self._hints_service = UpstreamHintService()
        self._repo_ops = RepoOperationsService()
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
                    "tags": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
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
        payload = self._resources.get_resource(
            uri=uri, config=config, repos_status=repos
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
            repo_paths = [row["repo_path"] for row in repos if row.get("exists")]
            query = str(arguments.get("query", "")).strip()
            if not query:
                raise InvalidToolArgumentsError("query is required")
            return {
                "hits": self._search_service.search(
                    query=query,
                    repo_paths=repo_paths,
                    preset=arguments.get("preset"),
                    max_results=int(arguments.get("max_results", 25)),
                )
            }

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
            result = self._managed_repo_search.search(
                config=config,
                workspace_root=status.root_path,
                query=query,
                project=arguments.get("project"),
                exact=bool(arguments.get("exact", False)),
                synced_only=bool(arguments.get("synced_only", False)),
                tags=tag_filter,
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
