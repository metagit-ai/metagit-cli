#!/usr/bin/env python
"""
Tenant configuration service for managing per-tenant AppConfigs.
"""

import logging
import os
from typing import Dict, Optional, Union

from metagit.core.appconfig.models import (
    AppConfig,
    TenantAppConfig,
    TenantConfigManager,
)

logger = logging.getLogger(__name__)


class TenantConfigService:
    """Service for managing tenant-specific configurations."""

    def __init__(self, global_config: AppConfig):
        """
        Initialize tenant configuration service.

        Args:
            global_config: Global application configuration
        """
        self.global_config = global_config
        self.tenant_configs: Dict[str, TenantAppConfig] = {}
        self.merged_configs: Dict[str, AppConfig] = {}
        self.config_dir = global_config.tenant_config_manager.config_dir

    def get_tenant_config(self, tenant_id: str) -> Union[TenantAppConfig, Exception]:
        """
        Get tenant-specific configuration.

        Args:
            tenant_id: Tenant identifier

        Returns:
            TenantAppConfig or Exception
        """
        try:
            # Check cache first
            if tenant_id in self.tenant_configs:
                return self.tenant_configs[tenant_id]

            # Load from global config manager
            tenant_config = self.global_config.get_tenant_config(tenant_id)
            if isinstance(tenant_config, Exception):
                return tenant_config

            # Cache the config
            self.tenant_configs[tenant_id] = tenant_config
            return tenant_config

        except Exception as e:
            logger.error(f"Failed to get tenant config for {tenant_id}: {e}")
            return e

    def get_merged_config(self, tenant_id: str) -> Union[AppConfig, Exception]:
        """
        Get merged configuration (global + tenant-specific).

        Args:
            tenant_id: Tenant identifier

        Returns:
            Merged AppConfig or Exception
        """
        try:
            # Check cache first
            if tenant_id in self.merged_configs:
                return self.merged_configs[tenant_id]

            # Get merged config from global config
            merged_config = self.global_config.merge_tenant_config(tenant_id)
            if isinstance(merged_config, Exception):
                return merged_config

            # Cache the merged config
            self.merged_configs[tenant_id] = merged_config
            return merged_config

        except Exception as e:
            logger.error(f"Failed to get merged config for {tenant_id}: {e}")
            return e

    def update_tenant_config(
        self, tenant_id: str, tenant_config: TenantAppConfig
    ) -> Union[bool, Exception]:
        """
        Update tenant-specific configuration.

        Args:
            tenant_id: Tenant identifier
            tenant_config: Updated tenant configuration

        Returns:
            True if successful, Exception if failed
        """
        try:
            # Ensure tenant_id matches
            tenant_config.tenant_id = tenant_id

            # Save to file
            result = TenantConfigManager.save_tenant_config(
                tenant_config, self.config_dir
            )
            if isinstance(result, Exception):
                return result

            # Update cache
            self.tenant_configs[tenant_id] = tenant_config
            # Clear merged config cache for this tenant
            self.merged_configs.pop(tenant_id, None)

            logger.info(f"Updated tenant config for {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update tenant config for {tenant_id}: {e}")
            return e

    def create_tenant_config(
        self, tenant_id: str, **kwargs
    ) -> Union[TenantAppConfig, Exception]:
        """
        Create a new tenant configuration.

        Args:
            tenant_id: Tenant identifier
            **kwargs: Additional configuration parameters

        Returns:
            TenantAppConfig or Exception
        """
        try:
            # Create default config
            tenant_config = TenantConfigManager.create_default_tenant_config(tenant_id)

            # Apply any additional parameters
            for key, value in kwargs.items():
                if hasattr(tenant_config, key):
                    setattr(tenant_config, key, value)

            # Save the config
            result = self.update_tenant_config(tenant_id, tenant_config)
            if isinstance(result, Exception):
                return result

            return tenant_config

        except Exception as e:
            logger.error(f"Failed to create tenant config for {tenant_id}: {e}")
            return e

    def delete_tenant_config(self, tenant_id: str) -> Union[bool, Exception]:
        """
        Delete tenant configuration.

        Args:
            tenant_id: Tenant identifier

        Returns:
            True if successful, Exception if failed
        """
        try:
            import os
            from pathlib import Path

            # Remove from cache
            self.tenant_configs.pop(tenant_id, None)
            self.merged_configs.pop(tenant_id, None)

            # Delete file
            config_path = Path(self.config_dir) / f"{tenant_id}.yml"
            if config_path.exists():
                config_path.unlink()

            logger.info(f"Deleted tenant config for {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete tenant config for {tenant_id}: {e}")
            return e

    def list_tenant_configs(self) -> Union[list[str], Exception]:
        """
        List all available tenant configurations.

        Returns:
            List of tenant IDs or Exception
        """
        try:
            return TenantConfigManager.list_tenant_configs(self.config_dir)
        except Exception as e:
            logger.error(f"Failed to list tenant configs: {e}")
            return e

    def get_tenant_providers(self, tenant_id: str) -> Union[Dict, Exception]:
        """
        Get provider configuration for a specific tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Provider configuration or Exception
        """
        try:
            tenant_config = self.get_tenant_config(tenant_id)
            if isinstance(tenant_config, Exception):
                return tenant_config

            return tenant_config.providers.model_dump()

        except Exception as e:
            logger.error(f"Failed to get providers for tenant {tenant_id}: {e}")
            return e

    def get_tenant_llm_config(self, tenant_id: str) -> Union[Dict, Exception]:
        """
        Get LLM configuration for a specific tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            LLM configuration or Exception
        """
        try:
            tenant_config = self.get_tenant_config(tenant_id)
            if isinstance(tenant_config, Exception):
                return tenant_config

            return tenant_config.llm.model_dump()

        except Exception as e:
            logger.error(f"Failed to get LLM config for tenant {tenant_id}: {e}")
            return e

    def get_tenant_settings(self, tenant_id: str) -> Union[Dict, Exception]:
        """
        Get custom settings for a specific tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Custom settings or Exception
        """
        try:
            tenant_config = self.get_tenant_config(tenant_id)
            if isinstance(tenant_config, Exception):
                return tenant_config

            return tenant_config.settings

        except Exception as e:
            logger.error(f"Failed to get settings for tenant {tenant_id}: {e}")
            return e

    def update_tenant_setting(
        self, tenant_id: str, key: str, value: any
    ) -> Union[bool, Exception]:
        """
        Update a specific setting for a tenant.

        Args:
            tenant_id: Tenant identifier
            key: Setting key
            value: Setting value

        Returns:
            True if successful, Exception if failed
        """
        try:
            tenant_config = self.get_tenant_config(tenant_id)
            if isinstance(tenant_config, Exception):
                return tenant_config

            # Update the setting
            tenant_config.settings[key] = value

            # Save the updated config
            return self.update_tenant_config(tenant_id, tenant_config)

        except Exception as e:
            logger.error(f"Failed to update setting {key} for tenant {tenant_id}: {e}")
            return e

    def clear_cache(self, tenant_id: Optional[str] = None) -> None:
        """
        Clear configuration cache.

        Args:
            tenant_id: Specific tenant to clear (None for all)
        """
        if tenant_id:
            self.tenant_configs.pop(tenant_id, None)
            self.merged_configs.pop(tenant_id, None)
            logger.debug(f"Cleared cache for tenant {tenant_id}")
        else:
            self.tenant_configs.clear()
            self.merged_configs.clear()
            logger.debug("Cleared all tenant config caches")
