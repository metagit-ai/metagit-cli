#!/usr/bin/env python

import logging
import os
from typing import Any, Union

from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import BaseModel

from metagit.core.utils.logging import LoggerConfig, UnifiedLogger

# Top-level logger instance for fallback
# default_logger = UnifiedLogger(LoggerConfig()).get_logger()
default_logger = UnifiedLogger(
    LoggerConfig(
        name="RepositoryAnalysis",
        level=logging.INFO,
        console=True,
        terse=False,
    )
)


class CIConfigAnalysis(BaseModel):
    devops_platform: str | None = None
    repo_provider: str | None = None
    origin_url: str | None = None
    ci_config_path: str | None = None
    detected_tool: str | None = None
    logger: Any | None = None
    model_config = {
        "extra": "allow",
        "exclude": {"logger"},
    }

    @classmethod
    def from_repo(
        cls, repo_path: str = ".", logger: Any | None = None
    ) -> Union["CIConfigAnalysis", Exception]:
        try:
            logger = logger or default_logger

            ci_tools = {
                ".github/workflows": "GitHub Actions",
                ".gitlab-ci.yml": "GitLab CI",
                ".circleci/config.yml": "CircleCI",
                "azure-pipelines.yml": "Azure Pipelines",
                "bitbucket-pipelines.yml": "Bitbucket Pipelines",
                "Jenkinsfile": "Jenkins",
                ".drone.yml": "Drone CI",
            }
            devops_platform = None
            ci_config_path = None
            for path, name in ci_tools.items():
                full_path = os.path.join(repo_path, path)
                if os.path.isdir(full_path) or os.path.isfile(full_path):
                    devops_platform = name
                    ci_config_path = path
                    break

            origin_url = None
            repo_provider = None
            try:
                repo = Repo(repo_path)
                if repo.remotes:
                    origin = next((r for r in repo.remotes if r.name == "origin"), None)
                    if origin and origin.urls:
                        origin_url = next(iter(origin.urls), None)
            except (InvalidGitRepositoryError, NoSuchPathError) as e:
                logger.error(f"Invalid git repository at '{repo_path}': {e}")
                origin_url = None

            if origin_url:
                # Infer provider from URL
                if "github.com" in origin_url:
                    repo_provider = "GitHub"
                elif "gitlab.com" in origin_url:
                    repo_provider = "GitLab"
                elif "bitbucket.org" in origin_url:
                    repo_provider = "Bitbucket"
                elif "dev.azure.com" in origin_url or "visualstudio.com" in origin_url:
                    repo_provider = "Azure DevOps"
                else:
                    repo_provider = "Unknown"
                logger.debug(
                    f"Detected repo provider: {repo_provider} from URL: {origin_url}"
                )
            else:
                logger.debug("No origin URL found for repo provider detection.")

            return cls(
                devops_platform=devops_platform,
                repo_provider=repo_provider,
                origin_url=origin_url,
                ci_config_path=ci_config_path,
                detected_tool=devops_platform,
                logger=logger,
            )
        except Exception as e:
            return e
