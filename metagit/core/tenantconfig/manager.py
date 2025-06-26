#!/usr/bin/env python

"""
Manager for tenant-specific configurations.

This module provides a manager for tenant-specific configurations.

It allows loading, saving, and listing tenant configurations.

The manager is responsible for:
  - Loading tenant configurations from a directory
  - Saving tenant configurations to a directory
  - Listing all available tenant configurations
  - Creating default tenant configurations
  - Merging tenant configurations with global configurations

"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from pydantic import Field

from metagit.core.appconfig.models import AppConfig
from metagit.core.tenantconfig.models import TenantConfig
from metagit.core.utils.logging import LoggingModel
from metagit.core.utils.yaml_class import yaml


class TenantConfigManager(LoggingModel):
    """Manager for tenant-specific configurations."""

    config_dir: str = Field(
        default="~/.config/metagit/tenants",
        description="Directory for tenant configuration files",
    )
    default_tenant_config: Optional[TenantConfig] = Field(
        None, description="Default tenant configuration template"
    )

    @classmethod
    def load_tenant_config(
        cls, tenant_id: str, config_dir: str = None
    ) -> Union[TenantConfig, Exception]:
        """
        Load configuration for a specific tenant.

        Args:
            tenant_id: Tenant identifier
            config_dir: Configuration directory (optional)

        Returns:
            TenantConfig or Exception
        """
        try:
            if not config_dir:
                config_dir = os.path.expanduser("~/.config/metagit/tenants")

            config_path = Path.joinpath(config_dir, f"{tenant_id}.yml")

            if not config_path.exists():
                return FileNotFoundError(
                    f"Tenant configuration not found: {config_path}"
                )

            with config_path.open("r") as f:
                config_data = yaml.safe_load(f)

            # Extract tenant config from the loaded data
            if "tenant_config" in config_data:
                tenant_config_data = config_data["tenant_config"]
            else:
                tenant_config_data = config_data

            # Ensure tenant_id is set
            tenant_config_data["tenant_id"] = tenant_id

            return TenantConfig(**tenant_config_data)

        except Exception as e:
            return e

    @classmethod
    def save_tenant_config(
        cls, tenant_config: TenantConfig, config_dir: str = None
    ) -> Union[bool, Exception]:
        """
        Save configuration for a specific tenant.

        Args:
            tenant_config: Tenant configuration to save
            config_dir: Configuration directory (optional)

        Returns:
            True if successful, Exception if failed
        """
        try:
            if not config_dir:
                config_dir = os.path.expanduser("~/.config/metagit/tenants")

            config_path = Path.joinpath(config_dir, f"{tenant_config.tenant_id}.yml")
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with config_path.open("w") as f:
                yaml.dump(
                    {"tenant_config": tenant_config.model_dump()},
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                )

            return True

        except Exception as e:
            return e

    @classmethod
    def list_tenant_configs(cls, config_dir: str = None) -> Union[List[str], Exception]:
        """
        List all available tenant configurations.

        Args:
            config_dir: Configuration directory (optional)

        Returns:
            List of tenant IDs or Exception
        """
        try:
            if not config_dir:
                config_dir = os.path.expanduser("~/.config/metagit/tenants")

            config_path = Path(config_dir)
            if not config_path.exists():
                return []

            tenant_configs = []
            for config_file in config_path.glob("*.yml"):
                tenant_id = config_file.stem
                tenant_configs.append(tenant_id)

            return tenant_configs

        except Exception as e:
            return e

    @classmethod
    def create_default_tenant_config(cls, tenant_id: str) -> TenantConfig:
        """
        Create a default tenant configuration.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Default TenantConfig
        """
        return TenantConfig(
            tenant_id=tenant_id,
            tenant_name=f"Tenant {tenant_id}",
            tenant_description=f"Default configuration for tenant {tenant_id}",
            tenant_max_concurrent_jobs=5,
            tenant_detection_timeout=300,
            tenant_settings={},
            tenant_is_active=True,
            tenant_created_at=datetime.now().isoformat(),
            tenant_updated_at=datetime.now().isoformat(),
        )

    def get_tenant_config(self, tenant_id: str) -> Union[TenantConfig, Exception]:
        """
        Get configuration for a specific tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            TenantAppConfig or Exception
        """
        try:
            # Try to load tenant-specific config
            tenant_config = TenantConfigManager.load_tenant_config(
                tenant_id, self.tenant_config_manager.config_dir
            )

            if isinstance(tenant_config, Exception):
                # If tenant config doesn't exist, create default
                if isinstance(tenant_config, FileNotFoundError):
                    tenant_config = TenantConfigManager.create_default_tenant_config(
                        tenant_id
                    )
                    # Save the default config for future use
                    TenantConfigManager.save_tenant_config(
                        tenant_config, self.tenant_config_manager.config_dir
                    )
                else:
                    return tenant_config

            return tenant_config

        except Exception as e:
            return e

    def merge_tenant_config(self, tenant_id: str) -> Union["AppConfig", Exception]:
        """
        Get a merged configuration that combines global config with tenant-specific config.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Merged AppConfig or Exception
        """
        try:
            # Get tenant-specific config
            tenant_config = self.get_tenant_config(tenant_id)
            if isinstance(tenant_config, Exception):
                return tenant_config

            # Create a copy of the current config
            merged_config = self.model_copy()

            # Merge tenant-specific provider config
            if tenant_config.providers:
                merged_config.providers = tenant_config.providers

            # Merge tenant-specific LLM config
            if tenant_config.llm:
                merged_config.llm = tenant_config.llm

            # Merge tenant-specific workspace config
            if tenant_config.workspace:
                merged_config.workspace = tenant_config.workspace

            return merged_config

        except Exception as e:
            return e
