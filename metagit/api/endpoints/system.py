#!/usr/bin/env python
"""
System endpoints for the metagit API.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from metagit.api.models import HealthResponse
from metagit.api.opensearch import OpenSearchService
from metagit.core.providers import registry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


def get_opensearch_service() -> OpenSearchService:
    """Dependency to get OpenSearch service."""
    from metagit.api.app import opensearch_service

    if not opensearch_service:
        raise HTTPException(status_code=503, detail="OpenSearch service not available")
    return opensearch_service


def get_detection_service():
    """Dependency to get detection service."""
    from metagit.api.app import detection_service

    if not detection_service:
        raise HTTPException(status_code=503, detail="Detection service not available")
    return detection_service


@router.get("/", response_model=dict)
async def root():
    """Root endpoint."""
    return {
        "message": "Metagit Detection API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health", response_model=HealthResponse)
async def health_check(
    opensearch: OpenSearchService = Depends(get_opensearch_service),
    detection=Depends(get_detection_service),
):
    """Health check endpoint."""
    # Check OpenSearch health
    opensearch_health = await opensearch.get_health()
    opensearch_status = (
        "healthy" if opensearch_health["status"] == "healthy" else "unhealthy"
    )

    # Check provider status
    providers = registry.get_all_providers()
    providers_status = {}
    for provider in providers:
        providers_status[provider.get_name()] = (
            "available" if provider.is_available() else "unavailable"
        )

    return HealthResponse(
        status="healthy" if opensearch_status == "healthy" else "unhealthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        opensearch_status=opensearch_status,
        providers_status=providers_status,
    )


@router.get("/providers")
async def list_providers():
    """List available providers."""
    providers = registry.get_all_providers()
    return {
        "providers": [
            {
                "name": provider.get_name(),
                "available": provider.is_available(),
                "supported_urls": provider.get_supported_url_patterns(),
            }
            for provider in providers
        ]
    }


@router.get("/index-info")
async def get_index_info(
    opensearch: OpenSearchService = Depends(get_opensearch_service),
):
    """Get information about the search index."""
    try:
        # Get index stats
        stats = await opensearch.get_index_stats()

        # Get index mapping
        mapping = await opensearch.get_index_mapping()

        # Get index settings
        settings = await opensearch.get_index_settings()

        # Get index health
        health = await opensearch.get_health()

        return {
            "index_name": opensearch.index_name,
            "health": health,
            "stats": stats,
            "mapping": mapping,
            "settings": settings,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting index info: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get index information: {str(e)}"
        )
