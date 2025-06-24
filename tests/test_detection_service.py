#!/usr/bin/env python
"""Tests for the detection service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from metagit.api.detection import DetectionJob, DetectionService
from metagit.api.models import DetectionStatus
from metagit.core.utils.common import normalize_git_url


class TestDetectionJob:
    """Test DetectionJob class."""

    def test_detection_job_creation(self):
        """Test DetectionJob creation."""
        job = DetectionJob(
            detection_id="test-id",
            repository_url="https://github.com/user/repo",
            priority=5,
            metadata={"test": "data"},
        )

        assert job.detection_id == "test-id"
        assert job.repository_url == "https://github.com/user/repo"
        assert job.priority == 5
        assert job.metadata == {"test": "data"}
        assert job.status == DetectionStatus.PENDING
        assert job.error_message is None
        assert job.record_id is None
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)

    def test_detection_job_defaults(self):
        """Test DetectionJob with default values."""
        job = DetectionJob(
            detection_id="test-id",
            repository_url="https://github.com/user/repo",
        )

        assert job.priority == 0
        assert job.metadata == {}
        assert job.status == DetectionStatus.PENDING

    def test_detection_job_without_url(self):
        """Test DetectionJob without repository URL."""
        job = DetectionJob(
            detection_id="test-id",
            repository_url=None,
        )

        assert job.repository_url is None


class TestDetectionService:
    """Test DetectionService class."""

    @pytest.fixture
    def mock_opensearch_service(self):
        """Create a mock OpenSearch service."""
        mock_service = MagicMock()
        mock_service.store_record = AsyncMock(return_value="test-record-id")
        mock_service.search_records = AsyncMock(
            return_value={"total": 0, "records": []}
        )
        return mock_service

    @pytest.fixture
    def detection_service(self, mock_opensearch_service):
        """Create a DetectionService instance."""
        return DetectionService(
            opensearch_service=mock_opensearch_service,
            max_concurrent_jobs=2,
        )

    @pytest.mark.asyncio
    async def test_submit_detection_success(self, detection_service):
        """Test successful detection submission."""
        job = await detection_service.submit_detection(
            repository_url="https://github.com/user/repo",
            priority=5,
            metadata={"test": "data"},
        )

        assert isinstance(job, DetectionJob)
        assert job.repository_url == "https://github.com/user/repo"
        assert job.priority == 5
        assert job.metadata == {"test": "data"}
        assert job.status == DetectionStatus.PENDING

    @pytest.mark.asyncio
    async def test_submit_detection_with_url_normalization(self, detection_service):
        """Test detection submission with URL normalization."""
        job = await detection_service.submit_detection(
            repository_url="https://github.com/user/repo/",
            priority=0,
        )

        assert (
            job.repository_url == "https://github.com/user/repo"
        )  # Trailing slash removed

    @pytest.mark.asyncio
    async def test_submit_detection_missing_url(self, detection_service):
        """Test detection submission without URL."""
        result = await detection_service.submit_detection(
            repository_url=None,
        )

        assert isinstance(result, Exception)
        assert "Repository URL is required" in str(result)

    @pytest.mark.asyncio
    async def test_submit_detection_invalid_url(self, detection_service):
        """Test detection submission with invalid URL."""
        result = await detection_service.submit_detection(
            repository_url="",
        )

        assert isinstance(result, Exception)
        assert "Invalid repository URL" in str(result)

    @pytest.mark.asyncio
    async def test_submit_detection_empty_url(self, detection_service):
        """Test detection submission with empty URL."""
        result = await detection_service.submit_detection(
            repository_url="   ",
        )

        assert isinstance(result, Exception)
        assert "Invalid repository URL" in str(result)

    @pytest.mark.asyncio
    async def test_get_job_status(self, detection_service):
        """Test getting job status."""
        # Submit a job first
        job = await detection_service.submit_detection(
            repository_url="https://github.com/user/repo",
        )

        # Get the job status
        retrieved_job = detection_service.get_job_status(job.detection_id)

        assert retrieved_job is not None
        assert retrieved_job.detection_id == job.detection_id
        assert retrieved_job.repository_url == job.repository_url

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, detection_service):
        """Test getting job status for non-existent job."""
        job = detection_service.get_job_status("non-existent-id")
        assert job is None

    @pytest.mark.asyncio
    async def test_get_all_jobs(self, detection_service):
        """Test getting all jobs."""
        # Submit multiple jobs
        job1 = await detection_service.submit_detection(
            repository_url="https://github.com/user/repo1",
        )
        job2 = await detection_service.submit_detection(
            repository_url="https://github.com/user/repo2",
        )

        # Get all jobs
        all_jobs = detection_service.get_all_jobs()

        assert len(all_jobs) >= 2
        job_ids = [job.detection_id for job in all_jobs]
        assert job1.detection_id in job_ids
        assert job2.detection_id in job_ids

    @pytest.mark.asyncio
    async def test_check_existing_record_not_found(self, detection_service):
        """Test checking for existing record when none exists."""
        result = await detection_service._check_existing_record(
            "https://github.com/user/repo",
            "test-checksum",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_check_existing_record_found(
        self, detection_service, mock_opensearch_service
    ):
        """Test checking for existing record when one exists."""
        # Mock the search to return an existing record
        mock_opensearch_service.search_records.return_value = {
            "total": 1,
            "results": [{"_id": "existing-record-id", "checksum": "test-checksum"}],
        }

        result = await detection_service._check_existing_record(
            "https://github.com/user/repo",
            "test-checksum",
        )

        assert result == "existing-record-id"

    @pytest.mark.asyncio
    async def test_check_existing_record_with_url_normalization(
        self, detection_service
    ):
        """Test checking for existing record with URL normalization."""
        result = await detection_service._check_existing_record(
            "https://github.com/user/repo/",
            "test-checksum",
        )

        # Should normalize the URL before searching
        assert result is None

    @pytest.mark.asyncio
    async def test_service_start_stop(self, detection_service):
        """Test service start and stop."""
        # Start the service
        await detection_service.start()
        assert detection_service.is_running is True

        # Stop the service
        await detection_service.stop()
        assert detection_service.is_running is False

    @pytest.mark.asyncio
    async def test_service_context_manager(self, detection_service):
        """Test service as context manager."""
        async with detection_service:
            assert detection_service.is_running is True
        assert detection_service.is_running is False


class TestURLNormalization:
    """Test URL normalization functionality."""

    def test_normalize_git_url_removes_trailing_slash(self):
        """Test that normalize_git_url removes trailing slashes."""
        test_cases = [
            ("https://github.com/user/repo/", "https://github.com/user/repo"),
            ("https://gitlab.com/user/repo/", "https://gitlab.com/user/repo"),
            ("https://github.com/user/repo.git/", "https://github.com/user/repo.git"),
            ("https://gitlab.com/user/repo.git/", "https://gitlab.com/user/repo.git"),
        ]

        for input_url, expected in test_cases:
            result = normalize_git_url(input_url)
            assert result == expected

    def test_normalize_git_url_no_trailing_slash(self):
        """Test that normalize_git_url doesn't change URLs without trailing slashes."""
        test_cases = [
            "https://github.com/user/repo",
            "https://gitlab.com/user/repo",
            "https://github.com/user/repo.git",
            "https://gitlab.com/user/repo.git",
        ]

        for url in test_cases:
            result = normalize_git_url(url)
            assert result == url

    def test_normalize_git_url_edge_cases(self):
        """Test normalize_git_url with edge cases."""
        # Empty string
        assert normalize_git_url("") == ""

        # None
        assert normalize_git_url(None) is None

        # Whitespace only
        assert normalize_git_url("   ") == ""

        # Multiple trailing slashes
        assert (
            normalize_git_url("https://github.com/user/repo///")
            == "https://github.com/user/repo"
        )
