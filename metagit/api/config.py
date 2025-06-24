#!/usr/bin/env python
"""
Configuration settings for the metagit detection API.
"""

import os
from typing import Optional

from pydantic import BaseModel, Field


class OpenSearchConfig(BaseModel):
    """OpenSearch configuration."""

    host: str = Field(default="localhost", description="OpenSearch host")
    port: int = Field(default=9200, description="OpenSearch port")
    index_name: str = Field(default="metagit-records", description="Index name")
    username: Optional[str] = Field(default=None, description="OpenSearch username")
    password: Optional[str] = Field(default=None, description="OpenSearch password")
    use_ssl: bool = Field(default=True, description="Use SSL")
    verify_certs: bool = Field(default=True, description="Verify SSL certificates")
    ssl_show_warn: bool = Field(default=False, description="Show SSL warnings")


class APIConfig(BaseModel):
    """API configuration."""

    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Debug mode")
    max_concurrent_jobs: int = Field(
        default=5, description="Max concurrent detection jobs"
    )
    job_cleanup_hours: int = Field(
        default=24, description="Hours to keep completed jobs"
    )


class DetectionConfig(BaseModel):
    """Detection configuration."""

    temp_dir: Optional[str] = Field(
        default=None, description="Temporary directory for cloning"
    )
    max_clone_size_mb: int = Field(
        default=100, description="Maximum repository size to clone (MB)"
    )
    timeout_seconds: int = Field(
        default=300, description="Detection timeout in seconds"
    )


class Config(BaseModel):
    """Main configuration."""

    opensearch: OpenSearchConfig = Field(default_factory=OpenSearchConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)

    @classmethod
    def from_environment(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            opensearch=OpenSearchConfig(
                host=os.getenv("OPENSEARCH_HOST", "localhost"),
                port=int(os.getenv("OPENSEARCH_PORT", "9200")),
                index_name=os.getenv("OPENSEARCH_INDEX", "metagit-records"),
                username=os.getenv("OPENSEARCH_USERNAME"),
                password=os.getenv("OPENSEARCH_PASSWORD"),
                use_ssl=os.getenv("OPENSEARCH_USE_SSL", "true").lower() == "true",
                verify_certs=os.getenv("OPENSEARCH_VERIFY_CERTS", "true").lower()
                == "true",
                ssl_show_warn=os.getenv("OPENSEARCH_SSL_SHOW_WARN", "false").lower()
                == "true",
            ),
            api=APIConfig(
                host=os.getenv("API_HOST", "0.0.0.0"),
                port=int(os.getenv("API_PORT", "8000")),
                debug=os.getenv("API_DEBUG", "false").lower() == "true",
                max_concurrent_jobs=int(os.getenv("MAX_CONCURRENT_JOBS", "5")),
                job_cleanup_hours=int(os.getenv("JOB_CLEANUP_HOURS", "24")),
            ),
            detection=DetectionConfig(
                temp_dir=os.getenv("DETECTION_TEMP_DIR"),
                max_clone_size_mb=int(os.getenv("MAX_CLONE_SIZE_MB", "100")),
                timeout_seconds=int(os.getenv("DETECTION_TIMEOUT_SECONDS", "300")),
            ),
        )


# Global config instance
config = Config.from_environment()
