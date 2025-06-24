#!/usr/bin/env python
"""
Config endpoints for the metagit API.
"""

import logging
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from metagit.api.opensearch import OpenSearchService
from metagit.core.config.models import MetagitConfig, MetagitRecord
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


def get_opensearch_service() -> OpenSearchService:
    """Dependency to get OpenSearch service."""
    from metagit.api.app import opensearch_service

    if not opensearch_service:
        raise HTTPException(status_code=503, detail="OpenSearch service not available")
    return opensearch_service


@router.get("/{git_url:path}")
async def get_config_by_url(
    git_url: str,
    opensearch: OpenSearchService = Depends(get_opensearch_service),
):
    """Get MetagitConfig from a MetagitRecord by git URL."""
    try:
        logger.info(f"Received git_url parameter: {git_url}")

        # URL decode the git URL and normalize it
        decoded_url = urllib.parse.unquote(git_url)
        logger.info(f"Decoded URL: {decoded_url}")

        normalized_url = normalize_git_url(decoded_url)
        logger.info(f"Normalized URL: {normalized_url}")

        # Search for the record by URL
        result = await opensearch.search_records(
            query="",  # Empty query to match all
            filters={"url": normalized_url},
            page=1,
            size=1,
        )

        if isinstance(result, Exception):
            raise HTTPException(status_code=500, detail=f"Search failed: {result}")

        if result["total"] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No MetagitRecord found for URL: {normalized_url}",
            )

        # Get the first (and should be only) result
        record_data = result["results"][0]
        record_id = record_data.pop("_id", None)

        # Create MetagitRecord from the data
        record = MetagitRecord(**record_data)

        # Convert to MetagitConfig (remove detection-specific fields)
        config_data = record.model_dump()

        # Remove detection-specific fields that are not part of MetagitConfig
        detection_fields = [
            "branch",
            "checksum",
            "last_updated",
            "branches",
            "metrics",
            "metadata",
            "detection_timestamp",
            "detection_source",
            "detection_version",
        ]
        for field in detection_fields:
            config_data.pop(field, None)

        # Create MetagitConfig
        config = MetagitConfig(**config_data)

        response_data = {
            "url": normalized_url,
            "record_id": record_id,
            "config": config.model_dump(),
            "detection_info": {
                "detection_timestamp": record.detection_timestamp,
                "detection_source": record.detection_source,
                "detection_version": record.detection_version,
                "branch": record.branch,
                "checksum": record.checksum,
            },
        }

        logger.info(f"Returning response with URL: {response_data['url']}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving config for URL {git_url}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
