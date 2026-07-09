#!/usr/bin/env python

import os
from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from metagit import DATA_PATH
from metagit.core.utils.yaml_class import yaml

success_blurb: str = "Success! ✅"
failure_blurb: str = "Failed! ❌"


class WorkspaceDedupeScope(str, Enum):
    """Where repository deduplication is applied."""

    WORKSPACE = "workspace"
    GLOBAL = "global"


class WorkspaceDedupeStrategy(str, Enum):
    """How duplicate repository identities share disk layout."""

    SYMLINK = "symlink"


class WorkspaceDedupeConfig(BaseModel):
    """Deduplicate synced repos within a workspace via a canonical directory."""

    model_config = ConfigDict(use_enum_values=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="When true, clone once under canonical_dir and symlink per project",
    )
    scope: WorkspaceDedupeScope = Field(
        default=WorkspaceDedupeScope.WORKSPACE,
        description="Dedupe scope (v1 implements workspace only)",
    )
    strategy: WorkspaceDedupeStrategy = Field(
        default=WorkspaceDedupeStrategy.SYMLINK,
        description="How project mounts reference canonical checkouts",
    )
    canonical_dir: str = Field(
        default="_canonical",
        description="Directory under workspace.path holding canonical checkouts",
    )


class WorkspaceConfig(BaseModel):
    """Model for workspace configuration in AppConfig."""

    path: str = Field(default="./.metagit", description="Workspace path")
    session_path: str = Field(
        default=".metagit/sessions",
        description=(
            "Path for workspace session state (metadata/objectives). Relative paths resolve from workspace root."
        ),
    )
    campaigns_path: str = Field(
        default="_campaigns",
        description=(
            "Path for committed campaign YAML overlays. Relative paths resolve from the manifest root. "
            "Defaults to _campaigns to avoid colliding with a workspace project named campaigns."
        ),
    )
    worktrees_path: str = Field(
        default=".worktrees",
        description=(
            "Directory for ACL agent git worktree checkouts. Relative paths resolve from the "
            "manifest/session root. Defaults to .worktrees; the path basename is reserved and "
            "cannot be used as a workspace project name."
        ),
    )
    default_project: Optional[str] = Field(
        default=None,
        description=(
            "Optional session preference for -p/--project when omitted. "
            "When unset, metagit resolves from the manifest (sole project) "
            "or uses the computed local project for application manifests."
        ),
    )
    dedupe: WorkspaceDedupeConfig = Field(
        default_factory=WorkspaceDedupeConfig,
        description="Optional workspace-scoped repository deduplication settings",
    )
    ui_show_preview: Optional[bool] = Field(default=True, description="Show preview in fuzzy finder console UI")
    ui_menu_length: Optional[int] = Field(default=10, description="Number of items to show in menu")
    ui_preview_height: Optional[int] = Field(default=3, description="Height of preview in fuzzy finder console UI")
    ui_ignore_hidden: bool = Field(
        default=True,
        description="When true, hide dotfiles and dot-directories from repo picker UI",
    )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class LLM(BaseModel):
    """Model for LLM configuration in AppConfig."""

    enabled: bool = Field(default=False, description="Whether LLM is enabled")
    provider: str = Field(default="openrouter", description="LLM provider")
    provider_model: str = Field(default="gpt-4o-mini", description="LLM provider model")
    embedder: str = Field(default="ollama", description="Embedding provider")
    embedder_model: str = Field(default="nomic-embed-text", description="Embedding model")
    api_key: str = Field(default="", description="API key for LLM provider")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class Boundary(BaseModel):
    """Model for organization boundaries in AppConfig."""

    name: str = Field(..., description="Boundary name")
    values: List[str] = Field(default_factory=list, description="Boundary values")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class Profile(BaseModel):
    """Model for profile configuration."""

    name: str = Field(default="default", description="Profile name")
    boundaries: Optional[List[Boundary]] = Field(
        description="Organization boundaries. Items in this list are internal to the profile.",
        default=[
            Boundary(name="github", values=[]),
            Boundary(name="jfrog", values=[]),
            Boundary(name="gitlab", values=[]),
            Boundary(name="bitbucket", values=[]),
            Boundary(name="azure_devops", values=[]),
            Boundary(name="dockerhub", values=[]),
            Boundary(
                name="domain",
                values=[
                    "localhost",
                    "127.0.0.1",
                    "0.0.0.0",  # nosec B104 — domain boundary allowlist, not a bind address
                    "192.168.*",
                    "10.0.*",
                    "172.16.*",
                ],
            ),
        ],
    )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class GitHubProvider(BaseModel):
    """Model for GitHub provider configuration in AppConfig."""

    enabled: bool = Field(default=False, description="Whether GitHub provider is enabled")
    api_token: str = Field(default="", description="GitHub API token")
    base_url: str = Field(default="https://api.github.com", description="GitHub API base URL")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class GitLabProvider(BaseModel):
    """Model for GitLab provider configuration in AppConfig."""

    enabled: bool = Field(default=False, description="Whether GitLab provider is enabled")
    api_token: str = Field(default="", description="GitLab API token")
    base_url: str = Field(default="https://gitlab.com/api/v4", description="GitLab API base URL")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class Providers(BaseModel):
    """Model for Git provider configuration in AppConfig."""

    github: GitHubProvider = Field(default_factory=GitHubProvider, description="GitHub provider configuration")
    gitlab: GitLabProvider = Field(default_factory=GitLabProvider, description="GitLab provider configuration")

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class StateConfig(BaseModel):
    """Remote or local coordination-state backend settings."""

    model_config = ConfigDict(extra="forbid")

    backend: Literal["local", "http"] = Field(
        default="local",
        description="State backend selector: local JSON files or remote HTTP ops API",
    )
    url: str = Field(
        default="",
        description="Base URL for remote state (ops server root, e.g. http://127.0.0.1:8787)",
    )
    token: str = Field(
        default="",
        description="Bearer token for remote state requests",
    )
    conflict_retries: int = Field(
        default=1,
        ge=0,
        description="Optimistic concurrency retries for mutating services",
    )


class MergeConfig(BaseModel):
    """Merge orchestrator settings."""

    model_config = ConfigDict(extra="forbid")

    validators: list[str] = Field(
        default_factory=list,
        description="Opt-in zsh commands that must pass before merge promotion",
    )


class AppConfig(BaseModel):
    """Application-level settings (not the Metagit package release version — use `metagit version`)."""

    model_config = ConfigDict(extra="ignore")

    agent_mode: bool = Field(
        default=False,
        description=(
            "When true, disable interactive UIs (fuzzy finder, prompts, editor). "
            "Overridden by METAGIT_AGENT_MODE when set."
        ),
    )
    description: str = "Metagit configuration"
    editor: str = Field(default="code", description="The editor to use for the CLI")
    # Reserved for future use
    api_url: str = Field(default="", description="The API URL to use for the CLI")
    # Reserved for future use
    api_version: str = Field(
        default="",
        description="Reserved for a future remote API contract version (METAGIT_API_VERSION)",
    )
    # Reserved for future use
    api_key: str = Field(default="", description="The API key to use for the CLI")
    # Reserved for future use
    cicd_file_data: str = Field(
        default=os.path.join(DATA_PATH, "cicd-files.json"),
        description="The path to the cicd file data",
    )
    file_type_data: str = Field(
        default=os.path.join(DATA_PATH, "file-types.json"),
        description="The path to the file type data",
    )
    package_manager_data: str = Field(
        default=os.path.join(DATA_PATH, "package-managers.json"),
        description="The path to the package manager data",
    )
    llm: LLM = Field(default=LLM(), description="The LLM configuration")
    workspace: WorkspaceConfig = Field(default=WorkspaceConfig(), description="The workspace configuration")
    profiles: List[Profile] = Field(default=[Profile()], description="The profiles available to this appconfig")
    providers: Providers = Field(default=Providers(), description="Git provider plugin configuration")
    state: StateConfig = Field(
        default_factory=StateConfig,
        description="Workspace coordination state backend (objectives, handoffs, approvals)",
    )
    merge: MergeConfig = Field(default_factory=MergeConfig, description="Merge orchestrator settings")

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
                config_path = os.path.join(Path.home(), ".config", "metagit", "config.yml")

            config_file = Path(config_path)
            if not config_file.exists():
                return cls()

            with config_file.open("r") as f:
                config_data = yaml.safe_load(f)

            config = cls(**config_data["config"]) if "config" in config_data else cls(**config_data)

            # Override with environment variables
            config = cls._override_from_environment(config)
            os.environ.setdefault("METAGIT_WORKSPACE_SESSION_PATH", config.workspace.session_path)
            os.environ.setdefault("METAGIT_WORKSPACE_CAMPAIGNS_PATH", config.workspace.campaigns_path)
            os.environ.setdefault("METAGIT_WORKSPACE_WORKTREES_PATH", config.workspace.worktrees_path)

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
        if os.getenv("METAGIT_AGENT_MODE") is not None:
            config.agent_mode = os.getenv("METAGIT_AGENT_MODE", "").strip().lower() in {
                "true",
                "1",
                "yes",
                "on",
            }

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

        if os.getenv("METAGIT_STATE_URL"):
            config.state.url = os.getenv("METAGIT_STATE_URL", "")
        if os.getenv("METAGIT_STATE_BACKEND"):
            config.state.backend = os.getenv("METAGIT_STATE_BACKEND", "local")  # type: ignore[assignment]
        if os.getenv("METAGIT_STATE_TOKEN"):
            config.state.token = os.getenv("METAGIT_STATE_TOKEN", "")

        # Workspace configuration
        if os.getenv("METAGIT_WORKSPACE_PATH"):
            config.workspace.path = os.getenv("METAGIT_WORKSPACE_PATH")
        if os.getenv("METAGIT_WORKSPACE_SESSION_PATH"):
            config.workspace.session_path = os.getenv("METAGIT_WORKSPACE_SESSION_PATH")
        if os.getenv("METAGIT_WORKSPACE_CAMPAIGNS_PATH"):
            config.workspace.campaigns_path = os.getenv("METAGIT_WORKSPACE_CAMPAIGNS_PATH")
        if os.getenv("METAGIT_WORKSPACE_WORKTREES_PATH"):
            config.workspace.worktrees_path = os.getenv("METAGIT_WORKSPACE_WORKTREES_PATH")
        if os.getenv("METAGIT_WORKSPACE_DEFAULT_PROJECT"):
            config.workspace.default_project = os.getenv("METAGIT_WORKSPACE_DEFAULT_PROJECT")
        if os.getenv("METAGIT_WORKSPACE_DEDUPE_ENABLED"):
            config.workspace.dedupe.enabled = os.getenv("METAGIT_WORKSPACE_DEDUPE_ENABLED", "").lower() == "true"

        # GitHub provider configuration
        if os.getenv("METAGIT_GITHUB_ENABLED"):
            config.providers.github.enabled = os.getenv("METAGIT_GITHUB_ENABLED").lower() == "true"
        if os.getenv("METAGIT_GITHUB_API_TOKEN"):
            config.providers.github.api_token = os.getenv("METAGIT_GITHUB_API_TOKEN")
        if os.getenv("METAGIT_GITHUB_BASE_URL"):
            config.providers.github.base_url = os.getenv("METAGIT_GITHUB_BASE_URL")

        # GitLab provider configuration
        if os.getenv("METAGIT_GITLAB_ENABLED"):
            config.providers.gitlab.enabled = os.getenv("METAGIT_GITLAB_ENABLED").lower() == "true"
        if os.getenv("METAGIT_GITLAB_API_TOKEN"):
            config.providers.gitlab.api_token = os.getenv("METAGIT_GITLAB_API_TOKEN")
        if os.getenv("METAGIT_GITLAB_BASE_URL"):
            config.providers.gitlab.base_url = os.getenv("METAGIT_GITLAB_BASE_URL")

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
                config_path = os.path.join(Path.home(), ".config", "metagit", "config.yml")

            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with config_file.open("w") as f:
                yaml.dump(
                    {"config": self.model_dump(exclude_none=True, exclude_unset=True, mode="json")},
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                )

            return True
        except Exception as e:
            return e
