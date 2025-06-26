#!/usr/bin/env python

from typing import Any, Dict, Optional

from pydantic import Field

from metagit.core.appconfig.models import AppConfig


class TenantConfig(AppConfig):
    """Per-tenant application configuration."""

    tenant_id: str = Field(..., description="Tenant identifier")
    tenant_name: str = Field(default="", description="Tenant display name")
    tenant_description: str = Field(default="", description="Tenant description")

    # Detection settings for this tenant
    tenant_max_concurrent_jobs: int = Field(
        default=5, description="Maximum concurrent detection jobs for this tenant"
    )
    tenant_detection_timeout: int = Field(
        default=300, description="Detection timeout in seconds for this tenant"
    )

    # Custom settings for this tenant
    tenant_settings: Dict[str, Any] = Field(
        default_factory=dict, description="Custom tenant-specific settings"
    )

    # Metadata
    tenant_created_at: Optional[str] = Field(
        None, description="Tenant creation timestamp"
    )
    tenant_updated_at: Optional[str] = Field(
        None, description="Tenant last update timestamp"
    )
    tenant_is_active: bool = Field(default=True, description="Whether tenant is active")

    class Config:
        """Pydantic configuration."""

        extra = "allow"
