#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.runtime
"""

import json
from pathlib import Path

import pytest

from metagit.core.mcp.runtime import MetagitMcpRuntime


def test_initialize_request_returns_capabilities(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )

    assert response is not None
    assert response["result"]["serverInfo"]["name"] == "metagit-mcp"
    assert "tools" in response["result"]["capabilities"]


def test_tools_list_returns_inactive_tools_without_config(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )

    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_workspace_status" in names
    assert "metagit_bootstrap_config_plan_only" in names
    assert "metagit_workspace_index" not in names
    workspace_status_tool = next(
        item for item in response["result"]["tools"] if item["name"] == "metagit_workspace_status"
    )
    assert workspace_status_tool["inputSchema"]["type"] == "object"


def test_tools_call_workspace_status_returns_text_payload(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "metagit_workspace_status", "arguments": {}},
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["state"] == "inactive_missing_config"


def test_resources_read_ops_log_returns_json_content(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/read",
            "params": {"uri": "metagit://workspace/ops-log"},
        }
    )

    assert response is not None
    assert response["result"]["contents"][0]["mimeType"] == "application/json"


def test_tools_call_invalid_arguments_returns_mcp_invalid_params(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "metagit_workspace_search", "arguments": {}},
        }
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["kind"] == "invalid_arguments"


def test_tools_call_workspace_semantic_search_requires_query(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: default",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "metagit_workspace_semantic_search",
                "arguments": {"query": "  "},
            },
        }
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["kind"] == "invalid_arguments"


def test_initialize_can_enable_sampling_capability(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "initialize",
            "params": {"capabilities": {"sampling": {}}},
        }
    )

    assert response is not None
    assert runtime._sampling_supported is True


def test_bootstrap_uses_sampling_when_client_supports_it(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: sampled-workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: default",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    runtime._sampling_supported = True
    runtime._request_client_sampling = lambda context: {  # type: ignore[method-assign]
        "content": {
            "type": "text",
            "text": "\n".join(
                [
                    "name: sampled",
                    "kind: application",
                    "workspace:",
                    "  projects:",
                    "    - name: default",
                    "      repos: []",
                ]
            )
            + "\n",
        }
    }

    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "metagit_bootstrap_config", "arguments": {}},
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["mode"] == "sampled"


def test_tools_call_workspace_grep_info_returns_backend(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: default",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "metagit_workspace_grep_info", "arguments": {}},
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert "ripgrep_available" in payload
    assert payload["search_backend"] in {"ripgrep", "python_walk"}


def test_tools_call_version_check_returns_structured_payload(
    tmp_path: Path, monkeypatch: object
) -> None:
    from datetime import datetime, timezone
    from unittest.mock import MagicMock

    from metagit.core.release.models import LatestReleaseInfo, VersionCheckResult

    fake_result = VersionCheckResult(
        installed_version="1.0.0",
        latest_release=LatestReleaseInfo(
            version="2.0.0",
            tag_name="v2.0.0",
            published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            html_url="https://github.com/metagit-ai/metagit-cli/releases/tag/v2.0.0",
            body="notes",
            source="github",
        ),
        pypi_version="2.0.0",
        update_available=True,
        is_latest=False,
    )
    fake_service = MagicMock()
    fake_service.check.return_value = fake_result
    monkeypatch.setattr(
        "metagit.core.mcp.runtime.ReleaseCheckService",
        lambda *args, **kwargs: fake_service,
    )

    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "metagit_version_check",
                "arguments": {"include_notes": True},
            },
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["installed_version"] == "1.0.0"
    assert payload["latest_release"]["version"] == "2.0.0"
    assert payload["update_available"] is True
    fake_service.check.assert_called_once_with(include_notes=True)


def test_tools_call_version_upgrade_dry_run_by_default(
    tmp_path: Path, monkeypatch: object
) -> None:
    from unittest.mock import MagicMock

    from metagit.core.release.models import VersionCheckResult, VersionUpgradeResult

    fake_result = VersionUpgradeResult(
        ok=True,
        dry_run=True,
        install_method="uv_tool",
        command="uv tool upgrade metagit-cli",
        check=VersionCheckResult(installed_version="1.0.0"),
        message="dry-run",
    )
    fake_service = MagicMock()
    fake_service.upgrade.return_value = fake_result
    monkeypatch.setattr(
        "metagit.core.mcp.runtime.VersionUpgradeService",
        lambda *args, **kwargs: fake_service,
    )

    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {"name": "metagit_version_upgrade", "arguments": {}},
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["dry_run"] is True
    fake_service.upgrade.assert_called_once_with(apply=False)


def test_tools_list_includes_repo_search_for_active_workspace(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}}
    )

    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_repo_search" in names


def test_tools_call_repo_search_returns_matches(tmp_path: Path) -> None:
    repo_dir = tmp_path / "platform" / "abacus-app"
    repo_dir.mkdir(parents=True)
    (repo_dir / ".git").mkdir()
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: abacus-app",
                "          path: platform/abacus-app",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {"name": "metagit_repo_search", "arguments": {"query": "abacus"}},
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["matches"][0]["repo_name"] == "abacus-app"


def test_tools_list_includes_project_context_tools(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 20, "method": "tools/list", "params": {}}
    )

    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_project_context_switch" in names
    assert "metagit_workspace_state_snapshot" in names


def test_tools_call_project_context_switch_unknown_project(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "name": "metagit_project_context_switch",
                "arguments": {"project_name": "missing"},
            },
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is False
    assert payload["error"] == "project_not_found"


def test_tools_call_cross_project_dependencies(tmp_path: Path) -> None:
    (tmp_path / "alpha" / "api").mkdir(parents=True)
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos:",
                "        - name: api",
                "          path: alpha/api",
                "          sync: true",
                "    - name: beta",
                "      repos:",
                "        - name: worker",
                "          path: beta/worker",
                "          sync: true",
                "          tags:",
                "            depends_on: alpha",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 30,
            "method": "tools/call",
            "params": {
                "name": "metagit_cross_project_dependencies",
                "arguments": {
                    "source_project": "alpha",
                    "dependency_types": ["declared"],
                    "depth": 2,
                },
            },
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert payload["source_project"] == "alpha"


def test_tools_list_includes_context_pack_tools_when_active(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 40, "method": "tools/list", "params": {}}
    )

    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_context_pack" in names
    assert "metagit_repo_card" in names


def test_tools_call_metagit_context_pack_tier_zero_succeeds(
    tmp_path: Path,
) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos:",
                "        - name: api",
                "          path: alpha/api",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    repo_dir = tmp_path / "alpha" / "api"
    repo_dir.mkdir(parents=True)
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 41,
            "method": "tools/call",
            "params": {
                "name": "metagit_context_pack",
                "arguments": {"tier": 0},
            },
        }
    )

    assert response is not None
    assert "result" in response
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["tier"] == 0
    assert payload["workspace_name"] == "workspace"
    assert payload["map"] is not None
    assert payload["cards"] is None
    assert "token_estimate" in payload


def test_tools_call_metagit_context_pack_invalid_args_returns_invalid_arguments(
    tmp_path: Path,
) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    missing_tier = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "tools/call",
            "params": {
                "name": "metagit_context_pack",
                "arguments": {},
            },
        }
    )
    assert missing_tier is not None
    assert missing_tier["error"]["code"] == -32602
    assert missing_tier["error"]["data"]["kind"] == "invalid_arguments"

    bad_tier = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 43,
            "method": "tools/call",
            "params": {
                "name": "metagit_context_pack",
                "arguments": {"tier": 9},
            },
        }
    )
    assert bad_tier is not None
    assert bad_tier["error"]["code"] == -32602
    assert bad_tier["error"]["data"]["kind"] == "invalid_arguments"


def test_tools_call_metagit_objective_list(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
                "          sync: true",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    demo_svc = tmp_path / "demo" / "svc"
    demo_svc.mkdir(parents=True)
    from metagit.core.context.models import Objective
    from metagit.core.context.objective_service import ObjectiveService
    from metagit.core.workspace.context_models import utc_now_iso

    stamp = utc_now_iso()
    ObjectiveService(workspace_root=str(tmp_path)).upsert(
        Objective(
            id="mcp-goal",
            title="MCP-listed goal",
            status="pending",
            created_at=stamp,
            updated_at=stamp,
        ),
    )

    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "metagit_objective_list",
                "arguments": {},
            },
        },
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is True
    ids = [item["id"] for item in payload["objectives"]]
    assert "mcp-goal" in ids


def test_tools_call_metagit_objective_edit(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos: []",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    from metagit.core.context.models import Objective
    from metagit.core.context.objective_service import ObjectiveService
    from metagit.core.workspace.context_models import utc_now_iso

    stamp = utc_now_iso()
    ObjectiveService(workspace_root=str(tmp_path)).upsert(
        Objective(
            id="mcp-edit",
            title="Before edit",
            status="pending",
            created_at=stamp,
            updated_at=stamp,
        ),
    )

    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 102,
            "method": "tools/call",
            "params": {
                "name": "metagit_objective_edit",
                "arguments": {
                    "id": "mcp-edit",
                    "status": "in_progress",
                    "acceptance": "Ship MCP parity",
                    "human_notes": "Need API + UI",
                },
            },
        },
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["id"] == "mcp-edit"
    assert payload["status"] == "in_progress"
    assert payload["acceptance"] == "Ship MCP parity"
    assert payload["human_notes"] == "Need API + UI"


def test_tools_list_includes_project_source_sync_when_active(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 200, "method": "tools/list", "params": {}}
    )
    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_project_source_sync" in names


def test_tools_call_project_source_sync_dry_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    from metagit.core.project.source_models import SourceSyncPlan, SourceSyncResult

    monkeypatch.setattr(
        "metagit.core.mcp.services.source_sync.run_source_sync",
        lambda **_: SourceSyncResult(
            ok=True,
            applied=False,
            plan=SourceSyncPlan(discovered_count=0, filtered_count=0),
        ),
    )

    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 201,
            "method": "tools/call",
            "params": {
                "name": "metagit_project_source_sync",
                "arguments": {
                    "project_name": "alpha",
                    "provider": "github",
                    "org": "acme",
                    "mode": "discover",
                },
            },
        }
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is True


def test_tools_list_includes_session_begin_when_active(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 300, "method": "tools/list", "params": {}}
    )
    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_session_begin" in names
    assert "metagit_session_digest" in names
    assert "metagit_objective_edit" in names


def test_tools_call_session_begin_returns_envelope(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos:",
                "        - name: api",
                "          path: alpha/api",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "alpha" / "api").mkdir(parents=True)
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 301,
            "method": "tools/call",
            "params": {
                "name": "metagit_session_begin",
                "arguments": {"max_tokens": 1},
            },
        }
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["schema_version"] == "1.0"
    assert payload["workspace_name"] == "workspace"
    assert payload["pack"]["tier"] == 2


def test_tools_call_session_digest_returns_digest(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    from metagit.core.context.models import Objective
    from metagit.core.context.objective_service import ObjectiveService
    from metagit.core.workspace.context_models import utc_now_iso

    stamp = utc_now_iso()
    ObjectiveService(workspace_root=str(tmp_path)).upsert(
        Objective(
            id="mcp-active",
            title="Active objective",
            status="in_progress",
            created_at=stamp,
            updated_at=stamp,
        ),
    )

    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 302,
            "method": "tools/call",
            "params": {
                "name": "metagit_session_digest",
                "arguments": {},
            },
        }
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["tier"] == 2
    assert payload["active_objective_id"] == "mcp-active"


# --- Handoff MCP tools ---

_HANDOFF_WORKSPACE_YML = "\n".join(
    [
        "name: workspace",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: alpha",
        "      repos: []",
    ]
)


def test_tools_list_includes_handoff_tools(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_HANDOFF_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 400, "method": "tools/list", "params": {}}
    )
    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_handoff_list" in names
    assert "metagit_handoff_create" in names
    assert "metagit_handoff_claim" in names
    assert "metagit_handoff_complete" in names
    assert "metagit_events" in names


def test_tools_call_handoff_create_returns_item(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_HANDOFF_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 401,
            "method": "tools/call",
            "params": {
                "name": "metagit_handoff_create",
                "arguments": {"title": "MCP handoff", "created_by": "tester"},
            },
        }
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["title"] == "MCP handoff"
    assert payload["status"] == "open"
    assert payload["id"]


def test_tools_call_handoff_list_returns_result(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_HANDOFF_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    # Create one first
    runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 402,
            "method": "tools/call",
            "params": {
                "name": "metagit_handoff_create",
                "arguments": {"title": "Listed handoff"},
            },
        }
    )
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 403,
            "method": "tools/call",
            "params": {
                "name": "metagit_handoff_list",
                "arguments": {},
            },
        }
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert len(payload["handoffs"]) == 1
    assert payload["handoffs"][0]["title"] == "Listed handoff"


def test_tools_call_handoff_claim_and_complete(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_HANDOFF_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    created = json.loads(
        runtime._handle_request(
            {
                "jsonrpc": "2.0",
                "id": 410,
                "method": "tools/call",
                "params": {
                    "name": "metagit_handoff_create",
                    "arguments": {"title": "Round trip"},
                },
            }
        )["result"]["content"][0]["text"]
    )
    handoff_id = created["id"]

    claimed = json.loads(
        runtime._handle_request(
            {
                "jsonrpc": "2.0",
                "id": 411,
                "method": "tools/call",
                "params": {
                    "name": "metagit_handoff_claim",
                    "arguments": {"id": handoff_id, "claimed_by": "agentX"},
                },
            }
        )["result"]["content"][0]["text"]
    )
    assert claimed["status"] == "claimed"

    done = json.loads(
        runtime._handle_request(
            {
                "jsonrpc": "2.0",
                "id": 412,
                "method": "tools/call",
                "params": {
                    "name": "metagit_handoff_complete",
                    "arguments": {"id": handoff_id, "actor": "agentX"},
                },
            }
        )["result"]["content"][0]["text"]
    )
    assert done["status"] == "completed"


def test_tools_call_events_returns_result(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_HANDOFF_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    # Seed a handoff so there is at least one event
    runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 420,
            "method": "tools/call",
            "params": {
                "name": "metagit_handoff_create",
                "arguments": {"title": "Event seed"},
            },
        }
    )
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 421,
            "method": "tools/call",
            "params": {
                "name": "metagit_events",
                "arguments": {},
            },
        }
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert payload["schema_version"] == "1.0"
    assert isinstance(payload["events"], list)
    assert len(payload["events"]) >= 1

