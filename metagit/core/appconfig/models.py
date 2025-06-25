#!/usr/bin/env python

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from metagit import DATA_PATH, __version__
from metagit.core.config.models import (
    LLM,
    Boundary,
    Profiles,
    Providers,
    TenantConfig,
    WorkspaceConfig,
)
from metagit.core.utils.yaml_class import yaml

success_blurb: str = "Success! ✅"
failure_blurb: str = "Failed! ❌"


class TenantAppConfig(BaseModel):
    """Per-tenant application configuration."""

    tenant_id: str = Field(..., description="Tenant identifier")
    name: str = Field(default="", description="Tenant display name")
    description: str = Field(default="", description="Tenant description")

    # Provider configuration for this tenant
    providers: Providers = Field(
        default=Providers(),
        description="Git provider plugin configuration for this tenant",
    )

    # LLM configuration for this tenant
    llm: LLM = Field(default=LLM(), description="LLM configuration for this tenant")

    # Workspace configuration for this tenant
    workspace: WorkspaceConfig = Field(
        default=WorkspaceConfig(), description="Workspace configuration for this tenant"
    )

    # Detection settings for this tenant
    max_concurrent_jobs: int = Field(
        default=5, description="Maximum concurrent detection jobs for this tenant"
    )
    detection_timeout: int = Field(
        default=300, description="Detection timeout in seconds for this tenant"
    )

    # Custom settings for this tenant
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Custom tenant-specific settings"
    )

    # Metadata
    created_at: Optional[str] = Field(None, description="Tenant creation timestamp")
    updated_at: Optional[str] = Field(None, description="Tenant last update timestamp")
    is_active: bool = Field(default=True, description="Whether tenant is active")

    class Config:
        """Pydantic configuration."""

        extra = "allow"


class TenantConfigManager(BaseModel):
    """Manager for tenant-specific configurations."""

    config_dir: str = Field(
        default="~/.config/metagit/tenants",
        description="Directory for tenant configuration files",
    )
    default_tenant_config: Optional[TenantAppConfig] = Field(
        None, description="Default tenant configuration template"
    )

    @classmethod
    def load_tenant_config(
        cls, tenant_id: str, config_dir: str = None
    ) -> Union[TenantAppConfig, Exception]:
        """
        Load configuration for a specific tenant.

        Args:
            tenant_id: Tenant identifier
            config_dir: Configuration directory (optional)

        Returns:
            TenantAppConfig or Exception
        """
        try:
            if not config_dir:
                config_dir = os.path.expanduser("~/.config/metagit/tenants")

            config_path = Path(config_dir) / f"{tenant_id}.yml"

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

            return TenantAppConfig(**tenant_config_data)

        except Exception as e:
            return e

    @classmethod
    def save_tenant_config(
        cls, tenant_config: TenantAppConfig, config_dir: str = None
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

            config_path = Path(config_dir) / f"{tenant_config.tenant_id}.yml"
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
    def create_default_tenant_config(cls, tenant_id: str) -> TenantAppConfig:
        """
        Create a default tenant configuration.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Default TenantAppConfig
        """
        return TenantAppConfig(
            tenant_id=tenant_id,
            name=f"Tenant {tenant_id}",
            description=f"Default configuration for tenant {tenant_id}",
            providers=Providers(),
            llm=LLM(),
            workspace=WorkspaceConfig(),
            max_concurrent_jobs=5,
            detection_timeout=300,
            settings={},
            is_active=True,
        )


class AppConfig(BaseModel):
    version: str = Field(default=__version__, description="The version of the CLI")
    description: str = "Metagit configuration"
    editor: str = Field(default="code", description="The editor to use for the CLI")
    # Reserved for future use
    api_url: str = Field(default="", description="The API URL to use for the CLI")
    # Reserved for future use
    api_version: str = Field(
        default="", description="The API version to use for the CLI"
    )
    # Reserved for future use
    api_key: str = Field(default="", description="The API key to use for the CLI")
    # Reserved for future use
    cicd_file_data: str = Field(
        default="", description="The path to the cicd file data"
    )
    file_type_data: str = Field(
        default="", description="The path to the file type data"
    )
    package_manager_data: str = Field(
        default="", description="The path to the package manager data"
    )
    default_project: str = Field(
        default="", description="The default project to use for the CLI"
    )
    llm: LLM = Field(default=LLM(), description="The LLM configuration")
    workspace: WorkspaceConfig = Field(
        default=WorkspaceConfig(), description="The workspace configuration"
    )
    profiles: Profiles = Field(
        default=Profiles(), description="The profiles configuration"
    )
    providers: Providers = Field(
        default=Providers(), description="Git provider plugin configuration"
    )
    tenant: TenantConfig = Field(
        default=TenantConfig(), description="Tenant configuration"
    )
    # Tenant configuration management
    tenant_config_manager: TenantConfigManager = Field(
        default=TenantConfigManager(), description="Tenant configuration manager"
    )

    @classmethod
    def load(cls, config_path: str = None) -> Union["AppConfig", Exception]:
        """
        Load AppConfig from file.

        Args:
            config_path: Path to configuration file (optional)

        Returns:
            AppConfig object or Exception
        """
        try:
            if not config_path:
                config_path = Path.joinpath(
                    Path.home(), ".config", "metagit", "config.yml"
                )

            config_file = Path(config_path)
            if not config_file.exists():
                return cls()

            with config_file.open("r") as f:
                config_data = yaml.safe_load(f)

            if "config" in config_data:
                config = cls(**config_data["config"])
            else:
                config = cls(**config_data)

            # Override with environment variables
            config = cls._override_from_environment(config)

            return config

        except Exception as e:
            return e

    @classmethod
    def _override_from_environment(cls, config: "AppConfig") -> "AppConfig":
        """
        Override configuration with environment variables.

        Args:
            config: AppConfig to override

        Returns:
            Updated AppConfig
        """
        # LLM configuration
        if os.getenv("METAGIT_LLM_ENABLED"):
            config.llm.enabled = os.getenv("METAGIT_LLM_ENABLED").lower() == "true"
        if os.getenv("METAGIT_LLM_PROVIDER"):
            config.llm.provider = os.getenv("METAGIT_LLM_PROVIDER")
        if os.getenv("METAGIT_LLM_PROVIDER_MODEL"):
            config.llm.provider_model = os.getenv("METAGIT_LLM_PROVIDER_MODEL")
        if os.getenv("METAGIT_LLM_EMBEDDER"):
            config.llm.embedder = os.getenv("METAGIT_LLM_EMBEDDER")
        if os.getenv("METAGIT_LLM_EMBEDDER_MODEL"):
            config.llm.embedder_model = os.getenv("METAGIT_LLM_EMBEDDER_MODEL")
        if os.getenv("METAGIT_LLM_API_KEY"):
            config.llm.api_key = os.getenv("METAGIT_LLM_API_KEY")

        # API configuration
        if os.getenv("METAGIT_API_KEY"):
            config.api_key = os.getenv("METAGIT_API_KEY")
        if os.getenv("METAGIT_API_URL"):
            config.api_url = os.getenv("METAGIT_API_URL")
        if os.getenv("METAGIT_API_VERSION"):
            config.api_version = os.getenv("METAGIT_API_VERSION")

        # Workspace configuration
        if os.getenv("METAGIT_WORKSPACE_PATH"):
            config.workspace.path = os.getenv("METAGIT_WORKSPACE_PATH")
        if os.getenv("METAGIT_WORKSPACE_DEFAULT_PROJECT"):
            config.workspace.default_project = os.getenv(
                "METAGIT_WORKSPACE_DEFAULT_PROJECT"
            )

        # Profiles configuration
        if os.getenv("METAGIT_PROFILES_CONFIG_PATH"):
            config.profiles.profile_config_path = os.getenv(
                "METAGIT_PROFILES_CONFIG_PATH"
            )
        if os.getenv("METAGIT_PROFILES_DEFAULT_PROFILE"):
            config.profiles.default_profile = os.getenv(
                "METAGIT_PROFILES_DEFAULT_PROFILE"
            )

        # GitHub provider configuration
        if os.getenv("METAGIT_GITHUB_ENABLED"):
            config.providers.github.enabled = (
                os.getenv("METAGIT_GITHUB_ENABLED").lower() == "true"
            )
        if os.getenv("METAGIT_GITHUB_API_TOKEN"):
            config.providers.github.api_token = os.getenv("METAGIT_GITHUB_API_TOKEN")
        if os.getenv("METAGIT_GITHUB_BASE_URL"):
            config.providers.github.base_url = os.getenv("METAGIT_GITHUB_BASE_URL")

        # GitLab provider configuration
        if os.getenv("METAGIT_GITLAB_ENABLED"):
            config.providers.gitlab.enabled = (
                os.getenv("METAGIT_GITLAB_ENABLED").lower() == "true"
            )
        if os.getenv("METAGIT_GITLAB_API_TOKEN"):
            config.providers.gitlab.api_token = os.getenv("METAGIT_GITLAB_API_TOKEN")
        if os.getenv("METAGIT_GITLAB_BASE_URL"):
            config.providers.gitlab.base_url = os.getenv("METAGIT_GITLAB_BASE_URL")

        # Tenant configuration
        if os.getenv("METAGIT_TENANT_ENABLED"):
            config.tenant.enabled = (
                os.getenv("METAGIT_TENANT_ENABLED").lower() == "true"
            )
        if os.getenv("METAGIT_TENANT_DEFAULT"):
            config.tenant.default_tenant = os.getenv("METAGIT_TENANT_DEFAULT")
        if os.getenv("METAGIT_TENANT_HEADER"):
            config.tenant.tenant_header = os.getenv("METAGIT_TENANT_HEADER")
        if os.getenv("METAGIT_TENANT_REQUIRED"):
            config.tenant.tenant_required = (
                os.getenv("METAGIT_TENANT_REQUIRED").lower() == "true"
            )
        if os.getenv("METAGIT_TENANT_ALLOWED"):
            config.tenant.allowed_tenants = os.getenv("METAGIT_TENANT_ALLOWED").split(
                ","
            )

        return config

    def save(self, config_path: str = None) -> Union[bool, Exception]:
        """
        Save AppConfig to file.

        Args:
            config_path: Path to save configuration file (optional)

        Returns:
            True if successful, Exception if failed
        """
        try:
            if not config_path:
                config_path = Path.joinpath(
                    Path.home(), ".config", "metagit", "config.yml"
                )

            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with config_file.open("w") as f:
                yaml.dump(
                    {"config": self.model_dump()},
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                )

            return True
        except Exception as e:
            return e

    def get_tenant_config(self, tenant_id: str) -> Union[TenantAppConfig, Exception]:
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
