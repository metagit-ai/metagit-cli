#!/usr/bin/env python

import os
from pathlib import Path
from typing import Union

from pydantic import BaseModel, Field

from metagit import DATA_PATH, __version__
from metagit.core.utils.yaml_class import yaml

success_blurb: str = "Success! ✅"
failure_blurb: str = "Failed! ❌"


class Boundary(BaseModel):
    name: str = Field(description="The name of the boundary")
    values: list[str] = Field(description="The values of the boundary")


class Profiles(BaseModel):
    profile_config_path: str = Field(
        default="~/.config/metagit/profiles",
        description="The path to the profile config",
    )
    default_profile: str = Field(
        default="default", description="The default profile to use for the CLI"
    )
    boundaries: list[Boundary] = Field(
        default=[],
        description="""
        The boundaries to use for the CLI. This is used to determine which repositories are part of the organization and which are not.
        Anything defined within a boundary are considered internal to the organization.
        """,
    )


class Workspace(BaseModel):
    path: str = Field(default="./.metagit", description="The path to the workspace")
    default_project: str = Field(
        default="default", description="The default project to use for the CLI"
    )


class LLM(BaseModel):
    enabled: bool = Field(default=False, description="Whether the LLM is enabled")
    provider: str = Field(
        default="openrouter", description="The provider to use for the CLI"
    )
    provider_model: str = Field(
        default="gpt-4o-mini", description="The provider model to use for the CLI"
    )
    embedder: str = Field(
        default="ollama", description="The embedder to use for the CLI"
    )
    embedder_model: str = Field(
        default="nomic-embed-text", description="The embedder model to use for the CLI"
    )
    api_key: str = Field(default="", description="The API key to use for the CLI")


class GitHubProvider(BaseModel):
    enabled: bool = Field(
        default=False, description="Whether GitHub provider is enabled"
    )
    api_token: str = Field(default="", description="GitHub Personal Access Token")
    base_url: str = Field(
        default="https://api.github.com",
        description="GitHub API base URL (for GitHub Enterprise)",
    )


class GitLabProvider(BaseModel):
    enabled: bool = Field(
        default=False, description="Whether GitLab provider is enabled"
    )
    api_token: str = Field(default="", description="GitLab Personal Access Token")
    base_url: str = Field(
        default="https://gitlab.com/api/v4",
        description="GitLab API base URL (for self-hosted GitLab)",
    )


class Providers(BaseModel):
    github: GitHubProvider = Field(
        default=GitHubProvider(), description="GitHub provider configuration"
    )
    gitlab: GitLabProvider = Field(
        default=GitLabProvider(), description="GitLab provider configuration"
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
    workspace: Workspace = Field(
        default=Workspace(), description="The workspace configuration"
    )
    profiles: Profiles = Field(
        default=Profiles(), description="The profiles configuration"
    )
    providers: Providers = Field(
        default=Providers(), description="Git provider plugin configuration"
    )

    @classmethod
    def load(cls, config_path: str = None) -> Union["AppConfig", Exception]:
        """
        Load AppConfig from file or create default, then override with environment variables.

        Args:
            config_path: Path to configuration file (optional)

        Returns:
            AppConfig instance or Exception
        """
        try:
            # Try to load from specified path or default locations
            if config_path:
                config_file = Path(config_path)
            else:
                # Try default locations
                default_paths = [
                    Path.joinpath(Path.cwd(), "metagit.config.yml"),
                    Path.joinpath(Path.cwd(), "metagit.config.yaml"),
                    Path.joinpath(Path.home(), ".config", "metagit", "config.yml"),
                    Path.joinpath(Path.home(), ".config", "metagit", "config.yaml"),
                    Path.joinpath(Path.home(), ".metagit", "config.yml"),
                    Path.joinpath(Path.home(), ".metagit", "config.yaml"),
                    Path.joinpath(DATA_PATH, "metagit.config.yml"),
                ]

                config_file = None
                for path in default_paths:
                    if path.exists():
                        config_file = path
                        break

                if not config_file:
                    # Return default config if no file found
                    config = cls()
                else:
                    # Load from file
                    if config_file.exists():
                        with config_file.open("r") as f:
                            data = yaml.safe_load(f)

                        # Handle both direct config and nested config structures
                        if "config" in data:
                            config = cls(**data["config"])
                        else:
                            config = cls(**data)
                    else:
                        return FileNotFoundError(
                            f"Configuration file {config_file} not found"
                        )

            # Override token values with environment variables if they exist
            config = cls._override_with_env_vars(config)

            return config

        except Exception as e:
            return e

    @classmethod
    def _override_with_env_vars(cls, config: "AppConfig") -> "AppConfig":
        """
        Override configuration values with environment variables if they exist.

        Args:
            config: The AppConfig instance to override

        Returns:
            Updated AppConfig instance
        """
        # Override LLM API key
        if os.getenv("METAGIT_LLM_API_KEY"):
            config.llm.api_key = os.getenv("METAGIT_LLM_API_KEY")

        # Override GitHub provider settings
        if os.getenv("METAGIT_GITHUB_TOKEN"):
            config.providers.github.api_token = os.getenv("METAGIT_GITHUB_TOKEN")
            config.providers.github.enabled = True

        if os.getenv("METAGIT_GITHUB_URL"):
            config.providers.github.base_url = os.getenv("METAGIT_GITHUB_URL")

        # Override GitLab provider settings
        if os.getenv("METAGIT_GITLAB_TOKEN"):
            config.providers.gitlab.api_token = os.getenv("METAGIT_GITLAB_TOKEN")
            config.providers.gitlab.enabled = True

        if os.getenv("METAGIT_GITLAB_URL"):
            config.providers.gitlab.base_url = os.getenv("METAGIT_GITLAB_URL")

        # Override main API settings
        if os.getenv("METAGIT_API_KEY"):
            config.api_key = os.getenv("METAGIT_API_KEY")

        if os.getenv("METAGIT_API_URL"):
            config.api_url = os.getenv("METAGIT_API_URL")

        if os.getenv("METAGIT_API_VERSION"):
            config.api_version = os.getenv("METAGIT_API_VERSION")

        if os.getenv("GITHUB_TOKEN"):
            config.providers.github.api_token = os.getenv("GITHUB_TOKEN")
            config.providers.github.enabled = True

        if os.getenv("GITLAB_TOKEN"):
            config.providers.gitlab.api_token = os.getenv("GITLAB_TOKEN")
            config.providers.gitlab.enabled = True

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
