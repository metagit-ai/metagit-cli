#!/usr/bin/env python
"""
Class for managing projects.
"""
import concurrent.futures
import os
from pathlib import Path
from typing import Union

import git
from tqdm import tqdm

from metagit.core.project.models import ProjectPath
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.models import WorkspaceProject


class ProjectManager:
    """
    Manager class for handling projects within a workspace.
    """

    def __init__(self, workspace_path: Union[str, Path], logger: UnifiedLogger) -> None:
        """
        Initialize the ProjectManager.

        Args:
            workspace_path: The root path of the workspace.
            logger: The logger instance for output.
        """
        self.workspace_path = Path(workspace_path)
        self.logger = logger
        self.logger.set_level("INFO")

    def sync(self, project: WorkspaceProject) -> bool:
        """
        Sync a workspace project concurrently.

        Iterates through each repository in the project and either creates a
        symbolic link for local paths or clones it if it's a remote repository.

        Returns:
            bool: True if sync is successful, False otherwise.
        """
        project_dir = self.workspace_path / project.name
        project_dir.mkdir(parents=True, exist_ok=True)
        tqdm.write(
            f"Concurrently syncing project '{project.name}' in '{project_dir}'..."
        )

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_repo = {
                executor.submit(self._sync_repo, repo, project_dir, i): repo
                for i, repo in enumerate(project.repos)
            }
            for future in concurrent.futures.as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    future.result()
                except Exception as exc:
                    tqdm.write(f"'{repo.name}' generated an exception: {exc}")
                    return False
        return True

    def _sync_repo(self, repo: ProjectPath, project_dir: Path, position: int) -> None:
        """
        Sync a single repository.

        This method is called by the thread pool executor.
        """
        target_path = project_dir / repo.name

        if repo.path:
            self._sync_local(repo, target_path, position)
        elif repo.url:
            self._sync_remote(repo, target_path, position)
        else:
            tqdm.write(f"Skipping '{repo.name}': No local path or remote URL provided.")

    def _sync_local(self, repo: ProjectPath, target_path: Path, position: int) -> None:
        """Handle syncing of a local repository via symlink."""
        source_path = Path(repo.path).expanduser().resolve()
        if not source_path.exists():
            tqdm.write(f"Source path for '{repo.name}' does not exist: {source_path}")
            return

        desc = f"'{repo.name}'"
        if target_path.exists() or target_path.is_symlink():
            with tqdm(
                total=1,
                desc=desc,
                position=position,
                bar_format="{l_bar}Already exists{r_bar}",
            ) as pbar:
                pbar.update(1)
            return

        try:
            os.symlink(source_path, target_path)
            with tqdm(
                total=1,
                desc=desc,
                position=position,
                bar_format="{l_bar}Symlinked{r_bar}",
            ) as pbar:
                pbar.update(1)
        except OSError as e:
            tqdm.write(f"Failed to create symbolic link for '{repo.name}': {e}")

    def _sync_remote(self, repo: ProjectPath, target_path: Path, position: int) -> None:
        """Handle syncing of a remote repository via git clone."""

        class CloneProgressHandler(git.RemoteProgress):
            def __init__(self, pbar: tqdm) -> None:
                super().__init__()
                self.pbar = pbar
                self.pbar.total = 100

            def update(
                self,
                op_code: int,
                cur_count: Union[str, float],
                max_count: Union[str, float, None] = None,
                message: str = "",
            ) -> None:
                if max_count:
                    self.pbar.total = float(max_count)
                self.pbar.n = float(cur_count)
                if message:
                    self.pbar.set_postfix_str(message.strip(), refresh=True)
                self.pbar.update(0)  # Manually update the progress bar

        desc = f"'{repo.name}'"
        if target_path.exists():
            with tqdm(
                total=1,
                desc=desc,
                position=position,
                bar_format="{l_bar}Already exists{r_bar}",
            ) as pbar:
                pbar.update(1)
            return

        with tqdm(
            desc=desc,
            position=position,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            miniters=1,
        ) as pbar:
            try:
                git.Repo.clone_from(
                    str(repo.url),
                    str(target_path),
                    progress=CloneProgressHandler(pbar),
                )
                pbar.set_description(f"{desc} Cloned")
            except git.exc.GitCommandError as e:
                pbar.set_description(f"{desc} Failed")
                tqdm.write(
                    f"Failed to clone repository '{repo.name}'.\n"
                    f"URL: {repo.url}\n"
                    f"Error: {e.stderr}"
                )
