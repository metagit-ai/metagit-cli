#!/usr/bin/env python
"""
Unit tests for tenant middleware functionality.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from metagit.api.middleware import TenantMiddleware
from metagit.core.appconfig.models import AppConfig


class TestTenantMiddleware:
    """Test tenant middleware functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app_config = AppConfig()
        self.app_config.tenant.enabled = True
        self.app_config.tenant.tenant_required = True
        self.app_config.tenant.tenant_header = "X-Tenant-ID"
        self.app_config.tenant.allowed_tenants = ["tenant-a", "tenant-b", "default"]

    def create_mock_request(self, headers=None, query_params=None):
        """Create a mock request for testing."""
        request = MagicMock()
        request.headers = headers or {}
        request.query_params = query_params or {}
        request.state = MagicMock()
        return request

    @pytest.mark.asyncio
    async def test_middleware_extract_tenant_from_header(self):
        """Test extracting tenant ID from header."""
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request(headers={"X-Tenant-ID": "tenant-a"})
        call_next = AsyncMock()

        await middleware.dispatch(request, call_next)

        assert request.state.tenant_id == "tenant-a"
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_extract_tenant_from_query(self):
        """Test extracting tenant ID from query parameter."""
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request(query_params={"tenant_id": "tenant-b"})
        call_next = AsyncMock()

        await middleware.dispatch(request, call_next)

        assert request.state.tenant_id == "tenant-b"
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_header_priority_over_query(self):
        """Test that header takes priority over query parameter."""
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request(
            headers={"X-Tenant-ID": "tenant-a"}, query_params={"tenant_id": "tenant-b"}
        )
        call_next = AsyncMock()

        await middleware.dispatch(request, call_next)

        assert request.state.tenant_id == "tenant-a"
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_tenant_required_missing(self):
        """Test middleware rejects request when tenant is required but missing."""
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request()
        call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)

        assert exc_info.value.status_code == 400
        assert "Tenant ID required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_middleware_tenant_not_required_missing(self):
        """Test middleware uses default tenant when not required and missing."""
        self.app_config.tenant.tenant_required = False
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request()
        call_next = AsyncMock()

        await middleware.dispatch(request, call_next)

        assert request.state.tenant_id == "default"
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_unauthorized_tenant(self):
        """Test middleware rejects unauthorized tenant."""
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request(
            headers={"X-Tenant-ID": "unauthorized-tenant"}
        )
        call_next = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)

        assert exc_info.value.status_code == 403
        assert "not authorized" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_middleware_authorized_tenant(self):
        """Test middleware accepts authorized tenant."""
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request(headers={"X-Tenant-ID": "tenant-a"})
        call_next = AsyncMock()

        await middleware.dispatch(request, call_next)

        assert request.state.tenant_id == "tenant-a"
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_empty_allowed_tenants(self):
        """Test middleware accepts any tenant when allowed_tenants is empty."""
        self.app_config.tenant.allowed_tenants = []
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request(headers={"X-Tenant-ID": "any-tenant"})
        call_next = AsyncMock()

        await middleware.dispatch(request, call_next)

        assert request.state.tenant_id == "any-tenant"
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_whitespace_handling(self):
        """Test middleware handles whitespace in tenant IDs."""
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request(headers={"X-Tenant-ID": "  tenant-a  "})
        call_next = AsyncMock()

        await middleware.dispatch(request, call_next)

        assert request.state.tenant_id == "tenant-a"
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_custom_header(self):
        """Test middleware works with custom tenant header."""
        self.app_config.tenant.tenant_header = "X-Custom-Tenant"
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request(headers={"X-Custom-Tenant": "tenant-a"})
        call_next = AsyncMock()

        await middleware.dispatch(request, call_next)

        assert request.state.tenant_id == "tenant-a"
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_error_handling(self):
        """Test middleware handles errors gracefully."""
        app = MagicMock()
        middleware = TenantMiddleware(app, self.app_config)

        request = self.create_mock_request(headers={"X-Tenant-ID": "tenant-a"})
        call_next = AsyncMock(side_effect=Exception("Test error"))

        with pytest.raises(Exception) as exc_info:
            await middleware.dispatch(request, call_next)

        assert str(exc_info.value) == "Test error"
