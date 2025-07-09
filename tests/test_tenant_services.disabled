#!/usr/bin/env python
"""
Unit tests for tenant-aware services functionality.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from metagit.api.detection_tenant import TenantAwareDetectionService
from metagit.api.models import DetectionStatus
from metagit.api.opensearch_tenant import TenantAwareOpenSearchService
from metagit.core.config.models import MetagitRecord


class TestTenantAwareOpenSearchService:
    """Test tenant-aware OpenSearch service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.service = TenantAwareOpenSearchService(
            hosts=[{"host": "localhost", "port": 9200}], index_name="test-index"
        )
        self.service.client = self.mock_client

    @pytest.mark.asyncio
    async def test_store_record_with_tenant(self):
        """Test storing record with tenant context."""
        # Mock record
        record = MetagitRecord(
            name="test-repo",
            description="Test repository",
            url="https://github.com/test/repo",
            kind="repository",
        )

        # Mock OpenSearch response
        self.mock_client.index.return_value = {"_id": "test-id"}

        result = await self.service.store_record(record, "tenant-a")

        assert result == "test-id"
        self.mock_client.index.assert_called_once()

        # Verify tenant_id was added to the record
        call_args = self.mock_client.index.call_args
        stored_data = call_args[1]["body"]
        assert stored_data["tenant_id"] == "tenant-a"

    @pytest.mark.asyncio
    async def test_get_record_with_tenant_verification(self):
        """Test getting record with tenant verification."""
        # Mock OpenSearch response
        self.mock_client.get.return_value = {
            "_source": {
                "name": "test-repo",
                "description": "Test repository",
                "url": "https://github.com/test/repo",
                "kind": "repository",
                "tenant_id": "tenant-a",
            }
        }

        result = await self.service.get_record("test-id", "tenant-a")

        assert isinstance(result, MetagitRecord)
        assert result.name == "test-repo"
        assert result.url == "https://github.com/test/repo"

    @pytest.mark.asyncio
    async def test_get_record_tenant_mismatch(self):
        """Test getting record with wrong tenant returns error."""
        # Mock OpenSearch response
        self.mock_client.get.return_value = {
            "_source": {"name": "test-repo", "tenant_id": "tenant-a"}
        }

        result = await self.service.get_record("test-id", "tenant-b")

        assert isinstance(result, Exception)
        assert "Record not found or access denied" in str(result)

    @pytest.mark.asyncio
    async def test_search_records_with_tenant_filter(self):
        """Test searching records with tenant filtering."""
        # Mock OpenSearch response
        self.mock_client.search.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "test-id",
                        "_source": {"name": "test-repo", "tenant_id": "tenant-a"},
                    }
                ],
            }
        }

        result = await self.service.search_records("test", "tenant-a")

        assert isinstance(result, dict)
        assert result["total"] == 1
        assert len(result["results"]) == 1

        # Verify tenant filter was applied
        call_args = self.mock_client.search.call_args
        search_body = call_args[1]["body"]
        assert {"term": {"tenant_id": "tenant-a"}} in search_body["query"]["bool"][
            "must"
        ]

    @pytest.mark.asyncio
    async def test_update_record_with_tenant_verification(self):
        """Test updating record with tenant verification."""
        # Mock get_record to return existing record
        with patch.object(
            self.service,
            "get_record",
            return_value=MetagitRecord(
                name="test-repo", url="https://github.com/test/repo", kind="repository"
            ),
        ):
            # Mock update response
            self.mock_client.update.return_value = {"result": "updated"}

            updated_record = MetagitRecord(
                name="updated-repo",
                url="https://github.com/test/repo",
                kind="repository",
            )

            result = await self.service.update_record(
                "test-id", updated_record, "tenant-a"
            )

            assert result is True
            self.mock_client.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_record_with_tenant_verification(self):
        """Test deleting record with tenant verification."""
        # Mock get_record to return existing record
        with patch.object(
            self.service,
            "get_record",
            return_value=MetagitRecord(
                name="test-repo", url="https://github.com/test/repo", kind="repository"
            ),
        ):
            # Mock delete response
            self.mock_client.delete.return_value = {"result": "deleted"}

            result = await self.service.delete_record("test-id", "tenant-a")

            assert result is True
            self.mock_client.delete.assert_called_once()


class TestTenantAwareDetectionService:
    """Test tenant-aware detection service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_opensearch = MagicMock()
        self.service = TenantAwareDetectionService(
            opensearch_service=self.mock_opensearch, max_concurrent_jobs=5
        )

    @pytest.mark.asyncio
    async def test_submit_detection_with_tenant(self):
        """Test submitting detection with tenant context."""
        # Mock successful detection
        with patch(
            "metagit.api.detection_tenant.normalize_git_url",
            return_value="https://github.com/test/repo",
        ):
            result = await self.service.submit_detection(
                repository_url="https://github.com/test/repo",
                tenant_id="tenant-a",
                priority=1,
                metadata={"test": "data"},
            )

            assert isinstance(result, str)
            assert result in self.service.active_jobs

            job = self.service.active_jobs[result]
            assert job["tenant_id"] == "tenant-a"
            assert job["repository_url"] == "https://github.com/test/repo"
            assert job["status"] == DetectionStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_detection_status_with_tenant_verification(self):
        """Test getting detection status with tenant verification."""
        # Add a test job
        job_id = "test-job-id"
        self.service.active_jobs[job_id] = {
            "detection_id": job_id,
            "repository_url": "https://github.com/test/repo",
            "tenant_id": "tenant-a",
            "status": DetectionStatus.PENDING,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Test correct tenant
        result = await self.service.get_detection_status(job_id, "tenant-a")

        assert isinstance(result, dict)
        assert result["detection_id"] == job_id
        assert result["tenant_id"] == "tenant-a"

    @pytest.mark.asyncio
    async def test_get_detection_status_wrong_tenant(self):
        """Test getting detection status with wrong tenant returns error."""
        # Add a test job
        job_id = "test-job-id"
        self.service.active_jobs[job_id] = {
            "detection_id": job_id,
            "repository_url": "https://github.com/test/repo",
            "tenant_id": "tenant-a",
            "status": DetectionStatus.PENDING,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Test wrong tenant
        result = await self.service.get_detection_status(job_id, "tenant-b")

        assert isinstance(result, Exception)
        assert "Detection job not found or access denied" in str(result)

    @pytest.mark.asyncio
    async def test_list_detections_with_tenant_filter(self):
        """Test listing detections with tenant filtering."""
        # Add test jobs for different tenants
        self.service.active_jobs["job-1"] = {
            "detection_id": "job-1",
            "repository_url": "https://github.com/test/repo1",
            "tenant_id": "tenant-a",
            "status": DetectionStatus.PENDING,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        self.service.active_jobs["job-2"] = {
            "detection_id": "job-2",
            "repository_url": "https://github.com/test/repo2",
            "tenant_id": "tenant-b",
            "status": DetectionStatus.PENDING,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Test filtering by tenant
        result = await self.service.list_detections("tenant-a")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["detection_id"] == "job-1"

    @pytest.mark.asyncio
    async def test_list_detections_with_status_filter(self):
        """Test listing detections with status filter."""
        # Add test jobs with different statuses
        self.service.active_jobs["job-1"] = {
            "detection_id": "job-1",
            "repository_url": "https://github.com/test/repo1",
            "tenant_id": "tenant-a",
            "status": DetectionStatus.PENDING,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        self.service.active_jobs["job-2"] = {
            "detection_id": "job-2",
            "repository_url": "https://github.com/test/repo2",
            "tenant_id": "tenant-a",
            "status": DetectionStatus.COMPLETED,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Test filtering by status
        result = await self.service.list_detections("tenant-a", DetectionStatus.PENDING)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["detection_id"] == "job-1"
        assert result[0]["status"] == DetectionStatus.PENDING

    @pytest.mark.asyncio
    async def test_submit_detection_invalid_url(self):
        """Test submitting detection with invalid URL."""
        with patch("metagit.api.detection_tenant.normalize_git_url", return_value=None):
            result = await self.service.submit_detection(
                repository_url="invalid-url", tenant_id="tenant-a"
            )

            assert isinstance(result, Exception)
            assert "Invalid repository URL" in str(result)
