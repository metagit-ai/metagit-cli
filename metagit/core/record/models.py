#!/usr/bin/env python
"""
Pydantic models for metagit records.
"""

from datetime import datetime
from typing import List, Optional

import yaml
from pydantic import Field

from metagit.core.config.models import (
    Branch,
    Language,
    MetagitConfig,
    Metrics,
    ProjectDomain,
    RepoMetadata,
)


class MetagitRecord(MetagitConfig):
    """
    Extended model for metagit records that includes detection-specific data suitable for OpenSearch.

    This class inherits from MetagitConfig and adds detection-specific attributes.
    """

    # Detection-specific attributes
    branch: Optional[str] = Field(None, description="Current branch")
    checksum: Optional[str] = Field(None, description="Branch checksum")
    last_updated: Optional[datetime] = Field(None, description="Last updated timestamp")
    branches: Optional[List[Branch]] = Field(None, description="Release branches")
    metrics: Optional[Metrics] = Field(None, description="Repository metrics")
    metadata: Optional[RepoMetadata] = Field(None, description="Repository metadata")

    # Language and project type detection
    language: Optional[Language] = Field(
        None, description="Detected language information"
    )
    language_version: Optional[str] = Field(
        None, description="Primary language version"
    )
    domain: Optional[ProjectDomain] = Field(None, description="Project domain")

    # Additional detection fields
    detection_timestamp: Optional[datetime] = Field(
        None, description="When this record was last detected/updated"
    )
    detection_source: Optional[str] = Field(
        None, description="Source of the detection (e.g., 'github', 'gitlab', 'local')"
    )
    detection_version: Optional[str] = Field(
        None, description="Version of the detection system used"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        extra = "forbid"

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "MetagitRecord":
        """Create a MetagitRecord from a YAML string."""
        return cls.model_validate_yaml(yaml_str)

    @classmethod
    def from_json(cls, json_str: str) -> "MetagitRecord":
        """Create a MetagitRecord from a JSON string."""
        return cls.model_validate_json(json_str)

    @classmethod
    def from_dict(cls, data: dict) -> "MetagitRecord":
        """Create a MetagitRecord from a dictionary."""
        return cls.model_validate(data)

    def to_yaml(self) -> str:
        """Convert a MetagitRecord to a YAML string."""
        return yaml.safe_dump(self.model_dump(exclude_none=True, exclude_defaults=True))

    @classmethod
    def to_json(self) -> str:
        """Convert a MetagitRecord to a JSON string."""
        return self.model_dump_json(exclude_defaults=True, exclude_none=True)
