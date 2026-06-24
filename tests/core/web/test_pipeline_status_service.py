#!/usr/bin/env python
"""Unit tests for pipeline status aggregation service."""

from datetime import datetime, timezone

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.web.pipeline_status_service import (
    PipelineQueryOptions,
    PipelineStatusService,
    _duration_seconds,
)


class _FakeIndexService:
    def __init__(self, rows):
        self._rows = rows

    def build_index(self, **kwargs):  # noqa: ANN003
        _ = kwargs
        return list(self._rows)


def _minimal_config() -> MetagitConfig:
    return MetagitConfig(
        name="workspace",
        kind="application",
        workspace={
            "projects": [
                {
                    "name": "platform",
                    "repos": [
                        {
                            "name": "metagit-cli",
                            "url": "https://github.com/metagit-ai/metagit-cli.git",
                        }
                    ],
                }
            ]
        },
    )


def test_provider_diagnostics_uses_env_fallback(monkeypatch) -> None:
    monkeypatch.setenv("METAGIT_GITHUB_API_TOKEN", "gh_env_token")
    monkeypatch.delenv("METAGIT_GITLAB_API_TOKEN", raising=False)
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    monkeypatch.delenv("GLAB_TOKEN", raising=False)

    service = PipelineStatusService(index_service=_FakeIndexService([]))
    payload = service.provider_diagnostics(AppConfig())

    assert payload["ok"] is True
    by_provider = {item["provider"]: item for item in payload["providers"]}
    assert by_provider["github"]["available"] is True
    assert by_provider["github"]["auth_source"] == "env.METAGIT_GITHUB_API_TOKEN"
    assert by_provider["gitlab"]["available"] is False
    assert by_provider["gitlab"]["auth_source"] == "none"


def test_pipeline_status_filters_by_provider_and_unsynced() -> None:
    rows = [
        {
            "project_name": "platform",
            "repo_name": "metagit-cli",
            "url": "https://github.com/metagit-ai/metagit-cli.git",
            "status": "synced",
            "repo_path": "/tmp/metagit-cli",
        },
        {
            "project_name": "platform",
            "repo_name": "platform-infra",
            "url": "https://gitlab.com/metagit-ai/platform-infra.git",
            "status": "configured_missing",
            "repo_path": "/tmp/platform-infra",
        },
        {
            "project_name": "misc",
            "repo_name": "other",
            "url": "https://example.com/other.git",
            "status": "synced",
            "repo_path": "/tmp/other",
        },
    ]
    service = PipelineStatusService(index_service=_FakeIndexService(rows))
    service._resolve_github_token = lambda app_config: (None, "none")  # type: ignore[method-assign]
    service._resolve_gitlab_token = lambda app_config: (None, "none")  # type: ignore[method-assign]

    result = service.pipeline_status(
        config=_minimal_config(),
        app_config=AppConfig(),
        workspace_root="/tmp",
        definition_root="/tmp",
        options=PipelineQueryOptions(provider="github", include_unsynced=False),
    )

    assert result["ok"] is True
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["provider"] == "github"
    assert row["local_status"] == "synced"
    assert row["pipeline_status"] == "unknown"
    assert row["reason"] == "no GitHub auth context available"
    assert result["summary"]["total"] == 1
    assert result["summary"]["unknown"] == 1


def test_pipeline_status_filters_by_repo_selector() -> None:
    rows = [
        {
            "project_name": "platform",
            "repo_name": "metagit-cli",
            "url": "https://example.com/metagit-cli.git",
            "status": "synced",
            "repo_path": "/tmp/metagit-cli",
        },
        {
            "project_name": "platform",
            "repo_name": "platform-infra",
            "url": "https://example.com/platform-infra.git",
            "status": "synced",
            "repo_path": "/tmp/platform-infra",
        },
    ]
    service = PipelineStatusService(index_service=_FakeIndexService(rows))

    result = service.pipeline_status(
        config=_minimal_config(),
        app_config=AppConfig(),
        workspace_root="/tmp",
        definition_root="/tmp",
        options=PipelineQueryOptions(repos=("platform/metagit-cli",)),
    )

    assert len(result["rows"]) == 1
    assert result["rows"][0]["repo_name"] == "metagit-cli"


def test_status_normalization_helpers() -> None:
    assert (
        PipelineStatusService._normalize_github_status("completed", "success")
        == "passed"
    )
    assert (
        PipelineStatusService._normalize_github_status("in_progress", None)
        == "running"
    )
    assert PipelineStatusService._normalize_gitlab_status("failed") == "failed"
    assert PipelineStatusService._normalize_gitlab_status("manual") == "pending"


def test_duration_seconds_returns_non_negative() -> None:
    start = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat()
    end = datetime(2026, 1, 1, 12, 1, 5, tzinfo=timezone.utc).isoformat()
    assert _duration_seconds(start, end) == 65
    assert _duration_seconds(end, start) is None
