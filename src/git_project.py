#!/usr/bin/env python3

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()


from typing import List, Optional

from pydantic import BaseModel, Field

from src.git_branch_analysis import GitBranchAnalysis


class ProjectAnalysis(BaseModel):
    path: str
    branch_analysis: Optional[GitBranchAnalysis] = None
    # Future fields:
    # commit_analysis: Optional[GitCommitAnalysis] = None
    # tag_analysis: Optional[GitTagAnalysis] = None
    # ci_config_analysis: Optional[CIConfigAnalysis] = None

    def run_all(self):
        self.branch_analysis = GitBranchAnalysis.from_repo(self.path)
        # Future calls:
        # self.commit_analysis = GitCommitAnalysis.from_repo(self.path)
        # self.tag_analysis = GitTagAnalysis.from_repo(self.path)
        # self.ci_config_analysis = CIConfigAnalysis.from_repo(self.path)

    def summary(self) -> str:
        lines = [f"Analysis for project at: {self.path}"]
        if self.branch_analysis:
            lines.append(f"Branching strategy: {self.branch_analysis.strategy_guess}")
            lines.append("Branches:")
            for b in self.branch_analysis.branches:
                lines.append(f"  - {'[remote]' if b.is_remote else '[local]'} {b.name}")
        else:
            lines.append("Branch analysis not available.")
        return "\n".join(lines)
