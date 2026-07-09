#!/usr/bin/env python
"""
Minimal MCP stdio runtime for Metagit tools and resources.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Literal, Optional, cast

from metagit.core.agent.service import AgentService
from metagit.core.appconfig import AppConfig
from metagit.core.config.graph_cypher_export import GraphCypherExportService
from metagit.core.config.graph_suggest import GraphRelationshipSuggestService
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.context.approval_service import ApprovalService
from metagit.core.context.compiler import ContextCompiler
from metagit.core.context.context_pack_service import ContextPackService
from metagit.core.context.handoff_service import HandoffService
from metagit.core.context.models import ApprovalStatus
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.context.repo_card_service import RepoCardService
from metagit.core.context.session_begin_service import SessionBeginService
from metagit.core.context.session_digest_service import SessionDigestService
from metagit.core.coordination.branch_service import BranchService
from metagit.core.coordination.claim_service import ClaimService
from metagit.core.coordination.lease_service import LeaseService
from metagit.core.coordination.models import ClaimCheckResult
from metagit.core.coordination.worktree_service import WorktreeService
from metagit.core.gitnexus.group_sync import GitNexusGroupSyncService
from metagit.core.mcp.gate import WorkspaceGate
from metagit.core.mcp.models import McpActivationState, WorkspaceStatus
from metagit.core.mcp.prompt_mcp import get_mcp_prompt, list_mcp_prompts
from metagit.core.mcp.resource_catalog import list_static_descriptors
from metagit.core.mcp.resource_service import ResourceContext
from metagit.core.mcp.resources import ResourcePublisher
from metagit.core.mcp.root_resolver import WorkspaceRootResolver
from metagit.core.mcp.services.bootstrap_sampling import BootstrapSamplingService
from metagit.core.mcp.services.cross_project_dependencies import (
    CrossProjectDependencyService,
)
from metagit.core.mcp.services.discovery_context import DiscoveryContextService
from metagit.core.mcp.services.ops_log import OperationsLogService
from metagit.core.mcp.services.project_context import ProjectContextService
from metagit.core.mcp.services.repo_ops import RepoOperationsService
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.mcp.services.source_sync import run_mcp_source_sync
from metagit.core.mcp.services.upstream_hints import UpstreamHintService
from metagit.core.mcp.services.workspace_health import WorkspaceHealthService
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.mcp.services.workspace_search import WorkspaceSearchService
from metagit.core.mcp.services.workspace_semantic_search import (
    WorkspaceSemanticSearchService,
)
from metagit.core.mcp.services.workspace_snapshot import WorkspaceSnapshotService
from metagit.core.mcp.services.workspace_sync import WorkspaceSyncService
from metagit.core.mcp.services.workspace_template import WorkspaceTemplateService
from metagit.core.mcp.tool_registry import ToolRegistry
from metagit.core.mcp.tools.bootstrap_plan_only import (
    metagit_bootstrap_config_plan_only,
)
from metagit.core.mcp.tools.workspace_status import metagit_workspace_status
from metagit.core.project.search_service import ManagedRepoSearchService
from metagit.core.release.release_check_service import ReleaseCheckService
from metagit.core.release.upgrade_service import VersionUpgradeService
from metagit.core.semantic.service import SemanticGraphService
from metagit.core.state.resolver import resolve_backend
from metagit.core.taskgraph.service import TaskGraphService
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.workspace.catalog_models import CatalogError
from metagit.core.workspace.catalog_service import WorkspaceCatalogService
from metagit.core.workspace.layout_context import resolve_sync_context
from metagit.core.workspace.layout_service import WorkspaceLayoutService
from metagit.core.workspace.root_resolver import resolve_sync_root


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
        self._graph_cypher_export = GraphCypherExportService()
        self._graph_suggest = GraphRelationshipSuggestService()
        self._gitnexus_group_sync = GitNexusGroupSyncService()
        self._workspace_health = WorkspaceHealthService()
        self._context_pack = ContextPackService()
        self._session_begin = SessionBeginService()
        self._repo_card = RepoCardService()
        self._workspace_catalog = WorkspaceCatalogService()
        self._workspace_layout = WorkspaceLayoutService()
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
            "metagit_workspace_grep_info": {"type": "object", "properties": {}},
            "metagit_version_check": {
                "type": "object",
                "properties": {
                    "include_notes": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_version_upgrade": {
                "type": "object",
                "properties": {
                    "apply": {"type": "boolean"},
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
                                "manual",
                            ],
                        },
                    },
                    "depth": {"type": "integer", "minimum": 1},
                    "include_external_repos": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_export_workspace_graph_cypher": {
                "type": "object",
                "properties": {
                    "gitnexus_repo": {"type": "string"},
                    "include_structure": {"type": "boolean"},
                    "include_documentation": {"type": "boolean"},
                    "manual_only": {"type": "boolean"},
                    "with_schema": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_suggest_graph_relationships": {
                "type": "object",
                "properties": {
                    "dependency_types": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "depth": {"type": "integer", "minimum": 1},
                    "min_confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "all"],
                    },
                    "include_declared": {"type": "boolean"},
                    "candidate_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "additionalProperties": False,
            },
            "metagit_apply_graph_relationships": {
                "type": "object",
                "properties": {
                    "dependency_types": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "depth": {"type": "integer", "minimum": 1},
                    "min_confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "all"],
                    },
                    "include_declared": {"type": "boolean"},
                    "candidate_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "dry_run": {"type": "boolean"},
                    "save": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_gitnexus_group_sync": {
                "type": "object",
                "properties": {
                    "group_name": {"type": "string"},
                    "create_group": {"type": "boolean"},
                    "prune": {"type": "boolean"},
                    "run_contract_sync": {"type": "boolean"},
                    "allow_stale": {"type": "boolean"},
                    "skip_embeddings": {"type": "boolean"},
                    "exact_only": {"type": "boolean"},
                    "verbose": {"type": "boolean"},
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
            "metagit_context_pack": {
                "type": "object",
                "required": ["tier"],
                "properties": {
                    "tier": {"type": "integer", "enum": [0, 1, 2]},
                    "project_name": {"type": "string"},
                    "repo_name": {"type": "string"},
                    "max_tokens": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
            "metagit_context_compile": {
                "type": "object",
                "required": ["project_name", "repo_name"],
                "properties": {
                    "project_name": {"type": "string"},
                    "repo_name": {"type": "string"},
                    "tier": {"type": "integer", "enum": [0, 1, 2]},
                    "budget": {"type": "integer", "minimum": 1},
                    "profile": {"type": "string"},
                    "task_id": {"type": "string"},
                    "graph_id": {"type": "string"},
                    "objective_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_session_begin": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "repo_name": {"type": "string"},
                    "max_tokens": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
            "metagit_session_digest": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "metagit_objective_list": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "metagit_objective_upsert": {
                "type": "object",
                "required": ["id", "title"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": [
                            "pending",
                            "in_progress",
                            "done",
                            "cancelled",
                        ],
                    },
                    "repos": {"type": "array", "items": {"type": "string"}},
                    "acceptance": {"type": "string"},
                    "human_notes": {"type": "string"},
                    "agent_notes": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_objective_edit": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": [
                            "pending",
                            "in_progress",
                            "done",
                            "cancelled",
                        ],
                    },
                    "repos": {"type": "array", "items": {"type": "string"}},
                    "acceptance": {"type": "string"},
                    "human_notes": {"type": "string"},
                    "agent_notes": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_approval_request": {
                "type": "object",
                "required": ["action", "payload"],
                "properties": {
                    "action": {"type": "string"},
                    "payload": {"type": "object"},
                    "requested_by": {"type": "string"},
                    "idempotency_key": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_approval_list": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "pending",
                            "approved",
                            "denied",
                            "all",
                        ],
                    },
                },
                "additionalProperties": False,
            },
            "metagit_approval_resolve": {
                "type": "object",
                "required": ["approval_id", "decision"],
                "properties": {
                    "approval_id": {"type": "string"},
                    "decision": {
                        "type": "string",
                        "enum": ["approved", "denied"],
                    },
                    "note": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_handoff_list": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["open", "claimed", "completed", "cancelled"],
                    },
                },
                "additionalProperties": False,
            },
            "metagit_handoff_create": {
                "type": "object",
                "required": ["title"],
                "properties": {
                    "title": {"type": "string"},
                    "created_by": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "additionalProperties": False,
            },
            "metagit_handoff_claim": {
                "type": "object",
                "required": ["id", "claimed_by"],
                "properties": {
                    "id": {"type": "string"},
                    "claimed_by": {"type": "string"},
                    "note": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_handoff_complete": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "actor": {"type": "string"},
                    "note": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_events": {
                "type": "object",
                "properties": {
                    "since": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_branch_allocate": {
                "type": "object",
                "required": ["repository", "agent_id", "task_id"],
                "properties": {
                    "repository": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "task_id": {"type": "string"},
                    "description": {"type": "string"},
                    "branch_name": {"type": "string"},
                    "base": {"type": "string"},
                    "integration_branch": {"type": "string"},
                    "create_git_branch": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_branch_list": {
                "type": "object",
                "properties": {
                    "repository": {"type": "string"},
                    "status": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_branch_release": {
                "type": "object",
                "properties": {
                    "branch_id": {"type": "string"},
                    "name": {"type": "string"},
                    "repository": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_lease_acquire": {
                "type": "object",
                "required": ["repository", "agent_id", "task_id"],
                "properties": {
                    "repository": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "task_id": {"type": "string"},
                    "branch": {"type": "string"},
                    "branch_id": {"type": "string"},
                    "ttl": {"type": "string"},
                    "allocate": {"type": "boolean"},
                    "description": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_lease_renew": {
                "type": "object",
                "required": ["lease_id", "agent_id"],
                "properties": {
                    "lease_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "ttl": {"type": "string"},
                    "force": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_lease_release": {
                "type": "object",
                "required": ["lease_id", "agent_id"],
                "properties": {
                    "lease_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "force": {"type": "boolean"},
                    "release_branch": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_lease_list": {
                "type": "object",
                "properties": {
                    "repository": {"type": "string"},
                    "status": {"type": "string"},
                    "agent_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_worktree_create": {
                "type": "object",
                "required": ["repository", "agent_id", "task_id", "branch"],
                "properties": {
                    "repository": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "task_id": {"type": "string"},
                    "branch": {"type": "string"},
                    "lease_id": {"type": "string"},
                    "integration_branch": {"type": "string"},
                    "claims": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False,
            },
            "metagit_worktree_destroy": {
                "type": "object",
                "properties": {
                    "worktree_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "repository": {"type": "string"},
                    "force": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_worktree_status": {
                "type": "object",
                "properties": {
                    "worktree_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_worktree_list": {
                "type": "object",
                "properties": {
                    "repository": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "status": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_claim_declare": {
                "type": "object",
                "required": ["repository", "agent_id", "patterns"],
                "properties": {
                    "repository": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "patterns": {"type": "array", "items": {"type": "string"}},
                    "task_id": {"type": "string"},
                    "strict": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_claim_check": {
                "type": "object",
                "required": ["repository", "patterns"],
                "properties": {
                    "repository": {"type": "string"},
                    "patterns": {"type": "array", "items": {"type": "string"}},
                    "agent_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_claim_list": {
                "type": "object",
                "properties": {
                    "repository": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "status": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_claim_release": {
                "type": "object",
                "required": ["claim_id", "agent_id"],
                "properties": {
                    "claim_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "force": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_semantic_declare": {
                "type": "object",
                "required": ["concept", "repository", "patterns"],
                "properties": {
                    "concept": {"type": "string"},
                    "repository": {"type": "string"},
                    "patterns": {"type": "array", "items": {"type": "string"}},
                    "symbol_hints": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False,
            },
            "metagit_semantic_query": {
                "type": "object",
                "required": ["concept"],
                "properties": {
                    "concept": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_semantic_owners": {
                "type": "object",
                "required": ["repository", "path"],
                "properties": {
                    "repository": {"type": "string"},
                    "path": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_semantic_conflicts": {
                "type": "object",
                "required": ["repository"],
                "properties": {
                    "repository": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_semantic_ingest": {
                "type": "object",
                "properties": {
                    "project": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_task_create": {
                "type": "object",
                "required": ["title", "goal"],
                "properties": {
                    "title": {"type": "string"},
                    "goal": {"type": "string"},
                    "acceptance": {"type": "array", "items": {"type": "string"}},
                    "objective_id": {"type": "string"},
                    "handoff_id": {"type": "string"},
                    "project": {"type": "string"},
                    "repos": {"type": "array", "items": {"type": "string"}},
                    "graph_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_task_expand": {
                "type": "object",
                "required": ["graph_id", "outline"],
                "properties": {
                    "graph_id": {"type": "string"},
                    "outline": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "object"}},
                        ]
                    },
                },
                "additionalProperties": False,
            },
            "metagit_task_list": {
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "status": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_task_status": {
                "type": "object",
                "required": ["node_id"],
                "properties": {
                    "node_id": {"type": "string"},
                    "graph_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_task_ready": {
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_task_block": {
                "type": "object",
                "required": ["node_id", "reason"],
                "properties": {
                    "node_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "graph_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_task_complete": {
                "type": "object",
                "required": ["node_id"],
                "properties": {
                    "node_id": {"type": "string"},
                    "graph_id": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_task_bind_acl": {
                "type": "object",
                "required": ["node_id", "agent_id"],
                "properties": {
                    "node_id": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "graph_id": {"type": "string"},
                    "branch": {"type": "string"},
                    "lease_id": {"type": "string"},
                    "worktree_id": {"type": "string"},
                    "pattern": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_repo_card": {
                "type": "object",
                "required": ["project_name", "repo_name"],
                "properties": {
                    "project_name": {"type": "string"},
                    "repo_name": {"type": "string"},
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
            "metagit_workspace_list": {"type": "object", "properties": {}},
            "metagit_workspace_projects_list": {"type": "object", "properties": {}},
            "metagit_workspace_project_add": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "agent_instructions": {"type": "string"},
                    "ensure": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_workspace_project_remove": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "force": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_workspace_repos_list": {
                "type": "object",
                "properties": {"project_name": {"type": "string"}},
                "additionalProperties": False,
            },
            "metagit_workspace_repo_add": {
                "type": "object",
                "required": ["project_name", "name"],
                "properties": {
                    "project_name": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "path": {"type": "string"},
                    "url": {"type": "string"},
                    "sync": {"type": "boolean"},
                    "agent_instructions": {"type": "string"},
                    "ensure": {"type": "boolean"},
                    "force": {"type": "boolean"},
                    "protected": {"type": "boolean"},
                    "tags": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "additionalProperties": False,
            },
            "metagit_workspace_repo_remove": {
                "type": "object",
                "required": ["project_name", "name"],
                "properties": {
                    "project_name": {"type": "string"},
                    "name": {"type": "string"},
                    "force": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_project_source_sync": {
                "type": "object",
                "required": ["project_name", "provider"],
                "properties": {
                    "project_name": {"type": "string"},
                    "provider": {"type": "string", "enum": ["github", "gitlab"]},
                    "org": {"type": "string"},
                    "user": {"type": "string"},
                    "group": {"type": "string"},
                    "mode": {
                        "type": "string",
                        "enum": ["discover", "additive", "reconcile"],
                    },
                    "recursive": {"type": "boolean"},
                    "include_archived": {"type": "boolean"},
                    "include_forks": {"type": "boolean"},
                    "path_prefix": {"type": "string"},
                    "include_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "ignore_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "name_strategy": {
                        "type": "string",
                        "enum": ["short", "namespaced"],
                    },
                    "ensure": {"type": "boolean"},
                    "refresh_metadata": {"type": "boolean"},
                    "enrich_topics": {"type": "boolean"},
                    "apply": {"type": "boolean"},
                    "confirm": {"type": "boolean"},
                    "sync": {"type": "boolean"},
                    "from_manifest": {"type": "boolean"},
                    "source_id": {"type": "string"},
                    "force": {"type": "boolean"},
                    "requested_by": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "metagit_workspace_project_rename": {
                "type": "object",
                "required": ["from_name", "to_name"],
                "properties": {
                    "from_name": {"type": "string"},
                    "to_name": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                    "move_disk": {"type": "boolean"},
                    "update_sessions": {"type": "boolean"},
                    "force": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_workspace_repo_rename": {
                "type": "object",
                "required": ["project_name", "from_name", "to_name"],
                "properties": {
                    "project_name": {"type": "string"},
                    "from_name": {"type": "string"},
                    "to_name": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                    "move_disk": {"type": "boolean"},
                    "force": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_workspace_repo_move": {
                "type": "object",
                "required": ["repo_name", "from_project", "to_project"],
                "properties": {
                    "repo_name": {"type": "string"},
                    "from_project": {"type": "string"},
                    "to_project": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                    "move_disk": {"type": "boolean"},
                    "force": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "metagit_agent_catalog": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "metagit_agent_dispatch_plan": {
                "type": "object",
                "required": ["template_id"],
                "properties": {
                    "template_id": {"type": "string"},
                    "vendor": {"type": "string"},
                    "scope": {
                        "type": "string",
                        "enum": ["project", "user"],
                    },
                    "project_name": {"type": "string"},
                    "repo_name": {"type": "string"},
                    "task": {"type": "string"},
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
            elif method == "prompts/list":
                result = self._handle_prompts_list()
            elif method == "prompts/get":
                result = self._handle_prompts_get(params=params)
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
                "resources": {"subscribe": False, "listChanged": True},
                "prompts": {"listChanged": False},
            },
        }

    def _handle_prompts_list(self) -> dict[str, Any]:
        status, _ = self._resolve_status_and_config()
        active = status.state == McpActivationState.ACTIVE
        return list_mcp_prompts(active=active)

    def _handle_prompts_get(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if not name or not isinstance(name, str):
            raise ValueError("name is required")
        status, config = self._resolve_status_and_config()
        if status.state != McpActivationState.ACTIVE or config is None or not status.root_path:
            raise ValueError("prompts/get requires an active workspace gate")
        context = self._build_resource_context(
            status=status,
            config=config,
            repos=[],
            health_payload=None,
        )
        arguments = params.get("arguments")
        args = arguments if isinstance(arguments, dict) else {}
        return get_mcp_prompt(
            config=config,
            name=name,
            arguments=args,
            config_path=context.config_path,
            workspace_root=context.workspace_root,
            workspace_dedupe=context.workspace_dedupe,
        )

    def _handle_tools_list(self) -> dict[str, Any]:
        status, _ = self._resolve_status_and_config()
        tool_names = self._registry.list_tools(status=status)
        tools: list[dict[str, Any]] = []
        for name in tool_names:
            tools.append(
                {
                    "name": name,
                    "description": f"Metagit MCP tool: {name}",
                    "inputSchema": self._tool_schemas.get(name, {"type": "object", "properties": {}}),
                }
            )
        return {"tools": tools}

    def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        arguments = params.get("arguments", {}) or {}
        status, config = self._resolve_status_and_config()
        allowed = set(self._registry.list_tools(status=status))
        if name not in allowed:
            raise InvalidToolArgumentsError(f"Tool not available in current state: {name}")

        result = self._dispatch_tool(
            name=name,
            arguments=arguments,
            status=status,
            config=config,
        )
        self._ops_log.append(action="tool_call", detail=name)
        if isinstance(result, dict) and "schema_version" not in result:
            result = {"schema_version": "1.0", **result}
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    def _handle_resources_list(self) -> dict[str, Any]:
        status, _ = self._resolve_status_and_config()
        resources = [
            {
                "uri": item.uri,
                "name": item.name,
                "description": item.description,
                "mimeType": item.mime_type,
            }
            for item in list_static_descriptors(gate_state=status.state)
        ]
        return {"resources": resources}

    def _build_resource_context(
        self,
        status: WorkspaceStatus,
        config: Any,
        repos: list[dict[str, Any]],
        health_payload: dict[str, Any] | None,
    ) -> ResourceContext:
        definition_root = status.root_path or ""
        config_path = str(Path(definition_root) / ".metagit.yml") if definition_root else ""
        app_config = AppConfig.load()
        sync_root = (
            resolve_sync_root(definition_root, app_config.workspace.path)
            if definition_root and not isinstance(app_config, Exception)
            else definition_root
        )
        workspace_dedupe = None if isinstance(app_config, Exception) else app_config.workspace.dedupe
        return ResourceContext(
            status=status,
            config=config,
            config_path=config_path,
            workspace_root=sync_root or definition_root,
            session_root=definition_root,
            definition_root=definition_root,
            repos_status=repos,
            health_payload=health_payload,
            workspace_dedupe=workspace_dedupe,
        )

    def _handle_resources_read(self, params: dict[str, Any]) -> dict[str, Any]:
        uri = params.get("uri")
        if not uri:
            raise ValueError("uri is required")
        status, config = self._resolve_status_and_config()
        repos = self._build_repo_index(status=status, config=config)
        health_payload = None
        if config and status.root_path:
            parsed = str(uri)
            if parsed.startswith("metagit://workspace/health"):
                health_payload = self._workspace_health.check(
                    config=config,
                    workspace_root=status.root_path,
                ).model_dump(mode="json")
        context = self._build_resource_context(
            status=status,
            config=config,
            repos=repos,
            health_payload=health_payload,
        )
        mime_type, text = self._resources.read_resource(uri=str(uri), context=context)
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": mime_type,
                    "text": text,
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
            repo_selectors = [str(item) for item in raw_repos] if isinstance(raw_repos, list) else None
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
                    paths=[str(item) for item in raw_paths] if isinstance(raw_paths, list) else None,
                    exclude=[str(item) for item in raw_exclude] if isinstance(raw_exclude, list) else None,
                    context_lines=int(arguments.get("context_lines", 0)),
                    include_paths=bool(arguments.get("include_paths", False)),
                    intent=arguments.get("intent"),
                )
            }

        if name == "metagit_workspace_grep_info":
            return WorkspaceSearchService.ripgrep_status()

        if name == "metagit_version_check":
            include_notes = bool(arguments.get("include_notes", True))
            result = ReleaseCheckService().check(include_notes=include_notes)
            return result.model_dump(mode="json")

        if name == "metagit_version_upgrade":
            apply = bool(arguments.get("apply", False))
            result = VersionUpgradeService().upgrade(apply=apply)
            return result.model_dump(mode="json")

        if name == "metagit_workspace_semantic_search":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("semantic workspace search requires an active workspace")
            repos = self._build_repo_index(status=status, config=config)
            raw_sem_repos = arguments.get("repos")
            sem_selectors = [str(item) for item in raw_sem_repos] if isinstance(raw_sem_repos, list) else None
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
                raise InvalidToolArgumentsError("managed repo search requires an active workspace")
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
            status_filter = [str(item) for item in raw_status] if isinstance(raw_status, list) else None
            sort_val = str(arguments.get("sort", "score"))
            if sort_val not in {"score", "project", "name"}:
                raise InvalidToolArgumentsError("sort must be score, project, or name")
            has_url = arguments.get("has_url")
            has_url_val = bool(has_url) if isinstance(has_url, bool) else None
            sync_enabled = arguments.get("sync_enabled")
            sync_enabled_val = bool(sync_enabled) if isinstance(sync_enabled, bool) else None
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
            return {"hints": self._hints_service.rank(blocker=blocker, repo_context=repos)}

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
                raise InvalidToolArgumentsError("workspace sync requires an active workspace")
            repos = self._build_repo_index(status=status, config=config)
            raw_repos = arguments.get("repos")
            repo_selectors = [str(item) for item in raw_repos] if isinstance(raw_repos, list) else ["all"]
            only_if = str(arguments.get("only_if", "any"))
            if only_if not in {"any", "missing", "dirty", "behind_origin"}:
                raise InvalidToolArgumentsError("only_if must be any, missing, dirty, or behind_origin")
            max_parallel_raw = arguments.get("max_parallel", 4)
            try:
                max_parallel = int(max_parallel_raw)
            except (TypeError, ValueError) as exc:
                raise InvalidToolArgumentsError("max_parallel must be an integer") from exc
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
                raise InvalidToolArgumentsError("project context requires an active workspace")
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
                raise InvalidToolArgumentsError("workspace snapshot requires an active workspace")
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
                raise InvalidToolArgumentsError("workspace snapshot restore requires an active workspace")
            snapshot_id = str(arguments.get("snapshot_id", "")).strip()
            if not snapshot_id:
                raise InvalidToolArgumentsError("snapshot_id is required")
            return self._workspace_snapshot.restore(
                config=config,
                workspace_root=status.root_path,
                snapshot_id=snapshot_id,
                switch_project=bool(arguments.get("switch_project", True)),
                restore_session=bool(arguments.get("restore_session", True)),
            ).model_dump(mode="json")

        if name == "metagit_workspace_health_check":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("workspace health check requires an active workspace")
            raw_warn = arguments.get("branch_head_warning_days")
            raw_crit = arguments.get("branch_head_critical_days")
            raw_integration = arguments.get("integration_stale_days")
            try:
                branch_warn = float(raw_warn) if raw_warn is not None else 180.0
                branch_crit = float(raw_crit) if raw_crit is not None else 365.0
                integration_td = float(raw_integration) if raw_integration is not None else 90.0
            except (TypeError, ValueError) as exc:
                raise InvalidToolArgumentsError("branch age thresholds must be numbers") from exc
            if branch_warn < 0 or branch_crit < 0 or integration_td < 0:
                raise InvalidToolArgumentsError("branch age thresholds must be non-negative")
            loaded_app = AppConfig.load()
            dedupe_cfg = loaded_app.workspace.dedupe if not isinstance(loaded_app, Exception) else None
            return self._workspace_health.check(
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
                dedupe=dedupe_cfg,
            ).model_dump(mode="json")

        if name == "metagit_context_pack":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("context pack requires an active workspace")
            if "tier" not in arguments:
                raise InvalidToolArgumentsError("tier is required")
            tier_raw = arguments.get("tier")
            try:
                tier_val = int(tier_raw)
            except (TypeError, ValueError) as exc:
                raise InvalidToolArgumentsError(
                    "tier must be an integer",
                ) from exc
            if tier_val not in (0, 1, 2):
                raise InvalidToolArgumentsError("tier must be 0, 1, or 2")
            project_raw = arguments.get("project_name")
            repo_raw = arguments.get("repo_name")
            project_opt = str(project_raw).strip() if isinstance(project_raw, str) and project_raw.strip() else None
            repo_opt = str(repo_raw).strip() if isinstance(repo_raw, str) and repo_raw.strip() else None
            max_tokens_raw = arguments.get("max_tokens")
            max_tokens: int | None = None
            if max_tokens_raw is not None:
                try:
                    max_tokens = int(max_tokens_raw)
                except (TypeError, ValueError) as exc:
                    raise InvalidToolArgumentsError(
                        "max_tokens must be an integer",
                    ) from exc
                if max_tokens < 1:
                    raise InvalidToolArgumentsError(
                        "max_tokens must be >= 1",
                    )
            config_path = str(Path(status.root_path) / ".metagit.yml")
            tier_literal = cast(Literal[0, 1, 2], tier_val)
            definition_root = status.root_path
            app_config = AppConfig.load()
            sync_root = (
                resolve_sync_root(definition_root, app_config.workspace.path)
                if not isinstance(app_config, Exception)
                else definition_root
            )
            pack = self._context_pack.pack(
                config=config,
                config_path=config_path,
                workspace_root=sync_root,
                session_root=definition_root,
                definition_root=definition_root,
                tier=tier_literal,
                project_name=project_opt,
                repo_name=repo_opt,
                max_tokens=max_tokens,
            )
            return pack.model_dump(mode="json")

        if name == "metagit_context_compile":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("context compile requires an active workspace")
            project_name = str(arguments.get("project_name", "")).strip()
            repo_name = str(arguments.get("repo_name", "")).strip()
            if not project_name:
                raise InvalidToolArgumentsError("project_name is required")
            if not repo_name:
                raise InvalidToolArgumentsError("repo_name is required")
            tier_raw = arguments.get("tier", 1)
            try:
                tier_val = int(tier_raw)
            except (TypeError, ValueError) as exc:
                raise InvalidToolArgumentsError("tier must be an integer") from exc
            if tier_val not in (0, 1, 2):
                raise InvalidToolArgumentsError("tier must be 0, 1, or 2")
            budget_raw = arguments.get("budget")
            budget: int | None = None
            if budget_raw is not None:
                try:
                    budget = int(budget_raw)
                except (TypeError, ValueError) as exc:
                    raise InvalidToolArgumentsError("budget must be an integer") from exc
                if budget < 1:
                    raise InvalidToolArgumentsError("budget must be >= 1")
            config_path = str(Path(status.root_path) / ".metagit.yml")
            definition_root = status.root_path
            app_config = AppConfig.load()
            sync_root = (
                resolve_sync_root(definition_root, app_config.workspace.path)
                if not isinstance(app_config, Exception)
                else definition_root
            )
            compiled = ContextCompiler(pack_service=self._context_pack).compile(
                config=config,
                config_path=config_path,
                workspace_root=sync_root,
                session_root=definition_root,
                definition_root=definition_root,
                project=project_name,
                repo=repo_name,
                tier=cast(Literal[0, 1, 2], tier_val),
                budget=budget,
                profile=arguments.get("profile") if isinstance(arguments.get("profile"), str) else None,
                task_id=arguments.get("task_id") if isinstance(arguments.get("task_id"), str) else None,
                graph_id=arguments.get("graph_id") if isinstance(arguments.get("graph_id"), str) else None,
                objective_id=arguments.get("objective_id") if isinstance(arguments.get("objective_id"), str) else None,
            )
            if isinstance(compiled, Exception):
                raise InvalidToolArgumentsError(str(compiled)) from compiled
            return compiled.model_dump(mode="json")

        if name == "metagit_session_begin":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("session begin requires an active workspace")
            project_raw = arguments.get("project_name")
            repo_raw = arguments.get("repo_name")
            project_opt = str(project_raw).strip() if isinstance(project_raw, str) and project_raw.strip() else None
            repo_opt = str(repo_raw).strip() if isinstance(repo_raw, str) and repo_raw.strip() else None
            max_tokens_raw = arguments.get("max_tokens")
            max_tokens: int | None = None
            if max_tokens_raw is not None:
                try:
                    max_tokens = int(max_tokens_raw)
                except (TypeError, ValueError) as exc:
                    raise InvalidToolArgumentsError(
                        "max_tokens must be an integer",
                    ) from exc
                if max_tokens < 1:
                    raise InvalidToolArgumentsError(
                        "max_tokens must be >= 1",
                    )

            config_path = str(Path(status.root_path) / ".metagit.yml")
            definition_root = status.root_path
            app_config = AppConfig.load()
            sync_root = (
                resolve_sync_root(definition_root, app_config.workspace.path)
                if not isinstance(app_config, Exception)
                else definition_root
            )
            envelope = self._session_begin.begin(
                config=config,
                config_path=config_path,
                workspace_root=sync_root,
                session_root=definition_root,
                definition_root=definition_root,
                project_name=project_opt,
                repo_name=repo_opt,
                max_tokens=max_tokens,
            )
            return envelope.model_dump(mode="json")

        if name == "metagit_session_digest":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("session digest requires an active workspace")
            config_path = str(Path(status.root_path) / ".metagit.yml")
            definition_root = status.root_path
            app_config = AppConfig.load()
            sync_root = (
                resolve_sync_root(definition_root, app_config.workspace.path)
                if not isinstance(app_config, Exception)
                else definition_root
            )
            objectives = ObjectiveService(workspace_root=definition_root).list().objectives
            active_objective_id = next(
                (objective.id for objective in objectives if objective.status == "in_progress"),
                None,
            )
            session_store = SessionStore(workspace_root=definition_root)
            digest = SessionDigestService.build(
                config=config,
                config_path=config_path,
                workspace_root=sync_root,
                since=session_store.get_last_session_at(),
                active_objective_id=active_objective_id,
                definition_root=definition_root,
            )
            return digest.model_dump(mode="json")

        if name == "metagit_objective_list":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "objective list requires an active workspace",
                )
            svc = ObjectiveService(workspace_root=status.root_path)
            return svc.list().model_dump(mode="json")

        if name == "metagit_objective_upsert":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "objective upsert requires an active workspace",
                )
            obj_id = str(arguments.get("id", "")).strip()
            if not obj_id:
                raise InvalidToolArgumentsError("id is required")
            partial: dict[str, Any] = {"id": obj_id}
            title_raw = arguments.get("title")
            if isinstance(title_raw, str) and title_raw.strip():
                partial["title"] = title_raw.strip()
            status_raw = arguments.get("status")
            if status_raw is not None:
                sv = str(status_raw).strip()
                if sv not in (
                    "pending",
                    "in_progress",
                    "done",
                    "cancelled",
                ):
                    raise InvalidToolArgumentsError("invalid objective status")
                partial["status"] = sv
            raw_repos = arguments.get("repos")
            if isinstance(raw_repos, list):
                partial["repos"] = [str(r) for r in raw_repos]
            for field in ("acceptance", "human_notes", "agent_notes", "notes"):
                raw_val = arguments.get(field)
                if isinstance(raw_val, str) and raw_val.strip():
                    partial[field] = raw_val.strip()
            svc = ObjectiveService(workspace_root=status.root_path)
            try:
                saved = svc.upsert_partial(partial)
            except ValueError as exc:
                raise InvalidToolArgumentsError(str(exc)) from exc
            return saved.model_dump(mode="json")

        if name == "metagit_objective_edit":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "objective edit requires an active workspace",
                )
            obj_id = str(arguments.get("id", "")).strip()
            if not obj_id:
                raise InvalidToolArgumentsError("id is required")
            updates: dict[str, Any] = {}
            title_raw = arguments.get("title")
            if isinstance(title_raw, str):
                updates["title"] = title_raw
            status_raw = arguments.get("status")
            if status_raw is not None:
                sv = str(status_raw).strip()
                if sv not in (
                    "pending",
                    "in_progress",
                    "done",
                    "cancelled",
                ):
                    raise InvalidToolArgumentsError("invalid objective status")
                updates["status"] = sv
            raw_repos = arguments.get("repos")
            if isinstance(raw_repos, list):
                updates["repos"] = [str(r) for r in raw_repos]
            for field in ("acceptance", "human_notes", "agent_notes"):
                if field in arguments and isinstance(arguments.get(field), str):
                    updates[field] = str(arguments[field])
            if not updates:
                raise InvalidToolArgumentsError(
                    "at least one editable field is required",
                )
            svc = ObjectiveService(workspace_root=status.root_path)
            try:
                saved = svc.edit(objective_id=obj_id, updates=updates)
            except ValueError as exc:
                raise InvalidToolArgumentsError(str(exc)) from exc
            return saved.model_dump(mode="json")

        if name == "metagit_approval_request":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "approval request requires an active workspace",
                )
            action = str(arguments.get("action", "")).strip()
            if not action:
                raise InvalidToolArgumentsError("action is required")
            payload = arguments.get("payload")
            if payload is None or not isinstance(payload, dict):
                raise InvalidToolArgumentsError("payload object is required")
            requested_raw = arguments.get("requested_by")
            requested_by = str(requested_raw).strip() if isinstance(requested_raw, str) else "agent"
            if not requested_by:
                requested_by = "agent"
            idempotency_raw = arguments.get("idempotency_key")
            idempotency_key = (
                str(idempotency_raw).strip() if isinstance(idempotency_raw, str) and idempotency_raw.strip() else None
            )
            req = ApprovalService(workspace_root=status.root_path).request(
                action=action,
                payload=payload,
                requested_by=requested_by,
                idempotency_key=idempotency_key,
            )
            return req.model_dump(mode="json")

        if name == "metagit_approval_list":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "approval list requires an active workspace",
                )
            raw_af = arguments.get("status")
            svc = ApprovalService(workspace_root=status.root_path)
            if raw_af is None:
                return svc.list(status="pending").model_dump(mode="json")
            sf = str(raw_af).strip().lower()
            if sf in ("", "pending"):
                return svc.list(status="pending").model_dump(mode="json")
            if sf == "all":
                return svc.list(status=None).model_dump(mode="json")
            if sf in ("approved", "denied"):
                return svc.list(
                    status=cast(ApprovalStatus, sf),
                ).model_dump(mode="json")
            raise InvalidToolArgumentsError(
                "status must be pending, approved, denied, or all",
            )

        if name == "metagit_approval_resolve":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "approval resolve requires an active workspace",
                )
            appr_id_raw = arguments.get("approval_id")
            appr_id = str(appr_id_raw).strip() if isinstance(appr_id_raw, str) else ""
            decision_raw = arguments.get("decision")
            decision_val = str(decision_raw).strip().lower() if isinstance(decision_raw, str) else ""
            if not appr_id:
                raise InvalidToolArgumentsError("approval_id is required")
            if decision_val not in ("approved", "denied"):
                raise InvalidToolArgumentsError(
                    "decision must be approved or denied",
                )
            decision_typed = cast(
                Literal["approved", "denied"],
                decision_val,
            )
            note_raw = arguments.get("note")
            note_opt = str(note_raw) if isinstance(note_raw, str) else None
            svc = ApprovalService(workspace_root=status.root_path)
            try:
                row = svc.resolve(
                    request_id=appr_id,
                    decision=decision_typed,
                    note=note_opt,
                )
            except ValueError as exc:
                raise InvalidToolArgumentsError(str(exc)) from exc
            return row.model_dump(mode="json")

        if name == "metagit_handoff_list":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "handoff list requires an active workspace",
                )
            status_filter_raw = arguments.get("status")
            status_filter = (
                str(status_filter_raw).strip()
                if isinstance(status_filter_raw, str) and status_filter_raw.strip()
                else None
            )
            svc = HandoffService(workspace_root=status.root_path)
            return svc.list(status=status_filter).model_dump(mode="json")

        if name == "metagit_handoff_create":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "handoff create requires an active workspace",
                )
            title_raw = arguments.get("title")
            if not isinstance(title_raw, str) or not title_raw.strip():
                raise InvalidToolArgumentsError("title is required")
            created_by_raw = arguments.get("created_by", "agent")
            created_by = str(created_by_raw).strip() or "agent"
            payload_raw = arguments.get("payload")
            payload: dict[str, Any] = {}
            if isinstance(payload_raw, dict):
                payload = payload_raw
            svc = HandoffService(workspace_root=status.root_path)
            row = svc.create(title=title_raw.strip(), created_by=created_by, payload=payload)
            return row.model_dump(mode="json")

        if name == "metagit_handoff_claim":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "handoff claim requires an active workspace",
                )
            hid = str(arguments.get("id", "")).strip()
            if not hid:
                raise InvalidToolArgumentsError("id is required")
            claimed_by_raw = arguments.get("claimed_by", "agent")
            claimed_by = str(claimed_by_raw).strip() or "agent"
            note_raw = arguments.get("note")
            note_opt = str(note_raw).strip() if isinstance(note_raw, str) and note_raw.strip() else None
            svc = HandoffService(workspace_root=status.root_path)
            try:
                row = svc.claim(hid, claimed_by=claimed_by, note=note_opt)
            except ValueError as exc:
                raise InvalidToolArgumentsError(str(exc)) from exc
            return row.model_dump(mode="json")

        if name == "metagit_handoff_complete":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "handoff complete requires an active workspace",
                )
            hid = str(arguments.get("id", "")).strip()
            if not hid:
                raise InvalidToolArgumentsError("id is required")
            actor_raw = arguments.get("actor", "agent")
            actor = str(actor_raw).strip() or "agent"
            note_raw = arguments.get("note")
            note_opt = str(note_raw).strip() if isinstance(note_raw, str) and note_raw.strip() else None
            svc = HandoffService(workspace_root=status.root_path)
            try:
                row = svc.complete(hid, actor=actor, note=note_opt)
            except ValueError as exc:
                raise InvalidToolArgumentsError(str(exc)) from exc
            return row.model_dump(mode="json")

        if name == "metagit_events":
            if not status.root_path:
                raise InvalidToolArgumentsError(
                    "events requires an active workspace",
                )
            since_raw = arguments.get("since")
            since_opt = str(since_raw).strip() if isinstance(since_raw, str) and since_raw.strip() else None
            return resolve_backend(status.root_path).events().list_events(since=since_opt).model_dump(mode="json")

        if name.startswith("metagit_task_"):
            return self._call_task_tool(name, arguments, status)

        if name.startswith("metagit_semantic_"):
            return self._call_semantic_tool(name, arguments, status)

        if (
            name.startswith("metagit_branch_")
            or name.startswith("metagit_lease_")
            or name.startswith(
                "metagit_worktree_",
            )
            or name.startswith("metagit_claim_")
        ):
            return self._call_acl_tool(name, arguments, status)

        if name == "metagit_repo_card":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("repo card requires an active workspace")
            proj_name = str(arguments.get("project_name", "")).strip()
            rname = str(arguments.get("repo_name", "")).strip()
            if not proj_name:
                raise InvalidToolArgumentsError("project_name is required")
            if not rname:
                raise InvalidToolArgumentsError("repo_name is required")
            try:
                card = self._repo_card.build_one(
                    config=config,
                    workspace_root=status.root_path,
                    project_name=proj_name,
                    repo_name=rname,
                )
            except ValueError as exc:
                raise InvalidToolArgumentsError(str(exc)) from exc
            return card.model_dump(mode="json")

        if name == "metagit_workspace_discover":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("workspace discover requires an active workspace")
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
                else ([str(item) for item in raw_scope] if isinstance(raw_scope, list) else None)
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
                raise InvalidToolArgumentsError("template apply requires an active workspace")
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
                raise InvalidToolArgumentsError("cross-project dependencies require an active workspace")
            source_project = str(arguments.get("source_project", "")).strip()
            if not source_project:
                raise InvalidToolArgumentsError("source_project is required")
            raw_types = arguments.get("dependency_types")
            dependency_types = [str(item) for item in raw_types] if isinstance(raw_types, list) else None
            depth_raw = arguments.get("depth", 2)
            try:
                depth_val = int(depth_raw)
            except (TypeError, ValueError) as exc:
                raise InvalidToolArgumentsError("depth must be an integer") from exc
            if depth_val < 1:
                raise InvalidToolArgumentsError("depth must be at least 1")
            return self._cross_project_deps.map_dependencies(
                config=config,
                workspace_root=status.root_path,
                source_project=source_project,
                dependency_types=dependency_types,
                depth=depth_val,
                include_external_repos=bool(arguments.get("include_external_repos", False)),
            ).model_dump(mode="json")

        if name == "metagit_export_workspace_graph_cypher":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("graph cypher export requires an active workspace")
            gitnexus_repo = arguments.get("gitnexus_repo")
            repo_name = str(gitnexus_repo).strip() if isinstance(gitnexus_repo, str) and gitnexus_repo.strip() else None
            return self._graph_cypher_export.export(
                config=config,
                workspace_root=status.root_path,
                gitnexus_repo=repo_name,
                include_structure=bool(arguments.get("include_structure", True)),
                include_documentation=bool(arguments.get("include_documentation", False)),
                manual_only=bool(arguments.get("manual_only", False)),
                with_schema=bool(arguments.get("with_schema", True)),
            ).model_dump(mode="json")

        if name in {
            "metagit_suggest_graph_relationships",
            "metagit_apply_graph_relationships",
        }:
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("graph relationship tools require an active workspace")
            config_path, _ = self._catalog_paths(status=status, config=config)
            suggest_args = self._graph_suggest_tool_args(arguments)
            if name == "metagit_suggest_graph_relationships":
                return self._graph_suggest.suggest(
                    config=config,
                    workspace_root=status.root_path,
                    **suggest_args,
                ).model_dump(mode="json")
            return self._graph_suggest.suggest_and_apply(
                config=config,
                workspace_root=status.root_path,
                config_path=config_path,
                dry_run=bool(arguments.get("dry_run", False)),
                save=bool(arguments.get("save", True)),
                **suggest_args,
            ).model_dump(mode="json")

        if name == "metagit_gitnexus_group_sync":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("gitnexus group sync requires an active workspace")
            group_name = arguments.get("group_name")
            resolved_group = str(group_name).strip() if isinstance(group_name, str) and group_name.strip() else None
            return self._gitnexus_group_sync.sync_workspace(
                config=config,
                workspace_root=status.root_path,
                group_name=resolved_group,
                create_group=bool(arguments.get("create_group", True)),
                prune=bool(arguments.get("prune", False)),
                run_contract_sync=bool(arguments.get("run_contract_sync", True)),
                allow_stale=bool(arguments.get("allow_stale", False)),
                skip_embeddings=bool(arguments.get("skip_embeddings", False)),
                exact_only=bool(arguments.get("exact_only", False)),
                verbose=bool(arguments.get("verbose", False)),
            ).model_dump(mode="json")

        if name == "metagit_workspace_list":
            config_path, workspace_root = self._catalog_paths(status=status, config=config)
            return self._workspace_catalog.list_workspace(
                config=config,
                config_path=config_path,
                workspace_root=workspace_root,
            ).model_dump(mode="json")

        if name == "metagit_workspace_projects_list":
            config_path, workspace_root = self._catalog_paths(status=status, config=config)
            _ = (config_path, workspace_root)
            return self._workspace_catalog.list_projects(config=config).model_dump(mode="json")

        if name == "metagit_workspace_project_add":
            config_path, _ = self._catalog_paths(status=status, config=config)
            project_name = str(arguments.get("name", "")).strip()
            return self._workspace_catalog.add_project(
                config=config,
                config_path=config_path,
                name=project_name,
                description=arguments.get("description"),
                agent_instructions=arguments.get("agent_instructions"),
                ensure=bool(arguments.get("ensure", True)),
            ).model_dump(mode="json")

        if name == "metagit_workspace_project_remove":
            config_path, _ = self._catalog_paths(status=status, config=config)
            return self._workspace_catalog.remove_project(
                config=config,
                config_path=config_path,
                name=str(arguments.get("name", "")).strip(),
                force=bool(arguments.get("force", False)),
            ).model_dump(mode="json")

        if name == "metagit_workspace_repos_list":
            config_path, workspace_root = self._catalog_paths(status=status, config=config)
            _ = config_path
            project_filter = arguments.get("project_name")
            return self._workspace_catalog.list_repos(
                config=config,
                workspace_root=workspace_root,
                project_name=str(project_filter).strip()
                if isinstance(project_filter, str) and project_filter.strip()
                else None,
            ).model_dump(mode="json")

        if name == "metagit_workspace_repo_add":
            config_path, _ = self._catalog_paths(status=status, config=config)
            built = self._workspace_catalog.build_repo_from_fields(
                name=str(arguments.get("name", "")),
                description=arguments.get("description"),
                path=arguments.get("path"),
                url=arguments.get("url"),
                sync=arguments.get("sync"),
                agent_instructions=arguments.get("agent_instructions"),
                tags=arguments.get("tags") if isinstance(arguments.get("tags"), dict) else None,
                protected=arguments.get("protected"),
            )
            if isinstance(built, CatalogError):
                return {"ok": False, "error": built.model_dump(mode="json")}
            return self._workspace_catalog.add_repo(
                config=config,
                config_path=config_path,
                project_name=str(arguments.get("project_name", "")).strip(),
                repo=built,
                ensure=bool(arguments.get("ensure", True)),
                force=bool(arguments.get("force", False)),
            ).model_dump(mode="json")

        if name == "metagit_workspace_repo_remove":
            config_path, _ = self._catalog_paths(status=status, config=config)
            return self._workspace_catalog.remove_repo(
                config=config,
                config_path=config_path,
                project_name=str(arguments.get("project_name", "")).strip(),
                repo_name=str(arguments.get("name", "")).strip(),
                force=bool(arguments.get("force", False)),
            ).model_dump(mode="json")

        if name == "metagit_project_source_sync":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("project source sync requires an active workspace")
            config_path, _ = self._catalog_paths(status=status, config=config)
            app_config = AppConfig.load()
            if isinstance(app_config, Exception):
                return {
                    "ok": False,
                    "errors": [
                        {
                            "kind": "app_config",
                            "message": str(app_config),
                        }
                    ],
                }
            logger = UnifiedLogger(LoggerConfig(log_level="INFO", minimal_console=True))
            return run_mcp_source_sync(
                app_config=app_config,
                logger=logger,
                config=config,
                config_path=config_path,
                arguments=arguments,
            )

        if name in {
            "metagit_workspace_project_rename",
            "metagit_workspace_repo_rename",
            "metagit_workspace_repo_move",
        }:
            config_path, definition_root = self._catalog_paths(status=status, config=config)
            sync_root, dedupe = resolve_sync_context(definition_root)
            dry_run = bool(arguments.get("dry_run", False))
            move_disk = bool(arguments.get("move_disk", True))
            force = bool(arguments.get("force", False))
            if name == "metagit_workspace_project_rename":
                return self._workspace_layout.rename_project(
                    config=config,
                    config_path=config_path,
                    workspace_path=sync_root,
                    from_name=str(arguments.get("from_name", "")).strip(),
                    to_name=str(arguments.get("to_name", "")).strip(),
                    dedupe=dedupe,
                    dry_run=dry_run,
                    move_disk=move_disk,
                    update_sessions=bool(arguments.get("update_sessions", True)),
                    force=force,
                ).model_dump(mode="json")
            if name == "metagit_workspace_repo_rename":
                return self._workspace_layout.rename_repo(
                    config=config,
                    config_path=config_path,
                    workspace_path=sync_root,
                    project_name=str(arguments.get("project_name", "")).strip(),
                    from_name=str(arguments.get("from_name", "")).strip(),
                    to_name=str(arguments.get("to_name", "")).strip(),
                    dedupe=dedupe,
                    dry_run=dry_run,
                    move_disk=move_disk,
                    force=force,
                ).model_dump(mode="json")
            return self._workspace_layout.move_repo(
                config=config,
                config_path=config_path,
                workspace_path=sync_root,
                repo_name=str(arguments.get("repo_name", "")).strip(),
                from_project=str(arguments.get("from_project", "")).strip(),
                to_project=str(arguments.get("to_project", "")).strip(),
                dedupe=dedupe,
                dry_run=dry_run,
                move_disk=move_disk,
                force=force,
            ).model_dump(mode="json")

        if name == "metagit_session_update":
            if not config or not status.root_path:
                raise InvalidToolArgumentsError("session update requires an active workspace")
            project_name = str(arguments.get("project_name", "")).strip()
            if not project_name:
                raise InvalidToolArgumentsError("project_name is required")
            recent = arguments.get("recent_repos")
            recent_repos = [str(item) for item in recent] if isinstance(recent, list) else None
            env_raw = arguments.get("env_overrides")
            env_overrides = {str(k): str(v) for k, v in env_raw.items()} if isinstance(env_raw, dict) else None
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

        if name == "metagit_agent_catalog":
            if not status.root_path:
                raise InvalidToolArgumentsError("agent catalog requires an active workspace")
            service = AgentService(manifest_root=Path(status.root_path))
            envelope = service.catalog.list_catalog(
                manifest_root=Path(status.root_path),
            )
            return envelope.model_dump(mode="json")

        if name == "metagit_agent_dispatch_plan":
            if not status.root_path:
                raise InvalidToolArgumentsError("agent dispatch plan requires an active workspace")
            template_id = str(arguments.get("template_id", "")).strip()
            if not template_id:
                raise InvalidToolArgumentsError("template_id is required")
            vendor = str(arguments.get("vendor", "claude_code")).strip()
            scope_raw = arguments.get("scope", "project")
            scope_val = str(scope_raw).strip() if isinstance(scope_raw, str) and scope_raw.strip() else "project"
            if scope_val not in {"project", "user"}:
                raise InvalidToolArgumentsError("scope must be project or user")
            project_raw = arguments.get("project_name")
            repo_raw = arguments.get("repo_name")
            task_raw = arguments.get("task")
            project_opt = str(project_raw).strip() if isinstance(project_raw, str) and project_raw.strip() else None
            repo_opt = str(repo_raw).strip() if isinstance(repo_raw, str) and repo_raw.strip() else None
            task_opt = str(task_raw).strip() if isinstance(task_raw, str) and task_raw.strip() else None
            service = AgentService(manifest_root=Path(status.root_path))
            try:
                plan = service.dispatch_plan(
                    template_id,
                    vendor=vendor,
                    scope=scope_val,  # type: ignore[arg-type]
                    project=project_opt,
                    repo=repo_opt,
                    task=task_opt,
                    config=config,
                )
            except Exception as exc:
                raise InvalidToolArgumentsError(str(exc)) from exc
            return plan.model_dump(mode="json")

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

    def _call_acl_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        status: WorkspaceStatus,
    ) -> dict[str, Any]:
        """Dispatch RFC-0007 ACL MCP tools against the session root."""
        if not status.root_path:
            raise InvalidToolArgumentsError(f"{name} requires an active workspace")
        root = status.root_path
        definition = str(Path(root) / ".metagit.yml")
        worktrees_path: str | None = None
        try:
            app_cfg = AppConfig.load()
            if isinstance(app_cfg, AppConfig) and app_cfg.workspace:
                worktrees_path = app_cfg.workspace.worktrees_path
        except Exception:  # noqa: BLE001 — fall back to defaults
            worktrees_path = None

        def _require(key: str) -> str:
            value = str(arguments.get(key, "")).strip()
            if not value:
                raise InvalidToolArgumentsError(f"{key} is required")
            return value

        def _unwrap(result: Any) -> dict[str, Any]:
            if isinstance(result, Exception):
                raise InvalidToolArgumentsError(str(result)) from result
            if hasattr(result, "model_dump"):
                return result.model_dump(mode="json")
            if isinstance(result, list):
                return {
                    "ok": True,
                    "items": [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in result],
                }
            return {"ok": True, "result": result}

        if name == "metagit_branch_allocate":
            service = BranchService(root, sync_root=root, definition_path=definition)
            return _unwrap(
                service.allocate(
                    repository=_require("repository"),
                    agent_id=_require("agent_id"),
                    task_id=_require("task_id"),
                    description=arguments.get("description") if isinstance(arguments.get("description"), str) else None,
                    branch_name=arguments.get("branch_name") if isinstance(arguments.get("branch_name"), str) else None,
                    base=arguments.get("base") if isinstance(arguments.get("base"), str) else None,
                    integration_branch=arguments.get("integration_branch")
                    if isinstance(arguments.get("integration_branch"), str)
                    else None,
                    create_git_branch=bool(arguments.get("create_git_branch", True)),
                ),
            )
        if name == "metagit_branch_list":
            service = BranchService(root, sync_root=root, definition_path=definition)
            return _unwrap(
                service.list(
                    repository=arguments.get("repository") if isinstance(arguments.get("repository"), str) else None,
                    status=arguments.get("status") if isinstance(arguments.get("status"), str) else None,
                ),
            )
        if name == "metagit_branch_release":
            service = BranchService(root, sync_root=root, definition_path=definition)
            return _unwrap(
                service.release(
                    branch_id=arguments.get("branch_id") if isinstance(arguments.get("branch_id"), str) else None,
                    name=arguments.get("name") if isinstance(arguments.get("name"), str) else None,
                    repository=arguments.get("repository") if isinstance(arguments.get("repository"), str) else None,
                ),
            )
        if name == "metagit_lease_acquire":
            service = LeaseService(root, sync_root=root, definition_path=definition)
            return _unwrap(
                service.acquire(
                    repository=_require("repository"),
                    agent_id=_require("agent_id"),
                    task_id=_require("task_id"),
                    branch=arguments.get("branch") if isinstance(arguments.get("branch"), str) else None,
                    branch_id=arguments.get("branch_id") if isinstance(arguments.get("branch_id"), str) else None,
                    ttl=str(arguments.get("ttl") or "30m"),
                    allocate_if_missing=bool(arguments.get("allocate", False)),
                    description=arguments.get("description") if isinstance(arguments.get("description"), str) else None,
                ),
            )
        if name == "metagit_lease_renew":
            service = LeaseService(root, sync_root=root, definition_path=definition)
            return _unwrap(
                service.renew(
                    lease_id=_require("lease_id"),
                    agent_id=_require("agent_id"),
                    ttl=str(arguments.get("ttl") or "30m"),
                    force=bool(arguments.get("force", False)),
                ),
            )
        if name == "metagit_lease_release":
            service = LeaseService(root, sync_root=root, definition_path=definition)
            return _unwrap(
                service.release(
                    lease_id=_require("lease_id"),
                    agent_id=_require("agent_id"),
                    force=bool(arguments.get("force", False)),
                    release_branch=bool(arguments.get("release_branch", False)),
                ),
            )
        if name == "metagit_lease_list":
            service = LeaseService(root, sync_root=root, definition_path=definition)
            return _unwrap(
                service.list(
                    repository=arguments.get("repository") if isinstance(arguments.get("repository"), str) else None,
                    status=arguments.get("status") if isinstance(arguments.get("status"), str) else None,
                    agent_id=arguments.get("agent_id") if isinstance(arguments.get("agent_id"), str) else None,
                ),
            )
        if name == "metagit_worktree_create":
            service = WorktreeService(
                root,
                sync_root=root,
                definition_path=definition,
                worktrees_path=worktrees_path,
            )
            claims_raw = arguments.get("claims")
            claims = [str(item) for item in claims_raw] if isinstance(claims_raw, list) else None
            return _unwrap(
                service.create(
                    repository=_require("repository"),
                    agent_id=_require("agent_id"),
                    task_id=_require("task_id"),
                    branch=_require("branch"),
                    lease_id=arguments.get("lease_id") if isinstance(arguments.get("lease_id"), str) else None,
                    integration_branch=arguments.get("integration_branch")
                    if isinstance(arguments.get("integration_branch"), str)
                    else None,
                    claims=claims,
                ),
            )
        if name == "metagit_worktree_destroy":
            service = WorktreeService(
                root,
                sync_root=root,
                definition_path=definition,
                worktrees_path=worktrees_path,
            )
            return _unwrap(
                service.destroy(
                    worktree_id=arguments.get("worktree_id") if isinstance(arguments.get("worktree_id"), str) else None,
                    agent_id=arguments.get("agent_id") if isinstance(arguments.get("agent_id"), str) else None,
                    repository=arguments.get("repository") if isinstance(arguments.get("repository"), str) else None,
                    force=bool(arguments.get("force", False)),
                ),
            )
        if name == "metagit_worktree_status":
            service = WorktreeService(
                root,
                sync_root=root,
                definition_path=definition,
                worktrees_path=worktrees_path,
            )
            return _unwrap(
                service.status(
                    worktree_id=arguments.get("worktree_id") if isinstance(arguments.get("worktree_id"), str) else None,
                    agent_id=arguments.get("agent_id") if isinstance(arguments.get("agent_id"), str) else None,
                ),
            )
        if name == "metagit_worktree_list":
            service = WorktreeService(
                root,
                sync_root=root,
                definition_path=definition,
                worktrees_path=worktrees_path,
            )
            return _unwrap(
                service.list(
                    repository=arguments.get("repository") if isinstance(arguments.get("repository"), str) else None,
                    agent_id=arguments.get("agent_id") if isinstance(arguments.get("agent_id"), str) else None,
                    status=arguments.get("status") if isinstance(arguments.get("status"), str) else None,
                ),
            )
        if name == "metagit_claim_declare":
            service = ClaimService(root)
            patterns_raw = arguments.get("patterns")
            if not isinstance(patterns_raw, list) or not patterns_raw:
                raise InvalidToolArgumentsError("patterns is required")
            result = service.declare(
                repository=_require("repository"),
                agent_id=_require("agent_id"),
                patterns=[str(item) for item in patterns_raw],
                task_id=arguments.get("task_id") if isinstance(arguments.get("task_id"), str) else None,
                allow_conflicts=not bool(arguments.get("strict", False)),
            )
            if isinstance(result, ClaimCheckResult):
                payload = result.model_dump(mode="json")
                payload["ok"] = False
                return payload
            return _unwrap(result)
        if name == "metagit_claim_check":
            service = ClaimService(root)
            patterns_raw = arguments.get("patterns")
            if not isinstance(patterns_raw, list) or not patterns_raw:
                raise InvalidToolArgumentsError("patterns is required")
            return _unwrap(
                service.check(
                    repository=_require("repository"),
                    patterns=[str(item) for item in patterns_raw],
                    agent_id=arguments.get("agent_id") if isinstance(arguments.get("agent_id"), str) else None,
                ),
            )
        if name == "metagit_claim_list":
            service = ClaimService(root)
            return _unwrap(
                service.list(
                    repository=arguments.get("repository") if isinstance(arguments.get("repository"), str) else None,
                    agent_id=arguments.get("agent_id") if isinstance(arguments.get("agent_id"), str) else None,
                    status=arguments.get("status") if isinstance(arguments.get("status"), str) else None,
                ),
            )
        if name == "metagit_claim_release":
            service = ClaimService(root)
            return _unwrap(
                service.release(
                    claim_id=_require("claim_id"),
                    agent_id=_require("agent_id"),
                    force=bool(arguments.get("force", False)),
                ),
            )
        raise ValueError(f"Unsupported ACL tool: {name}")

    def _call_task_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        status: WorkspaceStatus,
    ) -> dict[str, Any]:
        if not status.root_path:
            raise InvalidToolArgumentsError("task tools require an active workspace")
        root = status.root_path
        service = TaskGraphService(root)

        def _require(key: str) -> str:
            value = str(arguments.get(key, "")).strip()
            if not value:
                raise InvalidToolArgumentsError(f"{key} is required")
            return value

        def _unwrap(result: Any) -> dict[str, Any]:
            if isinstance(result, Exception):
                raise InvalidToolArgumentsError(str(result)) from result
            if hasattr(result, "model_dump"):
                return result.model_dump(mode="json")
            if isinstance(result, list):
                return {
                    "ok": True,
                    "items": [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in result],
                }
            return {"ok": True, "result": result}

        if name == "metagit_task_create":
            acceptance_raw = arguments.get("acceptance")
            repos_raw = arguments.get("repos")
            return _unwrap(
                service.create(
                    title=_require("title"),
                    goal=_require("goal"),
                    acceptance=[str(item) for item in acceptance_raw] if isinstance(acceptance_raw, list) else None,
                    objective_id=arguments.get("objective_id")
                    if isinstance(arguments.get("objective_id"), str)
                    else None,
                    handoff_id=arguments.get("handoff_id") if isinstance(arguments.get("handoff_id"), str) else None,
                    project=arguments.get("project") if isinstance(arguments.get("project"), str) else None,
                    repos=[str(item) for item in repos_raw] if isinstance(repos_raw, list) else None,
                    graph_id=arguments.get("graph_id") if isinstance(arguments.get("graph_id"), str) else None,
                ),
            )
        if name == "metagit_task_expand":
            outline = arguments.get("outline")
            if outline is None:
                raise InvalidToolArgumentsError("outline is required")
            return _unwrap(service.expand(_require("graph_id"), outline))
        if name == "metagit_task_list":
            graph_id = arguments.get("graph_id") if isinstance(arguments.get("graph_id"), str) else None
            status_filter = arguments.get("status") if isinstance(arguments.get("status"), str) else None
            if graph_id or status_filter:
                return _unwrap(service.list_nodes(graph_id=graph_id, status=status_filter))  # type: ignore[arg-type]
            return _unwrap(service.list_graphs())
        if name == "metagit_task_status":
            return _unwrap(
                service.status(
                    _require("node_id"),
                    graph_id=arguments.get("graph_id") if isinstance(arguments.get("graph_id"), str) else None,
                ),
            )
        if name == "metagit_task_ready":
            return _unwrap(
                service.ready(arguments.get("graph_id") if isinstance(arguments.get("graph_id"), str) else None),
            )
        if name == "metagit_task_block":
            return _unwrap(
                service.block(
                    _require("node_id"),
                    _require("reason"),
                    graph_id=arguments.get("graph_id") if isinstance(arguments.get("graph_id"), str) else None,
                ),
            )
        if name == "metagit_task_complete":
            return _unwrap(
                service.complete(
                    _require("node_id"),
                    graph_id=arguments.get("graph_id") if isinstance(arguments.get("graph_id"), str) else None,
                ),
            )
        if name == "metagit_task_bind_acl":
            return _unwrap(
                service.bind_acl(
                    _require("node_id"),
                    agent_id=_require("agent_id"),
                    graph_id=arguments.get("graph_id") if isinstance(arguments.get("graph_id"), str) else None,
                    branch=arguments.get("branch") if isinstance(arguments.get("branch"), str) else None,
                    lease_id=arguments.get("lease_id") if isinstance(arguments.get("lease_id"), str) else None,
                    worktree_id=arguments.get("worktree_id") if isinstance(arguments.get("worktree_id"), str) else None,
                    pattern=arguments.get("pattern") if isinstance(arguments.get("pattern"), str) else None,
                ),
            )
        raise ValueError(f"Unsupported task tool: {name}")

    def _call_semantic_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        status: WorkspaceStatus,
    ) -> dict[str, Any]:
        if not status.root_path:
            raise InvalidToolArgumentsError("semantic tools require an active workspace")
        service = SemanticGraphService(status.root_path)

        def _require(key: str) -> str:
            value = str(arguments.get(key, "")).strip()
            if not value:
                raise InvalidToolArgumentsError(f"{key} is required")
            return value

        def _unwrap(result: Any) -> dict[str, Any]:
            if isinstance(result, Exception):
                raise InvalidToolArgumentsError(str(result)) from result
            if hasattr(result, "model_dump"):
                return result.model_dump(mode="json")
            return {"ok": True, "result": result}

        if name == "metagit_semantic_declare":
            patterns_raw = arguments.get("patterns")
            if not isinstance(patterns_raw, list) or not patterns_raw:
                raise InvalidToolArgumentsError("patterns is required")
            symbol_hints_raw = arguments.get("symbol_hints")
            return _unwrap(
                service.declare(
                    concept=_require("concept"),
                    repository=_require("repository"),
                    patterns=[str(item) for item in patterns_raw],
                    symbol_hints=[str(item) for item in symbol_hints_raw]
                    if isinstance(symbol_hints_raw, list)
                    else None,
                ),
            )
        if name == "metagit_semantic_query":
            return _unwrap(service.query(concept=_require("concept")))
        if name == "metagit_semantic_owners":
            return _unwrap(
                service.owners(
                    path=_require("path"),
                    repository=_require("repository"),
                ),
            )
        if name == "metagit_semantic_conflicts":
            return _unwrap(service.conflicts(repository=_require("repository")))
        if name == "metagit_semantic_ingest":
            project = arguments.get("project") if isinstance(arguments.get("project"), str) else None
            return {
                "ok": True,
                "added": 0,
                "updated": 0,
                "project": project,
                "message": "semantic ingest is deferred until RFC-0010 Task 8",
            }
        raise ValueError(f"Unsupported semantic tool: {name}")

    def _resolve_status_and_config(self) -> tuple[WorkspaceStatus, Any]:
        resolved_root = self._resolver.resolve(cwd=os.getcwd(), cli_root=self._root_override)
        status = self._gate.evaluate(root_path=resolved_root)
        config = None
        if status.state == McpActivationState.ACTIVE and status.root_path:
            manager = MetagitConfigManager(config_path=Path(status.root_path) / ".metagit.yml")
            loaded = manager.load_config()
            config = None if isinstance(loaded, Exception) else loaded
        return status, config

    def _build_repo_index(self, status: WorkspaceStatus, config: Any) -> list[dict[str, Any]]:
        if status.state != McpActivationState.ACTIVE or not config or not status.root_path:
            return []
        return self._index_service.build_index(config=config, workspace_root=status.root_path)

    def _catalog_paths(self, status: WorkspaceStatus, config: Any) -> tuple[str, str]:
        if not config or not status.root_path:
            raise InvalidToolArgumentsError("catalog operations require an active workspace")
        config_path = str(Path(status.root_path) / ".metagit.yml")
        return config_path, status.root_path

    def _graph_suggest_tool_args(
        self,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize MCP arguments for graph relationship suggest/apply."""
        dependency_types = arguments.get("dependency_types")
        selected_types = [str(item) for item in dependency_types] if isinstance(dependency_types, list) else None
        candidate_ids = arguments.get("candidate_ids")
        selected_ids = [str(item) for item in candidate_ids] if isinstance(candidate_ids, list) else None
        min_confidence = arguments.get("min_confidence", "medium")
        confidence = str(min_confidence) if min_confidence in {"high", "medium", "all"} else "medium"
        depth_raw = arguments.get("depth", 3)
        depth = int(depth_raw) if isinstance(depth_raw, int) else 3
        return {
            "dependency_types": selected_types,
            "depth": max(1, depth),
            "min_confidence": confidence,
            "include_declared": bool(arguments.get("include_declared", False)),
            "candidate_ids": selected_ids,
        }

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
                            "text": (f"Create a valid .metagit.yml from this context. Output YAML only.\n{context}"),
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
        if isinstance(content, dict) and content.get("type") == "text":
            return content.get("text")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    return item.get("text")
        return None
