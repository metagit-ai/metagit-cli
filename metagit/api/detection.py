#!/usr/bin/env python
"""
Detection service for asynchronously processing repository detection requests.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from metagit.api.models import DetectionStatus
from metagit.core.config.models import Branch, MetagitRecord
from metagit.core.detect.repository import RepositoryAnalysis
from metagit.core.providers import registry
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)


class DetectionJob:
    """Represents a detection job."""

    def __init__(
        self,
        detection_id: str,
        repository_url: Optional[str],
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a detection job.

        Args:
            detection_id: Unique job ID
            repository_url: Repository URL to analyze
            priority: Job priority (higher = more important)
            metadata: Additional metadata
        """
        self.detection_id = detection_id
        self.repository_url = repository_url
        self.priority = priority
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.status = DetectionStatus.PENDING
        self.error_message = None
        self.record_id = None

        # Detection results
        self.analysis_result: Optional[RepositoryAnalysis] = None
        self.metagit_record: Optional[MetagitRecord] = None


class DetectionService:
    """Service for managing async repository detection jobs."""

    def __init__(self, opensearch_service, max_concurrent_jobs: int = 5):
        """
        Initialize detection service.

        Args:
            opensearch_service: OpenSearch service instance
            max_concurrent_jobs: Maximum number of concurrent detection jobs
        """
        self.opensearch_service = opensearch_service
        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_jobs: Dict[str, DetectionJob] = {}
        self.job_queue: asyncio.Queue = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.is_running = False

    async def start(self) -> None:
        """Start the detection service worker."""
        if not self.is_running:
            self.is_running = True
            self.worker_task = asyncio.create_task(self._worker_loop())
            logger.info("Detection service started")

    async def stop(self) -> None:
        """Stop the detection service worker."""
        if self.is_running:
            self.is_running = False
            if self.worker_task:
                self.worker_task.cancel()
                try:
                    await self.worker_task
                except asyncio.CancelledError:
                    pass
            logger.info("Detection service stopped")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def submit_detection(
        self,
        repository_url: Optional[str],
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Union[DetectionJob, Exception]:
        """
        Submit a new detection job.

        Args:
            repository_url: Repository URL to analyze
            priority: Job priority (higher = more important)
            metadata: Additional metadata

        Returns:
            DetectionJob or Exception
        """
        try:
            # Validate input
            if repository_url is None:
                return Exception("Repository URL is required")

            # Normalize URL
            normalized_url = normalize_git_url(repository_url)
            if not normalized_url:
                return Exception("Invalid repository URL")

            # Generate unique detection ID
            detection_id = str(uuid.uuid4())

            # Create detection job
            job = DetectionJob(
                detection_id=detection_id,
                repository_url=normalized_url,
                priority=priority,
                metadata=metadata,
            )

            # Add to active jobs and queue
            self.active_jobs[detection_id] = job
            await self.job_queue.put(job)
            logger.info(
                f"Submitted detection job {detection_id} for URL: {normalized_url}"
            )

            return job

        except Exception as e:
            logger.error(f"Failed to submit detection: {e}")
            return e

    def get_job_status(self, detection_id: str) -> Optional[DetectionJob]:
        """
        Get job status by ID.

        Args:
            detection_id: Detection job ID

        Returns:
            DetectionJob or None if not found
        """
        return self.active_jobs.get(detection_id)

    def get_all_jobs(self) -> List[DetectionJob]:
        """Get all active jobs."""
        return list(self.active_jobs.values())

    async def _worker_loop(self) -> None:
        """Main worker loop for processing detection jobs."""
        while self.is_running:
            try:
                # Get job from queue
                job = await asyncio.wait_for(self.job_queue.get(), timeout=1.0)

                # Process job
                await self._process_job(job)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")

    async def _process_job(self, job: DetectionJob) -> None:
        """
        Process a detection job.

        Args:
            job: Detection job to process
        """
        try:
            logger.info(f"Processing detection job {job.detection_id}")
            job.status = DetectionStatus.RUNNING
            job.updated_at = datetime.utcnow()

            # Get repository URL for checking existing records
            repository_url = job.repository_url
            if not repository_url:
                raise Exception("No repository URL provided")

            # Check if record already exists with same checksum
            existing_record_id = await self._check_existing_record(
                repository_url,
                None,  # We'll get checksum after cloning
            )
            if isinstance(existing_record_id, Exception):
                raise existing_record_id

            if existing_record_id:
                logger.info(
                    f"Record already exists for URL {repository_url}, skipping detection"
                )
                job.status = DetectionStatus.COMPLETED
                job.record_id = existing_record_id
                job.updated_at = datetime.utcnow()
                return

            # Clone and analyze repository
            logger.info(f"Cloning repository from URL: {repository_url}")
            analysis = RepositoryAnalysis.from_url(repository_url, logger)
            if isinstance(analysis, Exception):
                raise analysis

            # Enrich with provider data
            await self._enrich_with_provider_data(analysis, repository_url, job)

            # Create MetagitRecord
            record = await self._create_metagit_record(job, analysis)
            if isinstance(record, Exception):
                raise record

            # Store record
            record_id = await self.opensearch_service.store_record(record)
            if isinstance(record_id, Exception):
                raise record_id

            # Update job status
            job.status = DetectionStatus.COMPLETED
            job.record_id = record_id
            job.updated_at = datetime.utcnow()

            logger.info(f"Successfully completed detection job {job.detection_id}")

        except Exception as e:
            logger.error(f"Failed to process detection job {job.detection_id}: {e}")
            job.status = DetectionStatus.FAILED
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()

    async def _enrich_with_provider_data(
        self, analysis: RepositoryAnalysis, url: Union[str, Any], job: DetectionJob
    ) -> None:
        """
        Enrich analysis with provider-specific data.

        Args:
            analysis: RepositoryAnalysis instance
            url: Repository URL (can be HttpUrl or string)
            job: Detection job to store provider metadata
        """
        try:
            # Convert HttpUrl to string if needed
            url_string = normalize_git_url(str(url) if url else None)
            if not url_string:
                logger.warning("No URL provided for provider enrichment")
                return

            # Get provider for URL
            provider = registry.get_provider_for_url(url_string)
            if not provider:
                logger.warning(f"No provider found for URL: {url_string}")
                return

            # Extract repo info
            repo_info = provider.extract_repo_info(url_string)
            owner = repo_info.get("owner")
            repo = repo_info.get("repo")

            if not owner or not repo:
                logger.warning(f"Could not extract repo info from URL: {url_string}")
                return

            # Get metrics
            metrics_result = provider.get_repository_metrics(owner, repo)
            if not isinstance(metrics_result, Exception):
                analysis.metrics = metrics_result

            # Get metadata
            metadata_result = provider.get_repository_metadata(owner, repo)
            if not isinstance(metadata_result, Exception):
                # Update analysis with metadata
                if metadata_result.get("description"):
                    analysis.description = metadata_result["description"]
                # Store provider metadata in job.metadata for later use
                # This will be filtered and merged when creating the MetagitRecord
                job.metadata.update(metadata_result)

        except Exception as e:
            logger.error(f"Error enriching with provider data: {e}")

    async def _create_metagit_record(
        self, job: DetectionJob, analysis: RepositoryAnalysis
    ) -> Union[MetagitRecord, Exception]:
        """
        Create MetagitRecord from analysis.

        Args:
            job: Detection job
            analysis: RepositoryAnalysis instance

        Returns:
            MetagitRecord or Exception
        """
        try:
            # Get current branch from git repository
            current_branch = None
            checksum = None
            if analysis.is_git_repo:
                try:
                    from git import Repo

                    repo = Repo(analysis.path)
                    current_branch = repo.active_branch.name
                    checksum = repo.head.commit.hexsha
                except Exception as e:
                    logger.warning(f"Could not get current branch: {e}")

            # Create CI/CD configuration from analysis
            cicd_config = None
            if (
                analysis.ci_config_analysis
                and analysis.ci_config_analysis.detected_tool
            ):
                from metagit.core.config.models import CICD, CICDPlatform, Pipeline

                platform_map = {
                    "GitHub Actions": CICDPlatform.GITHUB,
                    "GitLab CI": CICDPlatform.GITLAB,
                    "CircleCI": CICDPlatform.CIRCLECI,
                    "Jenkins": CICDPlatform.JENKINS,
                }
                platform = platform_map.get(
                    analysis.ci_config_analysis.detected_tool, CICDPlatform.CUSTOM
                )
                cicd_config = CICD(
                    platform=platform,
                    pipelines=[
                        Pipeline(
                            name="default",
                            ref=analysis.ci_config_analysis.ci_config_path or "unknown",
                        )
                    ],
                )

            # Create repository metadata from analysis
            from datetime import timezone

            from metagit.core.config.models import RepoMetadata

            metadata = RepoMetadata(
                default_branch=(
                    analysis.branch_analysis.branches[0].name
                    if analysis.branch_analysis and analysis.branch_analysis.branches
                    else None
                ),
                has_ci=analysis.ci_config_analysis is not None,
                has_tests=analysis.has_tests,
                has_docs=analysis.has_docs,
                has_docker=analysis.has_docker,
                has_iac=analysis.has_iac,
                created_at=datetime.now(
                    timezone.utc
                ),  # Would need git history for actual creation date
                last_commit_at=datetime.now(
                    timezone.utc
                ),  # Would need git history for actual last commit
            )

            # Create record data directly from analysis
            record_data = {
                "name": analysis.name or "unknown",
                "description": analysis.description,
                "url": normalize_git_url(analysis.url),
                "kind": analysis.kind,
                "branch_strategy": None,  # Will be set from analysis if available
                "taskers": None,
                "branch_naming": None,
                "branch": current_branch,
                "checksum": checksum,
                "last_updated": datetime.utcnow(),
                "artifacts": None,
                "secrets_management": None,
                "secrets": None,
                "variables": None,
                "cicd": cicd_config,
                "deployment": None,
                "observability": None,
                "paths": None,
                "dependencies": None,
                "components": None,
                "workspace": None,
                # Detection-specific fields
                "detection_timestamp": datetime.utcnow(),
                "detection_source": "api",
                "detection_version": "1.0.0",
                "branches": (
                    [
                        Branch(
                            name=branch_info.name,
                            environment="remote" if branch_info.is_remote else "local",
                        )
                        for branch_info in analysis.branch_analysis.branches
                    ]
                    if analysis.branch_analysis
                    else None
                ),
                "metrics": analysis.metrics,
                "metadata": metadata,
            }

            # Add any additional metadata from job
            if job.metadata:
                # Filter job metadata to only include valid RepoMetadata fields
                valid_metadata_fields = {
                    "tags",
                    "created_at",
                    "last_commit_at",
                    "default_branch",
                    "topics",
                    "forked_from",
                    "archived",
                    "template",
                    "has_ci",
                    "has_tests",
                    "has_docs",
                    "has_docker",
                    "has_iac",
                }
                filtered_job_metadata = {
                    k: v for k, v in job.metadata.items() if k in valid_metadata_fields
                }

                # Merge job metadata with the created metadata
                metadata_dict = metadata.model_dump(
                    exclude_none=True, exclude_unset=True
                )
                metadata_dict.update(filtered_job_metadata)
                record_data["metadata"] = RepoMetadata(**metadata_dict)

            # Create MetagitRecord
            metagit_record = MetagitRecord(**record_data)
            return metagit_record

        except Exception as e:
            return e

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> None:
        """
        Clean up old completed/failed jobs.

        Args:
            max_age_hours: Maximum age in hours for jobs to keep
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        jobs_to_remove = []
        for job_id, job in self.active_jobs.items():
            if job.status in ["completed", "failed"] and job.updated_at < cutoff_time:
                jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]

        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")

    async def _check_existing_record(
        self, repository_url: str, checksum: str
    ) -> Union[str, None, Exception]:
        """
        Check if a record already exists for the given URL and checksum.

        Args:
            repository_url: Repository URL
            checksum: Git checksum

        Returns:
            Record ID if found with same checksum, None if not found, Exception on error
        """
        try:
            # Convert HttpUrl to string if needed
            url_string = normalize_git_url(
                str(repository_url) if repository_url else None
            )
            if not url_string:
                return None

            # Search for existing record by URL
            result = await self.opensearch_service.search_records(
                query="",
                filters={"url": url_string},
                page=1,
                size=1,
            )

            if isinstance(result, Exception):
                return result

            if result["total"] == 0:
                return None

            # Get the existing record
            record_data = result["results"][0]
            existing_checksum = record_data.get("checksum")
            record_id = record_data.get("_id")

            if existing_checksum == checksum:
                logger.info(
                    f"Found existing record {record_id} with same checksum {checksum}"
                )
                return record_id
            else:
                logger.info(
                    f"Found existing record {record_id} but checksum differs: {existing_checksum} vs {checksum}"
                )
                return None

        except Exception as e:
            logger.error(f"Error checking existing record: {e}")
            return e

    async def _update_existing_record(
        self, record_id: str, metagit_record: MetagitRecord
    ) -> Union[str, Exception]:
        """
        Update an existing record with new data.

        Args:
            record_id: Existing record ID
            metagit_record: Updated MetagitRecord

        Returns:
            Record ID or Exception
        """
        try:
            # Update the record
            result = await self.opensearch_service.update_record(
                record_id, metagit_record
            )
            if isinstance(result, Exception):
                return result

            logger.info(f"Updated existing record {record_id}")
            return record_id

        except Exception as e:
            logger.error(f"Error updating existing record {record_id}: {e}")
            return e
