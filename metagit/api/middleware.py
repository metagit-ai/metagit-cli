#!/usr/bin/env python
"""
Middleware for handling tenant context in the metagit API.
"""

import logging
from typing import Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from metagit.core.appconfig.models import AppConfig

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware for handling tenant context."""

    def __init__(self, app, app_config: AppConfig):
        super().__init__(app)
        self.config = app_config.tenant
        # System endpoints that don't require tenant validation
        self.system_endpoints = {
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/providers",
            "/index-info",
        }

    async def dispatch(self, request: Request, call_next):
        """Process request and add tenant context."""
        # Skip tenant validation for system endpoints
        if request.url.path in self.system_endpoints:
            # Set default tenant for system endpoints
            request.state.tenant_id = self.config.default_tenant
            response = await call_next(request)
            return response

        # Extract tenant from header or query param
        tenant_id = self._extract_tenant_id(request)

        # Validate tenant if required
        if self.config.tenant_required and not tenant_id:
            raise HTTPException(
                status_code=400,
                detail=f"Tenant ID required. Use header '{self.config.tenant_header}' or query parameter 'tenant_id'",
            )

        if (
            tenant_id
            and self.config.allowed_tenants
            and tenant_id not in self.config.allowed_tenants
        ):
            raise HTTPException(
                status_code=403,
                detail=f"Tenant '{tenant_id}' not authorized. Allowed tenants: {', '.join(self.config.allowed_tenants)}",
            )

        # Add tenant to request state
        request.state.tenant_id = tenant_id or self.config.default_tenant

        # Log tenant context for debugging
        if self.config.enabled:
            logger.debug(f"Request for tenant: {request.state.tenant_id}")

        response = await call_next(request)
        return response

    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request headers or query parameters."""
        # Try header first
        tenant_id = request.headers.get(self.config.tenant_header)
        if tenant_id:
            return tenant_id.strip()

        # Try query parameter
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id.strip()

        return None
