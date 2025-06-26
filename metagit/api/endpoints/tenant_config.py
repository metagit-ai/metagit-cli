#!/usr/bin/env python
"""
API endpoints for managing tenant configurations.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from metagit.api.tenant_config import TenantConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenant-config", tags=["tenant-config"])


class TenantConfigResponse(BaseModel):
    """Response model for tenant configuration."""

    tenant_id: str
    name: str
    description: str
    providers: Dict[str, Any]
    llm: Dict[str, Any]
    workspace: Dict[str, Any]
    max_concurrent_jobs: int
    detection_timeout: int
    settings: Dict[str, Any]
    is_active: bool


class TenantConfigUpdateRequest(BaseModel):
    """Request model for updating tenant configuration."""

    name: Optional[str] = None
    description: Optional[str] = None
    providers: Optional[Dict[str, Any]] = None
    llm: Optional[Dict[str, Any]] = None
    workspace: Optional[Dict[str, Any]] = None
    max_concurrent_jobs: Optional[int] = None
    detection_timeout: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TenantSettingUpdateRequest(BaseModel):
    """Request model for updating a specific tenant setting."""

    key: str
    value: Any


def get_tenant_config_service(request: Request) -> TenantConfigService:
    """Get tenant configuration service from request state."""
    if not hasattr(request.app.state, "tenant_config_service"):
        raise HTTPException(
            status_code=503, detail="Tenant configuration service not available"
        )
    return request.app.state.tenant_config_service


@router.get("/", response_model=TenantConfigResponse)
async def get_tenant_config(
    request: Request,
    tenant_config_service: TenantConfigService = Depends(get_tenant_config_service),
):
    """Get configuration for the current tenant."""
    tenant_id = request.state.tenant_id

    tenant_config = tenant_config_service.get_tenant_config(tenant_id)
    if isinstance(tenant_config, Exception):
        raise HTTPException(
            status_code=500, detail=f"Failed to get tenant config: {tenant_config}"
        )

    return TenantConfigResponse(
        tenant_id=tenant_config.tenant_id,
        name=tenant_config.name,
        description=tenant_config.description,
        providers=tenant_config.providers.model_dump(),
        llm=tenant_config.llm.model_dump(),
        workspace=tenant_config.workspace.model_dump(),
        max_concurrent_jobs=tenant_config.max_concurrent_jobs,
        detection_timeout=tenant_config.detection_timeout,
        settings=tenant_config.settings,
        is_active=tenant_config.is_active,
    )


@router.put("/", response_model=TenantConfigResponse)
async def update_tenant_config(
    config_update: TenantConfigUpdateRequest,
    request: Request,
    tenant_config_service: TenantConfigService = Depends(get_tenant_config_service),
):
    """Update configuration for the current tenant."""
    tenant_id = request.state.tenant_id

    # Get current config
    current_config = tenant_config_service.get_tenant_config(tenant_id)
    if isinstance(current_config, Exception):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get current tenant config: {current_config}",
        )

    # Update fields if provided
    if config_update.name is not None:
        current_config.name = config_update.name
    if config_update.description is not None:
        current_config.description = config_update.description
    if config_update.max_concurrent_jobs is not None:
        current_config.max_concurrent_jobs = config_update.max_concurrent_jobs
    if config_update.detection_timeout is not None:
        current_config.detection_timeout = config_update.detection_timeout
    if config_update.is_active is not None:
        current_config.is_active = config_update.is_active

    # Update nested objects if provided
    if config_update.providers is not None:
        current_config.providers = current_config.providers.model_validate(
            config_update.providers
        )
    if config_update.llm is not None:
        current_config.llm = current_config.llm.model_validate(config_update.llm)
    if config_update.workspace is not None:
        current_config.workspace = current_config.workspace.model_validate(
            config_update.workspace
        )
    if config_update.settings is not None:
        current_config.settings.update(config_update.settings)

    # Save updated config
    result = tenant_config_service.update_tenant_config(tenant_id, current_config)
    if isinstance(result, Exception):
        raise HTTPException(
            status_code=500, detail=f"Failed to update tenant config: {result}"
        )

    return TenantConfigResponse(
        tenant_id=current_config.tenant_id,
        name=current_config.name,
        description=current_config.description,
        providers=current_config.providers.model_dump(),
        llm=current_config.llm.model_dump(),
        workspace=current_config.workspace.model_dump(),
        max_concurrent_jobs=current_config.max_concurrent_jobs,
        detection_timeout=current_config.detection_timeout,
        settings=current_config.settings,
        is_active=current_config.is_active,
    )


@router.get("/providers")
async def get_tenant_providers(
    request: Request,
    tenant_config_service: TenantConfigService = Depends(get_tenant_config_service),
):
    """Get provider configuration for the current tenant."""
    tenant_id = request.state.tenant_id

    providers = tenant_config_service.get_tenant_providers(tenant_id)
    if isinstance(providers, Exception):
        raise HTTPException(
            status_code=500, detail=f"Failed to get tenant providers: {providers}"
        )

    return {"tenant_id": tenant_id, "providers": providers}


@router.get("/llm")
async def get_tenant_llm_config(
    request: Request,
    tenant_config_service: TenantConfigService = Depends(get_tenant_config_service),
):
    """Get LLM configuration for the current tenant."""
    tenant_id = request.state.tenant_id

    llm_config = tenant_config_service.get_tenant_llm_config(tenant_id)
    if isinstance(llm_config, Exception):
        raise HTTPException(
            status_code=500, detail=f"Failed to get tenant LLM config: {llm_config}"
        )

    return {"tenant_id": tenant_id, "llm": llm_config}


@router.get("/settings")
async def get_tenant_settings(
    request: Request,
    tenant_config_service: TenantConfigService = Depends(get_tenant_config_service),
):
    """Get custom settings for the current tenant."""
    tenant_id = request.state.tenant_id

    settings = tenant_config_service.get_tenant_settings(tenant_id)
    if isinstance(settings, Exception):
        raise HTTPException(
            status_code=500, detail=f"Failed to get tenant settings: {settings}"
        )

    return {"tenant_id": tenant_id, "settings": settings}


@router.put("/settings/{key}")
async def update_tenant_setting(
    key: str,
    setting_update: TenantSettingUpdateRequest,
    request: Request,
    tenant_config_service: TenantConfigService = Depends(get_tenant_config_service),
):
    """Update a specific setting for the current tenant."""
    tenant_id = request.state.tenant_id

    result = tenant_config_service.update_tenant_setting(
        tenant_id, key, setting_update.value
    )
    if isinstance(result, Exception):
        raise HTTPException(
            status_code=500, detail=f"Failed to update tenant setting: {result}"
        )

    return {
        "tenant_id": tenant_id,
        "key": key,
        "value": setting_update.value,
        "updated": True,
    }


@router.get("/merged")
async def get_merged_config(
    request: Request,
    tenant_config_service: TenantConfigService = Depends(get_tenant_config_service),
):
    """Get merged configuration (global + tenant-specific) for the current tenant."""
    tenant_id = request.state.tenant_id

    merged_config = tenant_config_service.get_merged_config(tenant_id)
    if isinstance(merged_config, Exception):
        raise HTTPException(
            status_code=500, detail=f"Failed to get merged config: {merged_config}"
        )

    return {
        "tenant_id": tenant_id,
        "merged_config": merged_config.model_dump(),
    }


# Admin endpoints (for system administrators)
@router.get("/admin/list")
async def list_all_tenant_configs(
    request: Request,
    tenant_config_service: TenantConfigService = Depends(get_tenant_config_service),
):
    """List all tenant configurations (admin only)."""
    # TODO: Add admin authorization check
    tenant_id = request.state.tenant_id

    # For now, only allow default tenant to list all configs
    if tenant_id != "default":
        raise HTTPException(status_code=403, detail="Admin access required")

    tenant_configs = tenant_config_service.list_tenant_configs()
    if isinstance(tenant_configs, Exception):
        raise HTTPException(
            status_code=500, detail=f"Failed to list tenant configs: {tenant_configs}"
        )

    return {"tenant_configs": tenant_configs}


@router.post("/admin/create/{new_tenant_id}")
async def create_tenant_config(
    new_tenant_id: str,
    config_update: TenantConfigUpdateRequest,
    request: Request,
    tenant_config_service: TenantConfigService = Depends(get_tenant_config_service),
):
    """Create a new tenant configuration (admin only)."""
    # TODO: Add admin authorization check
    tenant_id = request.state.tenant_id

    # For now, only allow default tenant to create new configs
    if tenant_id != "default":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Create new tenant config
    new_config = tenant_config_service.create_tenant_config(
        new_tenant_id, **config_update.model_dump(exclude_none=True)
    )
    if isinstance(new_config, Exception):
        raise HTTPException(
            status_code=500, detail=f"Failed to create tenant config: {new_config}"
        )

    return TenantConfigResponse(
        tenant_id=new_config.tenant_id,
        name=new_config.name,
        description=new_config.description,
        providers=new_config.providers.model_dump(),
        llm=new_config.llm.model_dump(),
        workspace=new_config.workspace.model_dump(),
        max_concurrent_jobs=new_config.max_concurrent_jobs,
        detection_timeout=new_config.detection_timeout,
        settings=new_config.settings,
        is_active=new_config.is_active,
    )


@router.delete("/admin/{target_tenant_id}")
async def delete_tenant_config(
    target_tenant_id: str,
    request: Request,
    tenant_config_service: TenantConfigService = Depends(get_tenant_config_service),
):
    """Delete a tenant configuration (admin only)."""
    # TODO: Add admin authorization check
    tenant_id = request.state.tenant_id

    # For now, only allow default tenant to delete configs
    if tenant_id != "default":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = tenant_config_service.delete_tenant_config(target_tenant_id)
    if isinstance(result, Exception):
        raise HTTPException(
            status_code=500, detail=f"Failed to delete tenant config: {result}"
        )

    return {"tenant_id": target_tenant_id, "deleted": True}
