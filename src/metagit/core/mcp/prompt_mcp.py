#!/usr/bin/env python
"""
MCP prompts/list and prompts/get handlers mirroring layered prompt resources.
"""

from __future__ import annotations

from typing import Any

from metagit.core.config.models import MetagitConfig
from metagit.core.prompt.models import PromptKind, PromptScope
from metagit.core.prompt.service import PromptService, PromptServiceError


def _prompt_arguments(scope: PromptScope) -> list[dict[str, Any]]:
    args: list[dict[str, Any]] = [
        {
            "name": "instructions",
            "description": "Include composed manifest instructions (1) or template only (0).",
            "required": False,
        },
    ]
    if scope in {"project", "repo"}:
        args.insert(
            0,
            {
                "name": "project",
                "description": "Workspace project name.",
                "required": True,
            },
        )
    if scope == "repo":
        args.insert(
            1,
            {
                "name": "repo",
                "description": "Repository name within the project.",
                "required": True,
            },
        )
    return args


def list_mcp_prompts(*, active: bool) -> dict[str, Any]:
    """Return MCP prompts/list payload."""
    if not active:
        return {"prompts": []}
    rows: list[dict[str, Any]] = []
    for entry in PromptService().list_entries():
        for scope in entry.scopes:
            rows.append(
                {
                    "name": f"{scope}/{entry.kind}",
                    "description": entry.description,
                    "arguments": _prompt_arguments(scope),
                }
            )
    return {"prompts": rows}


def parse_prompt_name(name: str) -> tuple[PromptScope, PromptKind]:
    """Split MCP prompt name ``scope/kind``."""
    parts = name.strip().split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"invalid prompt name {name!r}; expected scope/kind")
    scope_raw, kind_raw = parts[0], parts[1]
    return scope_raw, kind_raw  # type: ignore[return-value]


def get_mcp_prompt(
    *,
    config: MetagitConfig,
    name: str,
    arguments: dict[str, Any] | None,
    config_path: str,
    workspace_root: str,
    workspace_dedupe: Any = None,
) -> dict[str, Any]:
    """Return MCP prompts/get payload for one prompt."""
    scope, kind = parse_prompt_name(name)
    args = arguments or {}
    include_raw = args.get("instructions", "1")
    include_instructions = str(include_raw).strip().lower() not in {"0", "false", "no", "off"}
    project_name = args.get("project")
    repo_name = args.get("repo")
    project_name = project_name.strip() or None if isinstance(project_name, str) else None
    repo_name = repo_name.strip() or None if isinstance(repo_name, str) else None
    try:
        emitted = PromptService().emit(
            config,
            kind=kind,
            scope=scope,
            definition_path=config_path,
            workspace_root=workspace_root,
            project_name=project_name,
            repo_name=repo_name,
            include_instructions=include_instructions,
            workspace_dedupe=workspace_dedupe,
        )
    except PromptServiceError as exc:
        raise ValueError(str(exc)) from exc
    resource_uri = f"metagit://prompt/{scope}/{kind}"
    query_parts: list[str] = []
    if project_name:
        query_parts.append(f"project={project_name}")
    if repo_name:
        query_parts.append(f"repo={repo_name}")
    if not include_instructions:
        query_parts.append("instructions=0")
    if query_parts:
        resource_uri = f"{resource_uri}?{'&'.join(query_parts)}"
    return {
        "description": f"Metagit prompt {scope}/{kind}",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": emitted.text,
                },
            }
        ],
        "_meta": {
            "resource_uri": resource_uri,
            "prompt_kind": kind,
            "prompt_scope": scope,
        },
    }


__all__ = ["get_mcp_prompt", "list_mcp_prompts", "parse_prompt_name"]
