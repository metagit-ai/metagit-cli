#!/usr/bin/env python

import os
from typing import Optional

from pydantic import BaseModel

from src.utils.logging import LoggerConfig, UnifiedLogger

logger = UnifiedLogger(LoggerConfig()).get_logger()


class CIConfigAnalysis(BaseModel):
    detected_tool: Optional[str] = None
    repo_provider: Optional[str] = None
    origin_url: Optional[str] = None

    @classmethod
    def from_repo(cls, repo_path: str = ".") -> "CIConfigAnalysis":
        from git import InvalidGitRepositoryError, NoSuchPathError, Repo

        ci_tools = {
            ".github/workflows": "GitHub Actions",
            ".gitlab-ci.yml": "GitLab CI",
            ".circleci/config.yml": "CircleCI",
            "azure-pipelines.yml": "Azure Pipelines",
            "bitbucket-pipelines.yml": "Bitbucket Pipelines",
            "Jenkinsfile": "Jenkins",
            ".drone.yml": "Drone CI",
        }

        detected_tool = None
        for path, name in ci_tools.items():
            full_path = os.path.join(repo_path, path)
            if os.path.isdir(full_path) or os.path.isfile(full_path):
                detected_tool = name
                break

        origin_url = None
        repo_provider = None
        hosting_provider = None
        try:
            repo = Repo(repo_path)
            if repo.remotes:
                origin = next((r for r in repo.remotes if r.name == "origin"), None)
                if origin and origin.urls:
                    origin_url = next(iter(origin.urls), None)
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            if logger:
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
            if logger:
                logger.info(
                    f"Detected repo provider: {repo_provider} from URL: {origin_url}"
                )
        else:
            if logger:
                logger.info("No origin URL found for repo provider detection.")

        return cls(
            detected_tool=detected_tool,
            repo_provider=repo_provider,
            origin_url=origin_url,
        )
