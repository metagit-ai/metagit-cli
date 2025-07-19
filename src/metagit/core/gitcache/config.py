#!/usr/bin/env python
"""
Git cache configuration models.

This module defines the Pydantic models used for configuring
the git cache management system.
"""

from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class CacheType(str, Enum):
    """Enumeration of cache types."""

    GIT = "git"
    LOCAL = "local"


class CacheStatus(str, Enum):
    """Enumeration of cache statuses."""

    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"
    ERROR = "error"


class GitCacheEntry(BaseModel):
    """Model for a single git cache entry."""

    name: str = Field(..., description="Cache entry name/identifier")
    source_url: str = Field(..., description="Source URL or local path")
    cache_type: CacheType = Field(..., description="Type of cache entry")
    cache_path: Path = Field(..., description="Local cache path")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )
    last_accessed: datetime = Field(
        default_factory=datetime.now, description="Last access timestamp"
    )
    size_bytes: Optional[int] = Field(None, description="Cache size in bytes")
    status: CacheStatus = Field(
        default=CacheStatus.FRESH, description="Current cache status"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if status is ERROR"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    # Git-specific tracking fields
    local_commit_hash: Optional[str] = Field(
        None, description="Current local commit hash"
    )
    local_branch: Optional[str] = Field(None, description="Current local branch name")
    remote_commit_hash: Optional[str] = Field(
        None, description="Latest remote commit hash"
    )
    remote_branch: Optional[str] = Field(None, description="Default remote branch name")
    has_upstream_changes: Optional[bool] = Field(
        None, description="Whether upstream has new commits"
    )
    upstream_changes_summary: Optional[str] = Field(
        None, description="Summary of upstream changes"
    )
    last_diff_check: Optional[datetime] = Field(
        None, description="Last time differences were checked"
    )

    @field_validator("cache_path", mode="before")
    @classmethod
    def validate_cache_path(cls, v: Any) -> Path:
        """Convert string to Path object."""
        if isinstance(v, str):
            return Path(v)
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class GitCacheConfig(BaseModel):
    """Configuration model for git cache management."""

    cache_root: Path = Field(
        default=Path("./.metagit/.cache"),
        description="Root directory for git cache storage",
    )
    default_timeout_minutes: int = Field(
        default=60, description="Default cache timeout in minutes"
    )
    max_cache_size_gb: float = Field(
        default=10.0, description="Maximum cache size in GB"
    )
    enable_async: bool = Field(default=True, description="Enable async operations")
    git_config: Dict[str, Any] = Field(
        default_factory=dict, description="Git configuration options"
    )
    provider_config: Optional[Dict[str, Any]] = Field(
        None, description="Provider-specific configuration"
    )
    entries: Dict[str, GitCacheEntry] = Field(
        default_factory=dict, description="Cache entries"
    )

    @field_validator("cache_root", mode="before")
    @classmethod
    def validate_cache_root(cls, v: Any) -> Path:
        """Convert string to Path object and ensure it exists."""
        if isinstance(v, str):
            cache_path = Path(v)
        else:
            cache_path = v

        # Create cache directory if it doesn't exist
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    @field_validator("default_timeout_minutes")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    @field_validator("max_cache_size_gb")
    @classmethod
    def validate_max_size(cls, v: float) -> float:
        """Validate max cache size is positive."""
        if v <= 0:
            raise ValueError("Max cache size must be positive")
        return v

    def get_cache_path(self, name: str) -> Path:
        """Get the cache path for a specific entry."""
        return self.cache_root / name

    def is_entry_stale(self, entry: GitCacheEntry) -> bool:
        """Check if a cache entry is stale based on timeout."""
        timeout_delta = timedelta(minutes=self.default_timeout_minutes)
        return datetime.now() - entry.last_updated > timeout_delta

    def get_cache_size_bytes(self) -> int:
        """Get total cache size in bytes."""
        total_size = 0
        for entry in self.entries.values():
            if entry.cache_path.exists():
                try:
                    total_size += sum(
                        f.stat().st_size
                        for f in entry.cache_path.rglob("*")
                        if f.is_file()
                    )
                except (OSError, PermissionError):
                    continue
        return total_size

    def get_cache_size_gb(self) -> float:
        """Get total cache size in GB."""
        return self.get_cache_size_bytes() / (1024**3)

    def is_cache_full(self) -> bool:
        """Check if cache is at maximum size."""
        return self.get_cache_size_gb() >= self.max_cache_size_gb

    def add_entry(self, entry: GitCacheEntry) -> None:
        """Add a cache entry."""
        self.entries[entry.name] = entry

    def remove_entry(self, name: str) -> bool:
        """Remove a cache entry."""
        if name in self.entries:
            del self.entries[name]
            return True
        return False

    def get_entry(self, name: str) -> Optional[GitCacheEntry]:
        """Get a cache entry by name."""
        return self.entries.get(name)

    def list_entries(self) -> List[GitCacheEntry]:
        """List all cache entries."""
        return list(self.entries.values())

    def clear_entries(self) -> None:
        """Clear all cache entries."""
        self.entries.clear()

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"
