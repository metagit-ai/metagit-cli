#!/usr/bin/env python
"""
Detection endpoints for the metagit API.
"""

import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import ValidationError

from metagit.api.detection import DetectionService
from metagit.api.models import (
    DetectionRequest,
    DetectionResponse,
    DetectionStatus,
    DetectionStatusResponse,
)
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detect", tags=["detection"])


def get_detection_service() -> DetectionService:
    """Dependency to get detection service."""
    from metagit.api.app import detection_service

    if not detection_service:
        raise HTTPException(status_code=503, detail="Detection service not available")
    return detection_service


@router.post("/submit", response_model=DetectionResponse)
async def submit_detection(
    request: DetectionRequest,
    detection: DetectionService = Depends(get_detection_service),
) -> DetectionResponse:
    """Submit a new detection job."""
    try:
        if not request.repository_url:
            raise HTTPException(status_code=400, detail="Repository URL is required")

        job = await detection.submit_detection(
            repository_url=normalize_git_url(
                str(request.repository_url) if request.repository_url else None
            ),
            priority=request.priority,
            metadata=request.metadata,
        )

        if isinstance(job, Exception):
            raise HTTPException(
                status_code=500, detail=f"Failed to submit detection: {job}"
            )

        return DetectionResponse(
            detection_id=job.detection_id,
            status=DetectionStatus.PENDING,
            repository_url=normalize_git_url(
                str(job.repository_url) if job.repository_url else None
            ),
            created_at=job.created_at,
            updated_at=job.updated_at,
            estimated_completion=None,
            error_message=job.error_message,
            record_id=job.record_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in submit_detection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{detection_id}/status", response_model=DetectionStatusResponse)
async def get_detection_status(
    detection_id: str,
    detection: DetectionService = Depends(get_detection_service),
) -> DetectionStatusResponse:
    """Get the status of a detection job."""
    try:
        job = detection.get_job_status(detection_id)
        if not job:
            raise HTTPException(
                status_code=404, detail=f"Detection job {detection_id} not found"
            )

        return DetectionStatusResponse(
            detection_id=job.detection_id,
            status=job.status,
            repository_url=normalize_git_url(
                str(job.repository_url) if job.repository_url else None
            ),
            created_at=job.created_at,
            updated_at=job.updated_at,
            estimated_completion=None,
            error_message=job.error_message,
            record_id=job.record_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detection status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[DetectionStatusResponse])
async def list_detections(
    detection: DetectionService = Depends(get_detection_service),
) -> List[DetectionStatusResponse]:
    """List all detection jobs."""
    try:
        jobs = detection.get_all_jobs()

        return [
            DetectionStatusResponse(
                detection_id=job.detection_id,
                status=job.status,
                repository_url=normalize_git_url(
                    str(job.repository_url) if job.repository_url else None
                ),
                created_at=job.created_at,
                updated_at=job.updated_at,
                estimated_completion=None,
                error_message=job.error_message,
                record_id=job.record_id,
            )
            for job in jobs
        ]

    except Exception as e:
        logger.error(f"Error listing detections: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
