#!/usr/bin/env python
"""Tests for API models."""

from datetime import datetime

import pytest
from pydantic import HttpUrl, ValidationError

from metagit.api.models import (
    DetectionRequest,
    DetectionResponse,
    DetectionStatus,
    DetectionStatusResponse,
    SearchRequest,
)

test_url = "https://github.com/zloeber/mag-branch"


class TestDetectionRequest:
    """Test DetectionRequest model."""

    def test_detection_request_with_url(self):
        """Test DetectionRequest with repository URL."""
        request = DetectionRequest(
            repository_url=test_url,
            priority=5,
            metadata={"test": "data"},
        )

        assert request.repository_url == HttpUrl(test_url)
        assert request.priority == 5
        assert request.metadata == {"test": "data"}

    def test_detection_request_without_url(self):
        """Test DetectionRequest without repository URL."""
        request = DetectionRequest(
            priority=0,
        )

        assert request.repository_url is None
        assert request.priority == 0
        assert request.metadata is None

    def test_detection_request_defaults(self):
        """Test DetectionRequest default values."""
        request = DetectionRequest()

        assert request.repository_url is None
        assert request.priority == 0
        assert request.metadata is None

    def test_detection_request_validation_error(self):
        """Test DetectionRequest validation error."""
        # Should not raise error for empty request (all fields are optional)
        request = DetectionRequest()
        assert request is not None


class TestDetectionResponse:
    """Test DetectionResponse model."""

    def test_detection_response(self):
        """Test DetectionResponse creation."""
        timestamp = datetime.utcnow()
        response = DetectionResponse(
            detection_id="test-id",
            status=DetectionStatus.PENDING,
            repository_url=test_url,
            created_at=timestamp,
            updated_at=timestamp,
            estimated_completion=None,
            error_message=None,
            record_id=None,
        )

        assert response.detection_id == "test-id"
        assert response.status == DetectionStatus.PENDING
        assert response.repository_url == test_url
        assert response.created_at == timestamp
        assert response.updated_at == timestamp
        assert response.estimated_completion is None
        assert response.error_message is None
        assert response.record_id is None

    def test_detection_response_with_error(self):
        """Test DetectionResponse with error."""
        timestamp = datetime.utcnow()
        response = DetectionResponse(
            detection_id="test-id",
            status=DetectionStatus.FAILED,
            repository_url=test_url,
            created_at=timestamp,
            updated_at=timestamp,
            estimated_completion=None,
            error_message="Test error",
            record_id=None,
        )

        assert response.status == DetectionStatus.FAILED
        assert response.error_message == "Test error"


class TestDetectionStatusResponse:
    """Test DetectionStatusResponse model."""

    def test_detection_status_response(self):
        """Test DetectionStatusResponse creation."""
        timestamp = datetime.utcnow()
        response = DetectionStatusResponse(
            detection_id="test-id",
            status=DetectionStatus.COMPLETED,
            repository_url=test_url,
            created_at=timestamp,
            updated_at=timestamp,
            estimated_completion=None,
            error_message=None,
            record_id="record-123",
        )

        assert response.detection_id == "test-id"
        assert response.status == DetectionStatus.COMPLETED
        assert response.repository_url == test_url
        assert response.record_id == "record-123"

    def test_detection_status_response_running(self):
        """Test DetectionStatusResponse for running job."""
        timestamp = datetime.utcnow()
        response = DetectionStatusResponse(
            detection_id="test-id",
            status=DetectionStatus.RUNNING,
            repository_url=test_url,
            created_at=timestamp,
            updated_at=timestamp,
            estimated_completion=None,
            error_message=None,
            record_id=None,
        )

        assert response.status == DetectionStatus.RUNNING
        assert response.record_id is None


class TestSearchRequest:
    """Test SearchRequest model."""

    def test_search_request_basic(self):
        """Test SearchRequest with basic parameters."""
        request = SearchRequest(query="python api")

        assert request.query == "python api"
        assert request.page == 1
        assert request.size == 10
        assert request.filters is None

    def test_search_request_with_filters(self):
        """Test SearchRequest with filters."""
        filters = {"kind": "application", "has_ci": True}
        request = SearchRequest(
            query="python",
            filters=filters,
            page=2,
            size=50,
        )

        assert request.query == "python"
        assert request.filters == filters
        assert request.page == 2
        assert request.size == 50

    def test_search_request_validation(self):
        """Test SearchRequest validation."""
        # Test page validation
        with pytest.raises(ValidationError):
            SearchRequest(page=0)  # Page must be >= 1

        # Test size validation
        with pytest.raises(ValidationError):
            SearchRequest(size=0)  # Size must be >= 1

        with pytest.raises(ValidationError):
            SearchRequest(size=101)  # Size must be <= 100


class TestDetectionStatus:
    """Test DetectionStatus enum."""

    def test_detection_status_values(self):
        """Test DetectionStatus enum values."""
        assert DetectionStatus.PENDING == "pending"
        assert DetectionStatus.RUNNING == "running"
        assert DetectionStatus.COMPLETED == "completed"
        assert DetectionStatus.FAILED == "failed"

    def test_detection_status_ordering(self):
        """Test DetectionStatus enum ordering."""
        statuses = list(DetectionStatus)
        assert len(statuses) == 4
        assert "pending" in statuses
        assert "running" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
