#!/usr/bin/env python
"""
List git files in a repository.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.utils.files import list_git_files


def main():
    """List all git files in the current repository."""

    # Get the current working directory
    repo_path = Path.cwd()

    print(f"Listing git files in repository: {repo_path}")

    # List git files
    git_files = list_git_files(repo_path)

    if not git_files:
        print("No git files found.")
        return

    print(f"Found {len(git_files)} git files:")
    for file in git_files:
        print(f"- {file}")


if __name__ == "__main__":
    main()
