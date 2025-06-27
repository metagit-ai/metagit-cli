#!/usr/bin/env python
"""
Dependency injection utilities for the metagit API.
"""

import os

from fastapi import Depends, Request

from metagit.api.detection import DetectionService
from metagit.api.detection_tenant import TenantAwareDetectionService
from metagit.api.opensearch import OpenSearchService
from metagit.api.opensearch_tenant import TenantAwareOpenSearchService
from metagit.core.appconfig.models import AppConfig


def get_app_config() -> AppConfig:
    """Get application configuration."""
    # This would typically load from a global config or cache
    # For now, we'll return a default config
    return AppConfig()


def get_current_tenant(request: Request) -> str:
    """Get current tenant from request state."""
    return getattr(request.state, "tenant_id", "default")


def get_tenant_aware_opensearch_service(
    app_config: AppConfig = Depends(get_app_config),  # noqa: B008
) -> OpenSearchService:
    """Get appropriate OpenSearch service based on tenant configuration."""
    # Import here to avoid circular imports
    import os

    # Configure OpenSearch connection
    opensearch_host = os.getenv("OPENSEARCH_HOST", "localhost")
    opensearch_port = int(os.getenv("OPENSEARCH_PORT", "9200"))
    opensearch_hosts = [{"host": opensearch_host, "port": opensearch_port}]

    # Return appropriate service based on tenant config
    if app_config.tenant.enabled:
        return TenantAwareOpenSearchService(
            hosts=opensearch_hosts,
            index_name=os.getenv("OPENSEARCH_INDEX", "metagit-records"),
            username=os.getenv("OPENSEARCH_USERNAME"),
            password=os.getenv("OPENSEARCH_PASSWORD"),
            use_ssl=os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true",
            verify_certs=os.getenv("OPENSEARCH_VERIFY_CERTS", "false").lower()
            == "true",
        )
    else:
        return OpenSearchService(
            hosts=opensearch_hosts,
            index_name=os.getenv("OPENSEARCH_INDEX", "metagit-records"),
            username=os.getenv("OPENSEARCH_USERNAME"),
            password=os.getenv("OPENSEARCH_PASSWORD"),
            use_ssl=os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true",
            verify_certs=os.getenv("OPENSEARCH_VERIFY_CERTS", "false").lower()
            == "true",
        )


def get_tenant_aware_detection_service(
    opensearch_service: OpenSearchService = Depends(  # noqa: B008
        get_tenant_aware_opensearch_service
    ),
    app_config: AppConfig = Depends(get_app_config),  # noqa: B008
) -> DetectionService:
    """Get appropriate detection service based on tenant configuration."""

    max_concurrent_jobs = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))

    # Return appropriate service based on tenant config
    if app_config.tenant.enabled:
        return TenantAwareDetectionService(
            opensearch_service=opensearch_service,
            max_concurrent_jobs=max_concurrent_jobs,
        )
    else:
        from metagit.api.detection import DetectionService

        return DetectionService(
            opensearch_service=opensearch_service,
            max_concurrent_jobs=max_concurrent_jobs,
        )


# Convenience functions for backward compatibility
def get_opensearch_service() -> OpenSearchService:
    """Get OpenSearch service (backward compatibility)."""
    return get_tenant_aware_opensearch_service()


def get_detection_service() -> DetectionService:
    """Get detection service (backward compatibility)."""
    return get_tenant_aware_detection_service()
