#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.resource_service
"""

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.models import McpActivationState, WorkspaceStatus
from metagit.core.mcp.resource_service import ResourceContext, ResourceService
from metagit.core.mcp.services.ops_log import OperationsLogService


def _active_context(
    config: MetagitConfig,
    *,
    root: str = "/tmp/ws",
    repos_status: list[dict] | None = None,
) -> ResourceContext:
    return ResourceContext(
        status=WorkspaceStatus(
            state=McpActivationState.ACTIVE,
            root_path=root,
        ),
        config=config,
        config_path=f"{root}/.metagit.yml",
        workspace_root=root,
        session_root=root,
        definition_root=root,
        repos_status=repos_status or [],
        health_payload={"ok": True},
        workspace_dedupe=None,
    )


def test_read_map_returns_workspace_map() -> None:
    config = MetagitConfig(
        name="demo",
        kind="application",
        workspace={"projects": [{"name": "default", "repos": [{"name": "app", "path": "./app"}]}]},
    )
    service = ResourceService(ops_log=OperationsLogService())
    result = service.read(
        "metagit://workspace/map",
        _active_context(
            config,
            repos_status=[
                {
                    "project_name": "default",
                    "repo_name": "app",
                    "repo_path": "/tmp/ws/app",
                    "status": "present",
                    "exists": True,
                }
            ],
        ),
    )
    assert result.error is None
    assert result.data is not None
    assert result.data["workspace_name"] == "demo"


def test_read_config_summary_by_default() -> None:
    config = MetagitConfig(
        name="demo",
        kind="application",
        workspace={"projects": [{"name": "default", "repos": [{"name": "app", "path": "./app"}]}]},
    )
    service = ResourceService(ops_log=OperationsLogService())
    result = service.read("metagit://workspace/config", _active_context(config))
    assert result.data["view"] == "summary"
    assert result.data["project_count"] == 1


def test_read_prompt_returns_plain_text() -> None:
    config = MetagitConfig(
        name="demo",
        kind="application",
        workspace={"projects": []},
    )
    service = ResourceService(ops_log=OperationsLogService())
    result = service.read(
        "metagit://prompt/workspace/session-start?instructions=0",
        _active_context(config),
    )
    assert result.mime_type == "text/plain"
    assert result.text
    assert "metagit" in result.text.lower()


def test_read_project_summary() -> None:
    config = MetagitConfig(
        name="demo",
        kind="application",
        workspace={
            "projects": [
                {
                    "name": "default",
                    "repos": [
                        {"name": "app", "path": "./app"},
                        {"name": "lib", "path": "./lib"},
                    ],
                }
            ]
        },
    )
    service = ResourceService(ops_log=OperationsLogService())
    result = service.read(
        "metagit://project/default/summary",
        _active_context(
            config,
            repos_status=[
                {
                    "project_name": "default",
                    "repo_name": "app",
                    "status": "present",
                    "exists": True,
                },
                {
                    "project_name": "default",
                    "repo_name": "lib",
                    "status": "missing",
                    "exists": False,
                },
            ],
        ),
    )
    assert result.data["repo_count"] == 2
    assert result.data["health_summary"]["missing_clone"] == 1


def test_read_objectives_slim_by_default() -> None:
    config = MetagitConfig(
        name="demo",
        kind="application",
        workspace={"projects": []},
    )
    service = ResourceService(ops_log=OperationsLogService())
    result = service.read(
        "metagit://objectives",
        _active_context(config),
    )
    assert isinstance(result.data, list)


def test_read_repos_status_summary() -> None:
    config = MetagitConfig(name="demo", kind="application", workspace={"projects": []})
    service = ResourceService(ops_log=OperationsLogService())
    result = service.read(
        "metagit://workspace/repos/status?summary=1",
        _active_context(
            config,
            repos_status=[
                {
                    "project_name": "alpha",
                    "repo_name": "api",
                    "status": "present",
                    "exists": True,
                },
                {
                    "project_name": "alpha",
                    "repo_name": "lib",
                    "status": "missing",
                    "exists": False,
                },
            ],
        ),
    )
    assert result.data["view"] == "summary"
    assert result.data["missing_clone"] == 1


def test_read_session_digest_summary() -> None:
    config = MetagitConfig(name="demo", kind="application", workspace={"projects": []})
    service = ResourceService(ops_log=OperationsLogService())
    result = service.read(
        "metagit://session/digest/summary",
        _active_context(config),
    )
    assert result.data["view"] == "summary"
    assert "first_session" in result.data


def test_read_gate_status_includes_state_backend() -> None:
    config = MetagitConfig(name="demo", kind="application", workspace={"projects": []})
    service = ResourceService(ops_log=OperationsLogService())
    result = service.read(
        "metagit://gate/status",
        _active_context(config, root="/tmp/ws"),
    )
    assert result.data["state_backend"]["backend"] == "local"


def test_read_events_recent_uses_state_backend(tmp_path) -> None:
    config = MetagitConfig(name="demo", kind="application", workspace={"projects": []})
    root = str(tmp_path)
    service = ResourceService(ops_log=OperationsLogService())
    result = service.read(
        "metagit://events/recent",
        _active_context(config, root=root),
    )
    assert result.error is None
    assert result.data["schema_version"] == "1.0"
    assert isinstance(result.data["events"], list)
