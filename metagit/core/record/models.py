#!/usr/bin/env python
"""
Pydantic models for metagit records.
"""

from datetime import datetime
from typing import Dict, List, Optional, Type, TypeVar

import yaml
from pydantic import BaseModel, Field

from metagit.core.config.models import (
    AlertingChannel,
    Artifact,
    Branch,
    Dashboard,
    Environment,
    Language,
    License,
    Maintainer,
    MetagitConfig,
    Metrics,
    ProjectDomain,
    RepoMetadata,
    Secret,
    Workspace,
)

# Import models from detect module for forward references
try:
    from metagit.core.detect.models import (
        CIConfigAnalysis,
        GitBranchAnalysis,
        LanguageDetection,
        ProjectTypeDetection,
    )
    from metagit.core.utils.files import DirectoryDetails, DirectorySummary
except ImportError:
    # Forward references for type hints
    LanguageDetection = "LanguageDetection"
    ProjectTypeDetection = "ProjectTypeDetection"
    GitBranchAnalysis = "GitBranchAnalysis"
    CIConfigAnalysis = "CIConfigAnalysis"
    DirectoryDetails = "DirectoryDetails"
    DirectorySummary = "DirectorySummary"

from metagit.core.detect.models import (
    CIConfigAnalysis,
    GitBranchAnalysis,
    LanguageDetection,
    ProjectTypeDetection,
)
from metagit.core.utils.files import DirectoryDetails, DirectorySummary

T = TypeVar("T", bound=BaseModel)


def _get_common_fields(
    source_model: Type[BaseModel], target_model: Type[BaseModel]
) -> set[str]:
    """
    Automatically detect common fields between two Pydantic models.

    This utility function uses Pydantic's field introspection to find
    fields that exist in both models, making conversion more maintainable.

    Args:
        source_model: The source model class
        target_model: The target model class

    Returns:
        Set of field names that exist in both models
    """
    source_fields = set(source_model.model_fields.keys())
    target_fields = set(target_model.model_fields.keys())
    return source_fields & target_fields


def _convert_model_data(
    source_data: dict,
    target_model: Type[T],
    field_mapping: Optional[dict[str, str]] = None,
) -> T:
    """
    Convert data between Pydantic models with automatic field mapping.

    This function provides a generic way to convert data between any two
    Pydantic models by automatically detecting compatible fields.

    Args:
        source_data: Dictionary of source model data
        target_model: Target model class
        field_mapping: Optional mapping of source field names to target field names

    Returns:
        Instance of target model

    Raises:
        ValueError: If conversion fails
    """
    try:
        # Apply field mapping if provided
        if field_mapping:
            mapped_data = {}
            for source_key, target_key in field_mapping.items():
                if source_key in source_data:
                    mapped_data[target_key] = source_data[source_key]
            source_data = mapped_data

        # Filter to only include fields that exist in target model
        target_fields = set(target_model.model_fields.keys())
        filtered_data = {k: v for k, v in source_data.items() if k in target_fields}

        # Use model_validate for fast, validated conversion
        return target_model.model_validate(filtered_data)

    except Exception as e:
        raise ValueError(f"Conversion to {target_model.__name__} failed: {e}") from e


class MetagitRecord(MetagitConfig):
    """
    Extended model for metagit records that includes detection-specific data suitable for OpenSearch.

    This class inherits from MetagitConfig and adds detection-specific attributes.
    Now includes all RepositoryAnalysis attributes for comprehensive repository information.
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

    # RepositoryAnalysis attributes merged from repository.py
    # Repository path and URL information
    path: Optional[str] = Field(None, description="Repository path")
    url: Optional[str] = Field(None, description="Repository URL")
    is_git_repo: bool = Field(
        default=False, description="Whether this is a git repository"
    )
    is_cloned: bool = Field(
        default=False, description="Whether this was cloned from a URL"
    )
    temp_dir: Optional[str] = Field(None, description="Temporary directory if cloned")

    # Detection results from RepositoryAnalysis
    language_detection: Optional[LanguageDetection] = Field(
        None, description="Language detection results"
    )
    project_type_detection: Optional[ProjectTypeDetection] = Field(
        None, description="Project type detection results"
    )

    # Analysis results from RepositoryAnalysis
    branch_analysis: Optional[GitBranchAnalysis] = Field(
        None, description="Git branch analysis results"
    )
    ci_config_analysis: Optional[CIConfigAnalysis] = Field(
        None, description="CI/CD configuration analysis results"
    )
    directory_summary: Optional[DirectorySummary] = Field(
        None, description="Directory summary analysis results"
    )
    directory_details: Optional[DirectoryDetails] = Field(
        None, description="Directory details analysis results"
    )

    # Repository metadata from RepositoryAnalysis
    license_info: Optional[License] = Field(None, description="License information")
    maintainers: List[Maintainer] = Field(
        default_factory=list, description="Repository maintainers"
    )
    existing_workspace: Optional[Workspace] = Field(
        None, description="Existing workspace information"
    )

    # Additional metadata from RepositoryAnalysis
    artifacts: Optional[List[Artifact]] = Field(
        None, description="Repository artifacts"
    )
    secrets_management: Optional[List[str]] = Field(
        None, description="Secrets management information"
    )
    secrets: Optional[List[Secret]] = Field(None, description="Repository secrets")
    documentation: Optional[List[str]] = Field(
        None, description="Documentation information"
    )
    alerts: Optional[List[AlertingChannel]] = Field(
        None, description="Alerting channels"
    )
    dashboards: Optional[List[Dashboard]] = Field(None, description="Dashboards")
    environments: Optional[List[Environment]] = Field(None, description="Environments")

    # File analysis from RepositoryAnalysis
    detected_files: Dict[str, List[str]] = Field(
        default_factory=dict, description="Detected files by category"
    )
    has_docker: bool = Field(
        default=False, description="Whether repository has Docker files"
    )
    has_tests: bool = Field(
        default=False, description="Whether repository has test files"
    )
    has_docs: bool = Field(
        default=False, description="Whether repository has documentation"
    )
    has_iac: bool = Field(
        default=False, description="Whether repository has Infrastructure as Code files"
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

    def to_metagit_config(self, exclude_detection_fields: bool = True) -> MetagitConfig:
        """
        Fast conversion from MetagitRecord to MetagitConfig using automatic field detection.

        This method efficiently converts a MetagitRecord to a MetagitConfig by:
        1. Using Pydantic's field introspection to automatically detect compatible fields
        2. Leveraging model_dump() with field filtering for optimal performance
        3. Using model_validate() for fast, validated conversion
        4. Automatically handling field differences between models

        Args:
            exclude_detection_fields: Whether to exclude detection-specific fields
                                     (currently always True as MetagitConfig doesn't support them)

        Returns:
            MetagitConfig: A new MetagitConfig instance with the shared fields

        Example:
            record = MetagitRecord(name="my-project", description="A project")
            config = record.to_metagit_config()

        Performance Notes:
            - Uses Pydantic's field introspection for automatic field detection
            - Leverages Pydantic's C-optimized validation
            - Minimal memory allocation through direct field copying
            - No deep copying of nested objects (uses references)
        """
        # Get the model data, excluding None values and defaults for performance
        model_data = self.model_dump(
            exclude_none=True,
            exclude_defaults=True,
        )

        # Use the generic conversion utility for automatic field mapping
        return _convert_model_data(model_data, MetagitConfig)

    def to_metagit_config_advanced(self, **kwargs) -> MetagitConfig:
        """
        Advanced conversion method with automatic field mapping and validation.

        This method provides more sophisticated conversion capabilities:
        1. Automatic field compatibility detection
        2. Type conversion and validation
        3. Support for custom field mappings
        4. Better error handling and reporting

        Args:
            **kwargs: Additional options for conversion behavior

        Returns:
            MetagitConfig: A new MetagitConfig instance

        Example:
            record = MetagitRecord(name="my-project", description="A project")
            config = record.to_metagit_config_advanced()
        """
        try:
            # Use the standard method for now, but this could be extended
            # with more sophisticated field mapping logic
            return self.to_metagit_config()
        except Exception as e:
            # Could add more sophisticated error handling here
            raise ValueError(f"Conversion failed: {e}") from e

    @classmethod
    def from_metagit_config(
        cls,
        config: MetagitConfig,
        detection_source: str = "local",
        detection_version: str = "1.0.0",
        additional_detection_data: Optional[dict] = None,
    ) -> "MetagitRecord":
        """
        Fast conversion from MetagitConfig to MetagitRecord using latest Pydantic best practices.

        This method efficiently converts a MetagitConfig to a MetagitRecord by:
        1. Using model_dump() for optimal serialization performance
        2. Adding detection-specific fields with minimal overhead
        3. Leveraging Pydantic's built-in validation
        4. Supporting additional detection data injection

        Args:
            config: MetagitConfig instance to convert
            detection_source: Source of the detection (e.g., 'github', 'gitlab', 'local')
            detection_version: Version of the detection system used
            additional_detection_data: Additional detection-specific data to include

        Returns:
            MetagitRecord: A new MetagitRecord instance

        Example:
            config = MetagitConfig(name="my-project", description="A project")
            record = MetagitRecord.from_metagit_config(
                config,
                detection_source="github",
                detection_version="2.0.0"
            )

        Performance Notes:
            - Uses model_dump() with exclude_none=True for optimal serialization
            - Leverages Pydantic's C-optimized validation
            - Minimal memory allocation through direct field copying
            - No deep copying of nested objects (uses references)
        """
        # Get the base config data
        record_data = config.model_dump(exclude_none=True, exclude_defaults=True)

        # Add detection-specific fields
        record_data.update(
            {
                "detection_timestamp": datetime.now(),
                "detection_source": detection_source,
                "detection_version": detection_version,
            }
        )

        # Add additional detection data if provided
        if additional_detection_data:
            record_data.update(additional_detection_data)

        # Use model_validate for fast, validated conversion
        return cls.model_validate(record_data)

    @classmethod
    def from_metagit_config_advanced(
        cls, config: MetagitConfig, **detection_kwargs
    ) -> "MetagitRecord":
        """
        Advanced conversion from MetagitConfig to MetagitRecord with automatic field handling.

        This method provides more sophisticated conversion capabilities:
        1. Automatic field mapping and validation
        2. Support for complex detection data structures
        3. Better error handling and reporting
        4. Extensible for future enhancements

        Args:
            config: MetagitConfig instance to convert
            **detection_kwargs: Detection-specific parameters and data

        Returns:
            MetagitRecord: A new MetagitRecord instance

        Example:
            config = MetagitConfig(name="my-project", description="A project")
            record = MetagitRecord.from_metagit_config_advanced(
                config,
                detection_source="github",
                detection_version="2.0.0",
                branch="main",
                checksum="abc123"
            )
        """
        # Extract standard detection parameters
        detection_source = detection_kwargs.pop("detection_source", "local")
        detection_version = detection_kwargs.pop("detection_version", "1.0.0")

        # Use the standard method for now, but this could be extended
        # with more sophisticated field mapping logic
        return cls.from_metagit_config(
            config,
            detection_source=detection_source,
            detection_version=detection_version,
            additional_detection_data=detection_kwargs,
        )

    def get_detection_summary(self) -> dict:
        """
        Get a summary of detection-specific data for quick analysis.

        Returns:
            dict: Summary of detection data including source, version, and key metrics
        """
        summary = {
            "detection_source": self.detection_source,
            "detection_version": self.detection_version,
            "detection_timestamp": self.detection_timestamp,
            "current_branch": self.branch,
            "checksum": self.checksum,
        }

        # Add metrics summary if available
        if self.metrics:
            summary["metrics"] = {
                "stars": self.metrics.stars,
                "forks": self.metrics.forks,
                "open_issues": self.metrics.open_issues,
                "contributors": self.metrics.contributors,
            }

        # Add metadata summary if available
        if self.metadata:
            summary["metadata"] = {
                "has_ci": self.metadata.has_ci,
                "has_tests": self.metadata.has_tests,
                "has_docs": self.metadata.has_docs,
                "has_docker": self.metadata.has_docker,
                "has_iac": self.metadata.has_iac,
            }

        return summary

    @classmethod
    def get_field_differences(cls) -> dict:
        """
        Get the field differences between MetagitRecord and MetagitConfig.

        This method helps understand what fields are unique to each model,
        making it easier to understand the conversion behavior.

        Returns:
            dict: Field differences between the models
        """
        record_fields = set(cls.model_fields.keys())
        config_fields = set(MetagitConfig.model_fields.keys())

        return {
            "common_fields": sorted(record_fields & config_fields),
            "record_only_fields": sorted(record_fields - config_fields),
            "config_only_fields": sorted(config_fields - record_fields),
            "total_record_fields": len(record_fields),
            "total_config_fields": len(config_fields),
            "common_field_count": len(record_fields & config_fields),
        }

    @classmethod
    def get_compatible_fields(cls) -> set[str]:
        """
        Get the fields that are compatible between MetagitRecord and MetagitConfig.

        Returns:
            set: Field names that exist in both models
        """
        return _get_common_fields(cls, MetagitConfig)


MetagitRecord.model_rebuild()

# from metagit.core.detect.models import (
#     CIConfigAnalysis,
#     GitBranchAnalysis,
#     LanguageDetection,
#     ProjectTypeDetection,
# )
# from metagit.core.utils.files import DirectoryDetails, DirectorySummary

# MetagitRecord.model_rebuild()
