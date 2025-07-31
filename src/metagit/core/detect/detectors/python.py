import os
import tomli
from pathlib import Path
from typing import Optional
from metagit.core.detect.models import ProjectScanContext, DiscoveryResult


class PythonDetector:
    name = "PythonDetector"

    def should_run(self, ctx: ProjectScanContext) -> bool:
        indicators = ["pyproject.toml", "requirements.txt", "setup.py"]
        return any((ctx.root_path / name).exists() for name in indicators)

    def run(self, ctx: ProjectScanContext) -> Optional[DiscoveryResult]:
        if not self.should_run(ctx):
            return None

        dependencies = self._get_dependencies(ctx.root_path)

        return DiscoveryResult(
            name="Python Project",
            description="Detected a Python project using modern or legacy packaging standards",
            tags=["python"],
            confidence=0.98,
            data={"dependencies": dependencies},
        )

    def _get_dependencies(self, root: Path) -> list[str]:
        deps = []

        pyproject = os.path.join(root, "pyproject.toml")
        if os.path.exists(pyproject):
            with open(pyproject, "rb") as f:
                data = tomli.load(f)
                # Handle both Poetry and PEP 621
                try:
                    deps.extend(data["tool"]["poetry"]["dependencies"].keys())
                except KeyError:
                    pass
                try:
                    deps.extend(data["project"]["dependencies"])
                except KeyError:
                    pass

        reqs = root / "requirements.txt"
        if reqs.exists():
            with reqs.open("r") as f:
                deps.extend(
                    [
                        line.strip().split("==")[0]
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
                )

        setup = root / "setup.py"
        if setup.exists():
            deps.append(
                "[from setup.py]"
            )  # You could parse with `ast`, but keep it simple here

        return sorted(set(deps))
