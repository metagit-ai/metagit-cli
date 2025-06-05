#!/usr/bin/env python3

import yaml
from dotenv import load_dotenv

load_dotenv()


from typing import Optional

from pydantic import BaseModel

from src.git_branch_analysis import GitBranchAnalysis
from src.git_cicd_analysis import CIConfigAnalysis


class ProjectAnalysis(BaseModel):
    path: str
    branch_analysis: Optional[GitBranchAnalysis] = None
    ci_config_analysis: Optional[CIConfigAnalysis] = None
    # commit_analysis: Optional[GitCommitAnalysis] = None
    # tag_analysis: Optional[GitTagAnalysis] = None

    def run_all(self):
        self.branch_analysis = GitBranchAnalysis.from_repo(self.path)
        self.ci_config_analysis = CIConfigAnalysis.from_repo(self.path)
        # Future calls:
        # self.commit_analysis = GitCommitAnalysis.from_repo(self.path)
        # self.tag_analysis = GitTagAnalysis.from_repo(self.path)

    def summary(self) -> str:
        lines = [f"Analysis for project at: {self.path}"]
        if self.branch_analysis:
            lines.append(f"Branching strategy: {self.branch_analysis.strategy_guess}")
            lines.append("Branches:")
            for b in self.branch_analysis.branches:
                lines.append(f"  - {'[remote]' if b.is_remote else '[local]'} {b.name}")
        else:
            lines.append("Branch analysis not available.")
        if self.ci_config_analysis:
            lines.append(f"CI/CD tool: {self.ci_config_analysis.detected_tool}")
        else:
            lines.append("CI/CD analysis not available.")
        return "\n".join(lines)

    def to_yaml(self) -> str:
        """
        Convert the ProjectAnalysis model (including all nested models) to a YAML string.
        """
        # Use pydantic's .model_dump() for dict conversion (v2+), else .dict()
        data = self.model_dump() if hasattr(self, "model_dump") else self.dict()
        return yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
