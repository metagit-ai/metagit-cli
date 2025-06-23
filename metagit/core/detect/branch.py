#!/usr/bin/env python

import logging
import re
from typing import Any, Literal, Union

from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import BaseModel, Field

default_logger = logging.getLogger("CIConfigAnalysis")
default_logger.setLevel(logging.INFO)
if not default_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    default_logger.addHandler(handler)


class BranchInfo(BaseModel):
    name: str
    is_remote: bool = Field(default=False)


class GitBranchAnalysis(BaseModel):
    branches: list[BranchInfo]
    strategy_guess: (
        Literal[
            "Git Flow",
            "GitHub Flow",
            "GitLab Flow",
            "Trunk-Based Development",
            "Release Branching",
            "Unknown",
        ]
        | None
    ) = "Unknown"
    model_config = {
        "extra": "allow",
        "exclude": {"logger"},
    }

    @classmethod
    def from_repo(
        cls, repo_path: str = ".", logger: Any | None = None
    ) -> Union["GitBranchAnalysis", Exception]:
        """
        Analyze the git repository at the given path and return branch information and a strategy guess.
        Uses GitPython for all git operations.
        """
        try:
            logger = logger or default_logger

            try:
                repo = Repo(repo_path)
            except (InvalidGitRepositoryError, NoSuchPathError) as e:
                logging.exception(f"Invalid git repository at '{repo_path}': {e}")
                return ValueError(f"Invalid git repository at '{repo_path}': {e}")

            # Get local branches
            local_branches = [
                BranchInfo(name=branch.name, is_remote=False)
                for branch in repo.branches
                if branch.name != "HEAD"  # Exclude HEAD branch
            ]
            logger.debug(f"Found {len(local_branches)} local branches")

            # Get remote branches
            remote_branches = []
            for remote in repo.remotes:
                for ref in remote.refs:
                    # Remove remote name prefix (e.g., 'origin/')
                    branch_name = (
                        ref.name.split("/", 1)[1] if "/" in ref.name else ref.name
                    )
                    # Exclude HEAD branch from remote branches
                    if branch_name != "HEAD":
                        remote_branches.append(
                            BranchInfo(name=branch_name, is_remote=True)
                        )
            logger.debug(f"Found {len(remote_branches)} remote branches")

            # Combine and deduplicate branches (prefer local if name overlaps)
            all_branches_dict = {b.name: b for b in remote_branches}
            for b in local_branches:
                all_branches_dict[b.name] = b  # local takes precedence

            branches = list(all_branches_dict.values())

            strategy = cls.infer_strategy(branches)
            if isinstance(strategy, Exception):
                return strategy
            return cls(branches=branches, strategy_guess=strategy)
        except Exception as e:
            return e

    @staticmethod
    def infer_strategy(branches: list[BranchInfo]) -> Union[str, Exception]:
        try:
            names = [b.name for b in branches]

            def has(pattern: str) -> bool:
                return any(re.search(pattern, name) for name in names)

            if "main" in names or "master" in names:
                if has(r"^develop$") and has(r"^feature/") and has(r"^release/"):
                    return "Git Flow"
                elif has(r"^feature/") and not has(r"^develop$"):
                    return "GitHub Flow"
                elif has(r"^release/") and not has(r"^feature/"):
                    return "Release Branching"
                elif not has(r"/"):
                    return "Trunk-Based Development"
                elif has(r"^env/") or has(r"^staging") or has(r"^production"):
                    return "GitLab Flow"

            return "Unknown"
        except Exception as e:
            return e
