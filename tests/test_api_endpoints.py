#!/usr/bin/env python
"""Tests for API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from metagit.api.detection import DetectionJob
from metagit.api.models import DetectionStatus
from metagit.core.utils.common import normalize_git_url


class TestDetectionEndpoints:
    """Test detection API endpoints."""

    @pytest.fixture
    def mock_detection_service(self):
        """Create a mock detection service."""
        mock_service = MagicMock()
        mock_service.submit_detection = AsyncMock()
        mock_service.get_detection_status = AsyncMock()
        mock_service.list_detections = AsyncMock()
        return mock_service

    @pytest.fixture
    def client(self, mock_detection_service):
        """Create a test client with mocked dependencies."""
        # Import here to avoid circular imports
        from metagit.api.app import app
        from metagit.api.dependencies import get_tenant_aware_detection_service

        # Override the dependency
        def override_get_tenant_aware_detection_service():
            return mock_detection_service

        app.dependency_overrides[get_tenant_aware_detection_service] = (
            override_get_tenant_aware_detection_service
        )

        # Mock the app's lifespan to prevent service startup
        with (
            patch("metagit.api.app.opensearch_service"),
            patch("metagit.api.app.detection_service"),
            patch("metagit.api.app.lifespan"),
        ):
            client = TestClient(app)
            yield client

        # Clean up
        app.dependency_overrides.clear()

    def test_submit_detection_success(self, client, mock_detection_service):
        """Test successful detection submission."""
        # Create a successful job response
        job = {
            "detection_id": "test-id",
            "status": "pending",
            "repository_url": "https://github.com/user/repo",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_detection_service.submit_detection.return_value = "test-id"
        mock_detection_service.get_detection_status.return_value = job

        # Make request
        response = client.post(
            "/detect/submit",
            json={
                "repository_url": "https://github.com/user/repo",
                "priority": 5,
                "metadata": {"test": "data"},
            },
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["detection_id"] == "test-id"
        assert data["status"] == "pending"
        assert data["repository_url"] == "https://github.com/user/repo"

    def test_submit_detection_with_url_normalization(
        self, client, mock_detection_service
    ):
        """Test detection submission with URL normalization."""
        job = {
            "detection_id": "test-id",
            "status": "pending",
            "repository_url": "https://github.com/user/repo",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_detection_service.submit_detection.return_value = "test-id"
        mock_detection_service.get_detection_status.return_value = job

        # Make request with trailing slash
        response = client.post(
            "/detect/submit",
            json={
                "repository_url": "https://github.com/user/repo/",
                "priority": 0,
            },
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert (
            data["repository_url"] == "https://github.com/user/repo"
        )  # Trailing slash removed

    def test_submit_detection_missing_url(self, client, mock_detection_service):
        """Test detection submission without URL."""
        # Make request without URL
        response = client.post(
            "/detect/submit",
            json={
                "priority": 0,
            },
        )

        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Repository URL is required" in data["detail"]

    def test_submit_detection_service_error(self, client, mock_detection_service):
        """Test detection submission when service returns error."""
        mock_detection_service.submit_detection.return_value = Exception(
            "Service error"
        )

        # Make request
        response = client.post(
            "/detect/submit",
            json={
                "repository_url": "https://github.com/user/repo",
                "priority": 0,
            },
        )

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to submit detection" in data["detail"]

    def test_get_detection_status_success(self, client, mock_detection_service):
        """Test successful detection status retrieval."""
        job = {
            "detection_id": "test-id",
            "status": "completed",
            "repository_url": "https://github.com/user/repo",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "record_id": "record-123",
        }
        mock_detection_service.get_detection_status.return_value = job

        # Make request
        response = client.get("/detect/test-id/status")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["detection_id"] == "test-id"
        assert data["status"] == "completed"
        assert data["repository_url"] == "https://github.com/user/repo"
        assert data["record_id"] == "record-123"

    def test_get_detection_status_not_found(self, client, mock_detection_service):
        """Test detection status retrieval for non-existent job."""
        mock_detection_service.get_detection_status.return_value = Exception(
            "Job not found"
        )

        # Make request
        response = client.get("/detect/non-existent-id/status")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    def test_list_detections_success(self, client, mock_detection_service):
        """Test successful detection listing."""
        job1 = {
            "detection_id": "test-id-1",
            "status": "pending",
            "repository_url": "https://github.com/user/repo1",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        job2 = {
            "detection_id": "test-id-2",
            "status": "completed",
            "repository_url": "https://github.com/user/repo2",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_detection_service.list_detections.return_value = [job1, job2]

        # Make request
        response = client.get("/detect")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["detection_id"] == "test-id-1"
        assert data[1]["detection_id"] == "test-id-2"

    def test_list_detections_empty(self, client, mock_detection_service):
        """Test detection listing when no jobs exist."""
        mock_detection_service.list_detections.return_value = []

        # Make request
        response = client.get("/detect")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestRecordsEndpoints:
    """Test records API endpoints."""

    @pytest.fixture
    def mock_opensearch_service(self):
        """Create a mock OpenSearch service."""
        mock_service = MagicMock()
        mock_service.search_records = AsyncMock()
        mock_service.delete_record = AsyncMock()
        return mock_service

    @pytest.fixture
    def client(self, mock_opensearch_service):
        """Create a test client with mocked dependencies."""
        # Import here to avoid circular imports
        from metagit.api.app import app
        from metagit.api.dependencies import get_tenant_aware_opensearch_service

        # Override the dependency
        def override_get_tenant_aware_opensearch_service():
            return mock_opensearch_service

        app.dependency_overrides[get_tenant_aware_opensearch_service] = (
            override_get_tenant_aware_opensearch_service
        )

        # Mock the app's lifespan to prevent service startup
        with (
            patch("metagit.api.app.opensearch_service"),
            patch("metagit.api.app.detection_service"),
            patch("metagit.api.app.lifespan"),
        ):
            client = TestClient(app)
            yield client

        # Clean up
        app.dependency_overrides.clear()

    def test_get_records_by_url_success(self, client, mock_opensearch_service):
        """Test successful record retrieval by URL."""
        mock_opensearch_service.search_records.return_value = {
            "total": 1,
            "results": [{"_id": "record-123", "url": "https://github.com/user/repo"}],
        }

        # Make request
        response = client.get("/records/by-url?url=https%3A//github.com/user/repo")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://github.com/user/repo"
        assert data["total"] == 1
        assert len(data["records"]) == 1

    def test_get_records_by_url_with_normalization(
        self, client, mock_opensearch_service
    ):
        """Test record retrieval with URL normalization."""
        mock_opensearch_service.search_records.return_value = {
            "total": 1,
            "results": [{"_id": "record-123", "url": "https://github.com/user/repo"}],
        }

        # Make request with trailing slash
        response = client.get("/records/by-url?url=https%3A//github.com/user/repo/")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://github.com/user/repo"  # Normalized

    def test_get_records_by_url_not_found(self, client, mock_opensearch_service):
        """Test record retrieval when no records exist."""
        mock_opensearch_service.search_records.return_value = {
            "total": 0,
            "results": [],
        }

        # Make request
        response = client.get("/records/by-url?url=https%3A//github.com/user/repo")

        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "No MetagitRecord found" in data["detail"]


class TestConfigEndpoints:
    """Test config API endpoints."""

    @pytest.fixture
    def mock_opensearch_service(self):
        """Create a mock OpenSearch service."""
        mock_service = MagicMock()
        mock_service.search_records = AsyncMock()
        return mock_service

    @pytest.fixture
    def client(self, mock_opensearch_service):
        """Create a test client with mocked dependencies."""
        # Import here to avoid circular imports
        from metagit.api.app import app
        from metagit.api.dependencies import get_tenant_aware_opensearch_service

        # Override the dependency
        def override_get_tenant_aware_opensearch_service():
            return mock_opensearch_service

        app.dependency_overrides[get_tenant_aware_opensearch_service] = (
            override_get_tenant_aware_opensearch_service
        )

        # Mock the app's lifespan to prevent service startup
        with (
            patch("metagit.api.app.opensearch_service"),
            patch("metagit.api.app.detection_service"),
            patch("metagit.api.app.lifespan"),
        ):
            client = TestClient(app)
            yield client

        # Clean up
        app.dependency_overrides.clear()

    def test_get_config_by_url_success(self, client, mock_opensearch_service):
        """Test successful config retrieval by URL."""
        # Set up mock to return data that matches the expected normalized URL
        mock_opensearch_service.search_records.return_value = {
            "total": 1,
            "results": [
                {
                    "_id": "record-123",
                    "url": "https://github.com/user/repo",  # This should match the normalized URL
                    "name": "test-repo",
                    "kind": "application",
                    "description": "Test repository",
                    "detection_timestamp": "2024-01-01T00:00:00Z",
                    "detection_source": "test",
                    "detection_version": "1.0.0",
                    "branch": "main",
                    "checksum": "abc123",
                    "tenant_id": "default",
                }
            ],
        }

        # Make request with properly encoded URL
        response = client.get("/config/https%3A//github.com/user/repo")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://github.com/user/repo"
        assert data["record_id"] == "record-123"
        assert "config" in data

    def test_get_config_by_url_with_normalization(
        self, client, mock_opensearch_service
    ):
        """Test config retrieval with URL normalization."""
        mock_opensearch_service.search_records.return_value = {
            "total": 1,
            "results": [
                {
                    "_id": "record-123",
                    "url": "https://github.com/user/repo",
                    "name": "test-repo",
                    "description": "Test repository",
                    "detection_timestamp": "2024-01-01T00:00:00Z",
                    "detection_source": "test",
                    "detection_version": "1.0.0",
                    "branch": "main",
                    "checksum": "abc123",
                    "tenant_id": "default",
                }
            ],
        }

        # Make request with trailing slash
        response = client.get("/config/https%3A//github.com/user/repo/")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://github.com/user/repo"  # Normalized


class TestURLNormalizationIntegration:
    """Test URL normalization integration in endpoints."""

    def test_normalize_git_url_function(self):
        """Test the normalize_git_url function directly."""
        test_cases = [
            ("https://github.com/user/repo/", "https://github.com/user/repo"),
            ("https://gitlab.com/user/repo/", "https://gitlab.com/user/repo"),
            ("https://github.com/user/repo", "https://github.com/user/repo"),
            ("", ""),
            (None, None),
        ]

        for input_url, expected in test_cases:
            result = normalize_git_url(input_url)
            assert result == expected
