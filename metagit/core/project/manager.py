#!/usr/bin/env python
"""
Class for managing projects.
"""

import concurrent.futures
import os
from pathlib import Path
from typing import List, Union

import git
from tqdm import tqdm

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.utils.common import create_vscode_workspace
from metagit.core.utils.fuzzyfinder import (
    FuzzyFinder,
    FuzzyFinderConfig,
    FuzzyFinderTarget,
)
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.utils.userprompt import UserPrompt
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

    def add(
        self,
        config_path: Path,
        project_name: str,
        repo: Union[ProjectPath, None],
        metagit_config: MetagitConfig,
    ) -> Union[ProjectPath, Exception]:
        """
        Add a repository to a specific project in the configuration.

        Args:
            project_name: The name of the project to add the repository to.
            repo: The ProjectPath object representing the repository to add. If None, will prompt for data.
            metagit_config: The MetagitConfig instance to work with configuration data.

        Returns:
            Union[ProjectPath, Exception]: ProjectPath if successful, Exception if failed.
        """
        config_manager = MetagitConfigManager(metagit_config=metagit_config)
        try:
            # Validate inputs
            if not project_name or not isinstance(project_name, str):
                raise ValueError("Project name must be a non-empty string")

            # Check if workspace configuration exists
            if not metagit_config.workspace:
                raise ValueError("No workspace configuration found in the config file")
            # Find the target project
            target_project = None
            for project in metagit_config.workspace.projects:
                if project.name == project_name:
                    target_project = project
                    break

            if not target_project:
                raise ValueError(
                    f"Project '{project_name}' not found in workspace configuration"
                )

            # If repo is None, prompt for ProjectPath data
            if repo is None:
                self.logger.debug(
                    "No repository data provided. Prompting for information..."
                )
                repo_result = UserPrompt.prompt_for_model(
                    ProjectPath,
                    title="Add git repository or local path to project group",
                    fields_to_prompt=["name", "path", "url", "description"],
                )
                if isinstance(repo_result, Exception):
                    return repo_result
                if repo_result.path is None and repo_result.url is None:
                    raise ValueError(
                        "No local path or remote URL provided. Please provide one of them."
                    )
                repo = repo_result

            # Check if name already exists in the project
            for existing_repo in target_project.repos:
                if existing_repo.name == repo.name:
                    raise ValueError(
                        f"Repository '{repo.name}' already exists in project '{project_name}'"
                    )

            # Add the repository to the project
            target_project.repos.append(repo)

            # Save the updated configuration
            save_result = config_manager.save_config(metagit_config, config_path)
            if isinstance(save_result, Exception):
                return save_result

            self.logger.debug(
                f"Successfully added repository '{repo.name}' to project '{project_name}' in configuration"
            )
            return repo

        except Exception as e:
            self.logger.error(
                f"Failed to add repository '{repo.name if repo else 'unknown'}' to project '{project_name}': {str(e)}"
            )
            return e

    def sync(self, project: WorkspaceProject) -> bool:
        """
        Sync a workspace project concurrently.

        Iterates through each repository in the project and either creates a
        symbolic link for local paths or clones it if it's a remote repository.
        After syncing, creates a VS Code workspace file.

        Returns:
            bool: True if sync is successful, False otherwise.
        """
        project_dir = os.path.join(self.workspace_path, project.name)
        os.makedirs(project_dir, exist_ok=True)
        tqdm.write(f"Syncing {project.name} project to {project_dir}...")

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
                    tqdm.write(f"{repo.name} generated an exception: {exc}")
                    return False

        # Create VS Code workspace file after successful sync
        workspace_result = self._create_vscode_workspace(project, project_dir)
        if isinstance(workspace_result, Exception):
            tqdm.write(f"Failed to create VS Code workspace file: {workspace_result}")
            # Don't fail the entire sync for workspace file creation issues
        # else:
        #     tqdm.write(f"Created VS Code workspace file: {workspace_result}")

        return True

    def _create_vscode_workspace(
        self, project: WorkspaceProject, project_dir: str
    ) -> Union[str, Exception]:
        """
        Create a VS Code workspace file for the project.

        Args:
            project: The workspace project containing repository information
            project_dir: The directory where the project is located

        Returns:
            Path to the created workspace file on success, Exception on failure
        """
        try:
            # Get list of repository names that were successfully synced
            repo_names = []
            for repo in project.repos:
                repo_path = os.path.join(project_dir, repo.name)
                if os.path.exists(repo_path):
                    repo_names.append(repo.name)

            if not repo_names:
                return Exception("No repositories found to include in workspace")

            # Create workspace file content
            workspace_content = create_vscode_workspace(project.name, repo_names)
            if isinstance(workspace_content, Exception):
                return workspace_content

            # Write workspace file
            workspace_file_path = os.path.join(project_dir, "workspace.code-workspace")
            with open(workspace_file_path, "w") as f:
                f.write(workspace_content)

            return workspace_file_path

        except Exception as e:
            return e

    def _sync_repo(self, repo: ProjectPath, project_dir: str, position: int) -> None:
        """
        Sync a single repository.

        This method is called by the thread pool executor.
        """
        target_path = os.path.join(project_dir, repo.name)

        if repo.path:
            self._sync_local(repo, target_path, position)
        elif repo.url:
            self._sync_remote(repo, target_path, position)
        else:
            tqdm.write(f"Skipping {repo.name}: No local path or remote URL provided.")

    def _sync_local(self, repo: ProjectPath, target_path: str, position: int) -> None:
        """Handle syncing of a local repository via symlink."""
        source_path = Path(repo.path).expanduser().resolve()
        if not source_path.exists():
            tqdm.write(f"Source path for {repo.name} does not exist: {source_path}")
            return

        desc = f"  ✅   🔗 {repo.name}"
        if os.path.exists(target_path) or os.path.islink(target_path):
            desc = f"  🔗 {repo.name}"
            with tqdm(
                total=1,
                desc=desc,
                position=position,
                bar_format="{l_bar} 🟠 Already exists{r_bar}",
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
            tqdm.write(f"Failed to create symbolic link for {repo.name}: {e}")

    def _sync_remote(self, repo: ProjectPath, target_path: str, position: int) -> None:
        """Handle syncing of a remote repository via git clone."""

        class CloneProgressHandler(git.RemoteProgress):
            def __init__(self, pbar: tqdm) -> None:
                super().__init__()
                self.pbar = pbar
                self.pbar.total = 100

            def update(
                self,
                op_code: int,  # noqa: ARG002
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

        desc = f"  ⤵️ {repo.name}"
        if os.path.exists(target_path):
            with tqdm(
                total=1,
                desc=desc,
                position=position,
                bar_format="{l_bar} 🟠 Already exists{r_bar}",
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
                    target_path,
                    progress=CloneProgressHandler(pbar),
                )
                pbar.set_description(f"  ✅ {desc} Cloned")
            except git.exc.GitCommandError as e:
                pbar.set_description(f"  ❌ {desc} Failed")
                tqdm.write(
                    f"Failed to clone repository {repo.name}.\n"
                    f"URL: {repo.url}\n"
                    f"Error: {e.stderr}"
                )

    def select_repo(
        self,
        metagit_config: MetagitConfig,
        project: str,
    ) -> ProjectPath:
        """
        Select a repository from a synced project.
        """
        project_path: str = os.path.join(self.workspace_path, project)
        if project == "local":
            workspace_project = metagit_config.local_workspace_project
        else:
            workspace_project = [
                target_project
                for target_project in metagit_config.workspace.projects
                if target_project.name == project
            ][0]

        if not Path(project_path).exists(follow_symlinks=True):
            self.logger.warning(
                f"Project path does not exist for project: {project_path}"
            )
            self.logger.warning(
                f"You can sync the project with `metagit workspace sync --project {project_path}`"
            )
            return
        project_dict = {}
        # Iterate through the project path and add the directories and symlinks to the project_dict
        for f in Path(project_path).iterdir():
            if f.is_dir():
                project_dict[f.name] = "Directory - non-workspace managed"
            if f.is_symlink():
                target_path = f.readlink()
                project_dict[f.name] = f"Symlink({target_path}) - non-workspace managed"
        # Iterate through the workspace project and add the repo descriptions to the project_dict
        for repo in workspace_project.repos:
            if repo.name in project_dict:
                target_kind = "Directory"
                if repo.path is not None:
                    target_kind = f"Symlink ({repo.path})"
                if repo.description is None:
                    project_dict[repo.name] = f"{target_kind} - no description"
                else:
                    project_dict[repo.name] = f"{target_kind} - {repo.description}"
        projects: List[FuzzyFinderTarget] = []
        for target in project_dict:
            projects.append(
                FuzzyFinderTarget(name=target, description=project_dict[target])
            )
        if len(projects) == 0:
            self.logger.warning(f"No projects found in workspace: {project_path}")
            return

        finder_config = FuzzyFinderConfig(
            items=projects,
            prompt_text="🔍 Search projects: ",
            max_results=20,
            score_threshold=60.0,
            highlight_color="bold white bg:#0066cc",
            normal_color="cyan",
            prompt_color="bold green",
            separator_color="gray",
            enable_preview=True,
            display_field="name",
            preview_field="description",
            preview_header="About",
        )
        finder = FuzzyFinder(finder_config)
        selected = finder.run()
        if isinstance(selected, Exception):
            raise selected
        if selected is None:
            return None
        else:
            return os.path.join(project_path, selected.name)
