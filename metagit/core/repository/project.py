#!/usr/bin/env python3

import json
import logging
from typing import Any, Optional, Union

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

from metagit.core.repository.branch import GitBranchAnalysis
from metagit.core.repository.cicd import CIConfigAnalysis

load_dotenv()

default_logger = logging.getLogger("ProjectAnalysis")
default_logger.setLevel(logging.INFO)
if not default_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    default_logger.addHandler(handler)


class ProjectAnalysis(BaseModel):
    path: str
    url: Optional[str] = None
    branch: Optional[str] = None
    checksum: Optional[Union[str, int]] = None
    last_updated: Optional[str] = None
    branch_analysis: Optional[GitBranchAnalysis] = None
    ci_config_analysis: Optional[CIConfigAnalysis] = None
    logger: Optional[Any] = None
    # commit_analysis: Optional[GitCommitAnalysis] = None
    # tag_analysis: Optional[GitTagAnalysis] = None

    def model_post_init(self, __context: Any) -> None:
        # Use provided logger or fallback to top-level default_logger
        self.logger = self.logger or default_logger

    def run_all(self) -> Union[None, Exception]:
        try:
            self.branch_analysis = GitBranchAnalysis.from_repo(self.path, self.logger)
            self.ci_config_analysis = CIConfigAnalysis.from_repo(self.path, self.logger)
            # Future calls:
            # self.commit_analysis = GitCommitAnalysis.from_repo(self.path)
            # self.tag_analysis = GitTagAnalysis.from_repo(self.path)
            return None
        except Exception as e:
            return e

    def summary(self) -> Union[str, Exception]:
        try:
            lines = [f"Analysis for project at: {self.path}"]
            if self.branch_analysis:
                lines.append(
                    f"Branching strategy: {self.branch_analysis.strategy_guess}"
                )
                lines.append("Branches:")
                for b in self.branch_analysis.branches:
                    lines.append(
                        f"  - {'[remote]' if b.is_remote else '[local]'} {b.name}"
                    )
            else:
                lines.append("Branch analysis not available.")
            if self.ci_config_analysis:
                lines.append(f"CI/CD tool: {self.ci_config_analysis.detected_tool}")
            else:
                lines.append("CI/CD analysis not available.")
            return "\n".join(lines)
        except Exception as e:
            return e

    def remove_logger(self, obj: Any) -> Union[Any, Exception]:
        try:
            if isinstance(obj, dict):
                return {
                    k: self.remove_logger(v) for k, v in obj.items() if k != "logger"
                }
            elif isinstance(obj, list):
                return [self.remove_logger(item) for item in obj]
            else:
                return obj
        except Exception as e:
            return e

    def to_yaml(self) -> Union[str, Exception]:
        """
        Convert the ProjectAnalysis model (including all nested models) to a YAML string.
        """
        try:
            # Use pydantic's .model_dump() for dict conversion (v2+), else .dict()
            data = (
                self.model_dump(exclude={"logger"})
                if hasattr(self, "model_dump")
                else dict(self, exclude={"logger"})
            )
            data = self.remove_logger(data)
            if isinstance(data, Exception):
                return data
            return yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
        except Exception as e:
            return e

    def to_json(self) -> Union[str, Exception]:
        """
        Convert the ProjectAnalysis model (including all nested models) to a JSON string.
        """
        try:
            data = (
                self.model_dump(exclude={"logger"})
                if hasattr(self, "model_dump")
                else dict(self, exclude={"logger"})
            )
            data = self.remove_logger(data)
            if isinstance(data, Exception):
                return data
            return json.dumps(data, indent=4)
        except Exception as e:
            return e
