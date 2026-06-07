#!/usr/bin/env python
"""Pydantic models for Metagit release/version checks."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

InstallMethod = Literal["uv_tool", "pip", "editable", "unknown"]


class LatestReleaseInfo(BaseModel):
    """Published release metadata from GitHub or PyPI."""

    version: str = Field(description="Normalized release version (no leading v)")
    tag_name: str | None = Field(
        default=None, description="Git tag when source is github"
    )
    name: str | None = Field(default=None, description="Human-readable release title")
    published_at: datetime | None = Field(
        default=None, description="UTC publish timestamp when known"
    )
    html_url: str | None = Field(default=None, description="Release page URL")
    body: str | None = Field(default=None, description="Release notes markdown")
    source: Literal["github", "pypi"] = Field(description="Where metadata came from")


class VersionCheckResult(BaseModel):
    """Installed vs latest release comparison for agents and humans."""

    installed_version: str
    latest_release: LatestReleaseInfo | None = None
    pypi_version: str | None = Field(
        default=None, description="Latest version on PyPI (metagit-cli)"
    )
    update_available: bool = Field(
        default=False,
        description="True when a published release is newer than installed",
    )
    is_latest: bool = Field(
        default=True,
        description="True when installed matches or exceeds latest published",
    )
    install_command: str = Field(
        default="uv tool install -U metagit-cli",
        description="Suggested upgrade command for uv tool installs",
    )
    fetch_errors: list[str] = Field(
        default_factory=list,
        description="Non-fatal errors while contacting GitHub or PyPI",
    )


class VersionUpgradeResult(BaseModel):
    """Self-update attempt or dry-run plan."""

    ok: bool = Field(description="Whether the operation completed without error")
    applied: bool = Field(
        default=False,
        description="True when the upgrade command was executed",
    )
    dry_run: bool = Field(
        default=True,
        description="True when only reporting the planned upgrade command",
    )
    skipped: bool = Field(
        default=False,
        description="True when already on the latest published release",
    )
    install_method: InstallMethod = Field(
        description="Detected install channel for the running package"
    )
    command: str | None = Field(
        default=None,
        description="Upgrade command that was or would be executed",
    )
    check: VersionCheckResult
    stdout: str | None = Field(default=None, description="Upgrade subprocess stdout")
    stderr: str | None = Field(default=None, description="Upgrade subprocess stderr")
    exit_code: int | None = Field(
        default=None,
        description="Upgrade subprocess exit code when applied",
    )
    error: str | None = Field(
        default=None,
        description="Failure reason when ok is false",
    )
    message: str | None = Field(
        default=None,
        description="Human-readable outcome summary",
    )
