#!/usr/bin/env python
"""
Detection endpoints for the metagit API.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from metagit.api.dependencies import (
    get_current_tenant,
    get_tenant_aware_detection_service,
)
from metagit.api.models import (
    DetectionRequest,
    DetectionResponse,
    DetectionStatus,
    DetectionStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detect", tags=["detection"])


@router.post("/submit", response_model=DetectionResponse)
async def submit_detection(
    request: DetectionRequest,
    current_tenant: str = Depends(get_current_tenant),
    detection_service=Depends(get_tenant_aware_detection_service),
) -> DetectionResponse:
    """Submit a new detection job with tenant context."""
    try:
        if not request.repository_url:
            raise HTTPException(status_code=400, detail="Repository URL is required")

        # Use tenant from request if provided, otherwise use current tenant
        tenant_id = request.tenant_id or current_tenant

        detection_id = await detection_service.submit_detection(
            repository_url=str(request.repository_url),
            tenant_id=tenant_id,
            priority=request.priority,
            metadata=request.metadata,
        )

        if isinstance(detection_id, Exception):
            raise HTTPException(
                status_code=500, detail=f"Failed to submit detection: {detection_id}"
            )

        # Get detection status
        status_result = await detection_service.get_detection_status(
            detection_id, tenant_id
        )
        if isinstance(status_result, Exception):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get detection status: {status_result}",
            )

        return DetectionResponse(
            detection_id=status_result["detection_id"],
            status=status_result["status"],
            repository_url=status_result["repository_url"],
            created_at=status_result["created_at"],
            updated_at=status_result["updated_at"],
            estimated_completion=status_result.get("estimated_completion"),
            error_message=status_result.get("error_message"),
            record_id=status_result.get("record_id"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_detection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{detection_id}/status", response_model=DetectionStatusResponse)
async def get_detection_status(
    detection_id: str,
    current_tenant: str = Depends(get_current_tenant),
    detection_service=Depends(get_tenant_aware_detection_service),
) -> DetectionStatusResponse:
    """Get the status of a detection job with tenant verification."""
    try:
        status_result = await detection_service.get_detection_status(
            detection_id, current_tenant
        )

        if isinstance(status_result, Exception):
            raise HTTPException(
                status_code=404,
                detail=f"Detection job {detection_id} not found or access denied",
            )

        return DetectionStatusResponse(
            detection_id=status_result["detection_id"],
            status=status_result["status"],
            repository_url=status_result["repository_url"],
            created_at=status_result["created_at"],
            updated_at=status_result["updated_at"],
            estimated_completion=status_result.get("estimated_completion"),
            error_message=status_result.get("error_message"),
            record_id=status_result.get("record_id"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detection status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[DetectionStatusResponse])
async def list_detections(
    status: DetectionStatus = None,
    current_tenant: str = Depends(get_current_tenant),
    detection_service=Depends(get_tenant_aware_detection_service),
) -> List[DetectionStatusResponse]:
    """List detection jobs for the current tenant."""
    try:
        jobs_result = await detection_service.list_detections(current_tenant, status)

        if isinstance(jobs_result, Exception):
            raise HTTPException(
                status_code=500, detail=f"Failed to list detections: {jobs_result}"
            )

        return [
            DetectionStatusResponse(
                detection_id=job["detection_id"],
                status=job["status"],
                repository_url=job["repository_url"],
                created_at=job["created_at"],
                updated_at=job["updated_at"],
                estimated_completion=job.get("estimated_completion"),
                error_message=job.get("error_message"),
                record_id=job.get("record_id"),
            )
            for job in jobs_result
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing detections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
