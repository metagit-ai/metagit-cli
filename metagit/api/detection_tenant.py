#!/usr/bin/env python
"""
Tenant-aware detection service for processing repository detection jobs.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from metagit.api.models import DetectionStatus
from metagit.core.config.models import MetagitRecord
from metagit.core.detect.repository import RepositoryAnalysis
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)


class TenantAwareDetectionService:
    """Tenant-aware detection service for processing repository detection jobs."""

    def __init__(
        self,
        opensearch_service,
        max_concurrent_jobs: int = 5,
    ):
        """
        Initialize tenant-aware detection service.

        Args:
            opensearch_service: OpenSearch service for storing records
            max_concurrent_jobs: Maximum number of concurrent detection jobs
        """
        self.opensearch_service = opensearch_service
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self.job_queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self) -> None:
        """Start the detection service."""
        if self.running:
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Tenant-aware detection service started")

    async def stop(self) -> None:
        """Stop the detection service."""
        if not self.running:
            return

        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Tenant-aware detection service stopped")

    async def submit_detection(
        self,
        repository_url: str,
        tenant_id: str,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Exception]:
        """
        Submit a detection job with tenant context.

        Args:
            repository_url: Repository URL to analyze
            tenant_id: Tenant identifier
            priority: Detection priority
            metadata: Additional metadata

        Returns:
            Detection ID or Exception
        """
        try:
            # Validate repository URL
            normalized_url = normalize_git_url(repository_url)
            if not normalized_url:
                return Exception("Invalid repository URL")

            # Create detection job
            detection_id = str(uuid.uuid4())
            job = {
                "detection_id": detection_id,
                "repository_url": normalized_url,
                "tenant_id": tenant_id,
                "priority": priority,
                "metadata": metadata or {},
                "status": DetectionStatus.PENDING,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "error_message": None,
                "record_id": None,
            }

            # Add to active jobs
            self.active_jobs[detection_id] = job

            # Add to queue with priority
            await self.job_queue.put((priority, detection_id))

            logger.info(f"Submitted detection {detection_id} for tenant {tenant_id}")
            return detection_id

        except Exception as e:
            logger.error(f"Failed to submit detection for tenant {tenant_id}: {e}")
            return e

    async def get_detection_status(
        self, detection_id: str, tenant_id: str
    ) -> Union[Dict[str, Any], Exception]:
        """
        Get detection job status with tenant verification.

        Args:
            detection_id: Detection job ID
            tenant_id: Tenant identifier for verification

        Returns:
            Detection status or Exception
        """
        try:
            if detection_id not in self.active_jobs:
                return Exception("Detection job not found")

            job = self.active_jobs[detection_id]

            # Verify tenant ownership
            if job.get("tenant_id") != tenant_id:
                return Exception("Detection job not found or access denied")

            return {
                "detection_id": job["detection_id"],
                "tenant_id": job["tenant_id"],
                "status": job["status"],
                "repository_url": job["repository_url"],
                "created_at": job["created_at"],
                "updated_at": job["updated_at"],
                "estimated_completion": job.get("estimated_completion"),
                "error_message": job.get("error_message"),
                "record_id": job.get("record_id"),
            }

        except Exception as e:
            logger.error(
                f"Failed to get detection status {detection_id} for tenant {tenant_id}: {e}"
            )
            return e

    async def list_detections(
        self, tenant_id: str, status: Optional[DetectionStatus] = None
    ) -> Union[List[Dict[str, Any]], Exception]:
        """
        List detection jobs for a tenant.

        Args:
            tenant_id: Tenant identifier
            status: Optional status filter

        Returns:
            List of detection jobs or Exception
        """
        try:
            jobs = []
            for job in self.active_jobs.values():
                # Filter by tenant
                if job.get("tenant_id") != tenant_id:
                    continue

                # Filter by status if specified
                if status and job["status"] != status:
                    continue

                jobs.append(
                    {
                        "detection_id": job["detection_id"],
                        "tenant_id": job["tenant_id"],
                        "status": job["status"],
                        "repository_url": job["repository_url"],
                        "created_at": job["created_at"],
                        "updated_at": job["updated_at"],
                        "estimated_completion": job.get("estimated_completion"),
                        "error_message": job.get("error_message"),
                        "record_id": job.get("record_id"),
                    }
                )

            # Sort by creation time (newest first)
            jobs.sort(key=lambda x: x["created_at"], reverse=True)
            return jobs

        except Exception as e:
            logger.error(f"Failed to list detections for tenant {tenant_id}: {e}")
            return e

    async def _worker_loop(self) -> None:
        """Main worker loop for processing detection jobs."""
        while self.running:
            try:
                # Wait for job with timeout
                try:
                    priority, detection_id = await asyncio.wait_for(
                        self.job_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Process job
                await self._process_detection(detection_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in detection worker loop: {e}")

    async def _process_detection(self, detection_id: str) -> None:
        """Process a single detection job."""
        try:
            if detection_id not in self.active_jobs:
                logger.warning(f"Detection job {detection_id} not found in active jobs")
                return

            job = self.active_jobs[detection_id]
            tenant_id = job["tenant_id"]
            repository_url = job["repository_url"]

            # Update status to running
            job["status"] = DetectionStatus.RUNNING
            job["updated_at"] = datetime.utcnow()
            job["estimated_completion"] = datetime.utcnow() + timedelta(minutes=5)

            logger.info(f"Processing detection {detection_id} for tenant {tenant_id}")

            # Perform detection using RepositoryAnalysis
            detection_result = RepositoryAnalysis.from_url(repository_url)

            if isinstance(detection_result, Exception):
                # Detection failed
                job["status"] = DetectionStatus.FAILED
                job["error_message"] = str(detection_result)
                job["updated_at"] = datetime.utcnow()
                logger.error(f"Detection failed for {detection_id}: {detection_result}")
                return

            # Convert RepositoryAnalysis to MetagitRecord
            analysis = detection_result
            try:
                # Create MetagitRecord from analysis
                record = MetagitRecord(
                    name=analysis.name or "Unknown",
                    description=analysis.description or "",
                    url=analysis.url or repository_url,
                    kind=analysis.kind.value if analysis.kind else "repository",
                    branch_strategy="main",
                    detection_timestamp=datetime.utcnow(),
                    detection_source="api",
                    detection_version="1.0.0",
                    branches=[],
                    metrics=analysis.metrics,
                    metadata={
                        "has_ci": analysis.has_docker,
                        "has_tests": analysis.has_tests,
                        "has_docs": analysis.has_docs,
                        "has_docker": analysis.has_docker,
                        "has_iac": analysis.has_iac,
                    },
                    language_detection={
                        "primary": (
                            analysis.language_detection.primary
                            if analysis.language_detection
                            else "Unknown"
                        ),
                        "secondary": (
                            analysis.language_detection.secondary
                            if analysis.language_detection
                            else []
                        ),
                        "frameworks": (
                            analysis.language_detection.frameworks
                            if analysis.language_detection
                            else []
                        ),
                        "package_managers": (
                            analysis.language_detection.package_managers
                            if analysis.language_detection
                            else []
                        ),
                    },
                    project_type_detection={
                        "type": (
                            analysis.project_type_detection.type.value
                            if analysis.project_type_detection
                            else "other"
                        ),
                        "domain": (
                            analysis.project_type_detection.domain.value
                            if analysis.project_type_detection
                            else "other"
                        ),
                        "confidence": (
                            analysis.project_type_detection.confidence
                            if analysis.project_type_detection
                            else 0.0
                        ),
                    },
                )
            except Exception as e:
                # Failed to create record
                job["status"] = DetectionStatus.FAILED
                job["error_message"] = f"Failed to create record: {e}"
                job["updated_at"] = datetime.utcnow()
                logger.error(f"Failed to create record for {detection_id}: {e}")
                return

            # Store record in OpenSearch
            store_result = await self.opensearch_service.store_record(record, tenant_id)

            if isinstance(store_result, Exception):
                # Storage failed
                job["status"] = DetectionStatus.FAILED
                job["error_message"] = f"Failed to store record: {store_result}"
                job["updated_at"] = datetime.utcnow()
                logger.error(
                    f"Failed to store record for {detection_id}: {store_result}"
                )
                return

            # Detection completed successfully
            job["status"] = DetectionStatus.COMPLETED
            job["record_id"] = store_result
            job["updated_at"] = datetime.utcnow()
            job["estimated_completion"] = None

            logger.info(
                f"Detection completed for {detection_id}, record stored as {store_result}"
            )

        except Exception as e:
            logger.error(f"Error processing detection {detection_id}: {e}")
            if detection_id in self.active_jobs:
                job = self.active_jobs[detection_id]
                job["status"] = DetectionStatus.FAILED
                job["error_message"] = str(e)
                job["updated_at"] = datetime.utcnow()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
