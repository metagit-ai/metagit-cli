#!/usr/bin/env python
"""
API models for the metagit detection service.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class DetectionStatus(str, Enum):
    """Detection job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DetectionPriority(str, Enum):
    """Enumeration of detection priority values."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DetectionRequest(BaseModel):
    """Request model for submitting a detection job."""

    repository_url: Optional[HttpUrl] = Field(
        None, description="Git repository URL to analyze"
    )
    priority: int = Field(
        default=0, description="Detection priority (higher = more important)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata for the detection"
    )


class DetectionResponse(BaseModel):
    """Response model for detection job submission."""

    detection_id: str
    status: DetectionStatus
    repository_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime]
    error_message: Optional[str]
    record_id: Optional[str]


class DetectionStatusResponse(BaseModel):
    """Response model for detection job status."""

    detection_id: str
    status: DetectionStatus
    repository_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime]
    error_message: Optional[str]
    record_id: Optional[str]


class SearchRequest(BaseModel):
    """Request model for searching records."""

    query: str = Field(default="", description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=100, description="Page size")


class SearchResponse(BaseModel):
    """Model for search response."""

    total: int = Field(..., description="Total number of results")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Results per page")
    results: List[dict] = Field(..., description="Search results")
    aggregations: Optional[dict] = Field(None, description="Search aggregations")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class HealthResponse(BaseModel):
    """Model for health check response."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")
    opensearch_status: str = Field(..., description="OpenSearch connection status")
    providers_status: dict = Field(..., description="Provider status")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"
