#!/usr/bin/env python

"""
Test script demonstrating FuzzyFinder with object list and preview functionality.
This script shows how to use the FuzzyFinder with a list of objects that have
multiple fields, including a preview field that displays additional information
when an item is selected.
"""

import sys
import traceback
from pathlib import Path
from typing import List

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


class ProjectFile:
    """Example object representing a project file with multiple attributes."""

    def __init__(self, name: str, path: str, size: int, type: str, description: str):
        self.name = name
        self.path = path
        self.size = size
        self.type = type
        self.description = description

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"


def create_sample_project_files() -> List[ProjectFile]:
    """Create a list of sample project files for testing."""
    return [
        ProjectFile(
            name="main.py",
            path="src/main.py",
            size=2048,
            type="Python",
            description="Main application entry point with CLI interface and core functionality",
        ),
        ProjectFile(
            name="config.yaml",
            path="config/config.yaml",
            size=512,
            type="YAML",
            description="Application configuration file with database settings and API keys",
        ),
        ProjectFile(
            name="requirements.txt",
            path="requirements.txt",
            size=256,
            type="Text",
            description="Python dependencies list with version constraints",
        ),
        ProjectFile(
            name="README.md",
            path="README.md",
            size=1024,
            type="Markdown",
            description="Project documentation with installation and usage instructions",
        ),
        ProjectFile(
            name="docker-compose.yml",
            path="docker-compose.yml",
            size=768,
            type="YAML",
            description="Docker Compose configuration for local development environment",
        ),
        ProjectFile(
            name="test_main.py",
            path="tests/test_main.py",
            size=1536,
            type="Python",
            description="Unit tests for main application functionality",
        ),
        ProjectFile(
            name="Dockerfile",
            path="Dockerfile",
            size=640,
            type="Dockerfile",
            description="Docker image configuration for containerized deployment",
        ),
        ProjectFile(
            name="setup.py",
            path="setup.py",
            size=384,
            type="Python",
            description="Package setup script for distribution and installation",
        ),
        ProjectFile(
            name=".env.example",
            path=".env.example",
            size=128,
            type="Environment",
            description="Example environment variables template for configuration",
        ),
        ProjectFile(
            name="api.py",
            path="src/api.py",
            size=1792,
            type="Python",
            description="REST API implementation with FastAPI framework",
        ),
        ProjectFile(
            name="database.py",
            path="src/database.py",
            size=1280,
            type="Python",
            description="Database connection and ORM models using SQLAlchemy",
        ),
        ProjectFile(
            name="utils.py",
            path="src/utils.py",
            size=896,
            type="Python",
            description="Utility functions for common operations and helpers",
        ),
        ProjectFile(
            name="models.py",
            path="src/models.py",
            size=1024,
            type="Python",
            description="Data models and Pydantic schemas for API validation",
        ),
        ProjectFile(
            name="middleware.py",
            path="src/middleware.py",
            size=768,
            type="Python",
            description="Custom middleware for authentication and logging",
        ),
        ProjectFile(
            name="cli.py",
            path="src/cli.py",
            size=1152,
            type="Python",
            description="Command-line interface implementation using Click",
        ),
    ]


def format_preview_text(file_obj: ProjectFile) -> str:
    """Format the preview text for a project file."""
    return f"""
File: {file_obj.name}
Path: {file_obj.path}
Type: {file_obj.type}
Size: {file_obj.size} bytes
Description: {file_obj.description}
""".strip()


def main():
    """Main function to demonstrate FuzzyFinder with preview functionality."""
    print("FuzzyFinder Preview Test")
    print("=" * 50)
    print("This demo shows FuzzyFinder with a list of project files.")
    print("Use arrow keys to navigate, type to search, and Enter to select.")
    print("The preview pane shows detailed information about the selected file.")
    print()

    # Create sample data
    project_files = create_sample_project_files()

    # Configure FuzzyFinder with preview enabled
    config = FuzzyFinderConfig(
        items=project_files,
        display_field="name",  # Use the 'name' field for display/search
        preview_field="description",  # Use 'description' for preview
        enable_preview=True,
        prompt_text="Search files: ",
        max_results=8,
        score_threshold=60.0,
        scorer="partial_ratio",
        case_sensitive=False,
        # Custom styling
        highlight_color="bold white bg:#0066cc",
        normal_color="white",
        prompt_color="bold green",
        separator_color="gray",
    )

    # Create and run the fuzzy finder
    finder = FuzzyFinder(config)

    print("Starting FuzzyFinder...")
    print("(Press Ctrl+C to exit)")
    print()

    try:
        result = finder.run()

        if isinstance(result, Exception):
            print(f"Error occurred: {result}")
            return

        if result is None:
            print("No selection made.")
        else:
            selected_file = result
            print(f"\nSelected: {selected_file.name}")
            print(f"Path: {selected_file.path}")
            print(f"Type: {selected_file.type}")
            print(f"Size: {selected_file.size} bytes")
            print(f"Description: {selected_file.description}")

    except KeyboardInterrupt:
        print("\nExited by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[TOP-LEVEL EXCEPTION]", e)
        print(traceback.format_exc())
