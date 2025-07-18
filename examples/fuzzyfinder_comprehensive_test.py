#!/usr/bin/env python

"""
Comprehensive test script demonstrating all FuzzyFinder features.
This script shows various configurations and use cases for the FuzzyFinder.
"""

import sys
from pathlib import Path
from typing import List, Optional

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


class FileItem:
    """Example object representing a file with multiple attributes."""

    def __init__(
        self,
        name: str,
        path: str,
        size: int,
        type: str,
        description: str,
        tags: List[str],
    ):
        self.name = name
        self.path = path
        self.size = size
        self.type = type
        self.description = description
        self.tags = tags

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"

    def get_preview_text(self) -> str:
        """Get formatted preview text for this file."""
        return f"""File: {self.name}
Path: {self.path}
Type: {self.type}
Size: {self.size:,} bytes
Tags: {', '.join(self.tags)}
Description: {self.description}"""


def create_sample_files() -> List[FileItem]:
    """Create a list of sample files for testing."""
    return [
        FileItem(
            name="main.py",
            path="src/main.py",
            size=2048,
            type="Python",
            description="Main application entry point with CLI interface and core functionality",
            tags=["python", "cli", "main"],
        ),
        FileItem(
            name="config.yaml",
            path="config/config.yaml",
            size=512,
            type="YAML",
            description="Application configuration file with database settings and API keys",
            tags=["config", "yaml", "settings"],
        ),
        FileItem(
            name="requirements.txt",
            path="requirements.txt",
            size=256,
            type="Text",
            description="Python dependencies list with version constraints",
            tags=["dependencies", "python", "requirements"],
        ),
        FileItem(
            name="README.md",
            path="README.md",
            size=1024,
            type="Markdown",
            description="Project documentation with installation and usage instructions",
            tags=["documentation", "markdown", "readme"],
        ),
        FileItem(
            name="docker-compose.yml",
            path="docker-compose.yml",
            size=768,
            type="YAML",
            description="Docker Compose configuration for local development environment",
            tags=["docker", "yaml", "devops"],
        ),
        FileItem(
            name="test_main.py",
            path="tests/test_main.py",
            size=1536,
            type="Python",
            description="Unit tests for main application functionality",
            tags=["python", "tests", "unit"],
        ),
        FileItem(
            name="Dockerfile",
            path="Dockerfile",
            size=640,
            type="Dockerfile",
            description="Docker image configuration for containerized deployment",
            tags=["docker", "container", "deployment"],
        ),
        FileItem(
            name="setup.py",
            path="setup.py",
            size=384,
            type="Python",
            description="Package setup script for distribution and installation",
            tags=["python", "setup", "distribution"],
        ),
        FileItem(
            name=".env.example",
            path=".env.example",
            size=128,
            type="Environment",
            description="Example environment variables template for configuration",
            tags=["config", "environment", "template"],
        ),
        FileItem(
            name="api.py",
            path="src/api.py",
            size=1792,
            type="Python",
            description="REST API implementation with FastAPI framework",
            tags=["python", "api", "fastapi", "rest"],
        ),
        FileItem(
            name="database.py",
            path="src/database.py",
            size=1280,
            type="Python",
            description="Database connection and ORM models using SQLAlchemy",
            tags=["python", "database", "sqlalchemy", "orm"],
        ),
        FileItem(
            name="utils.py",
            path="src/utils.py",
            size=896,
            type="Python",
            description="Utility functions for common operations and helpers",
            tags=["python", "utils", "helpers"],
        ),
        FileItem(
            name="models.py",
            path="src/models.py",
            size=1024,
            type="Python",
            description="Data models and Pydantic schemas for API validation",
            tags=["python", "models", "pydantic", "validation"],
        ),
        FileItem(
            name="middleware.py",
            path="src/middleware.py",
            size=768,
            type="Python",
            description="Custom middleware for authentication and logging",
            tags=["python", "middleware", "auth", "logging"],
        ),
        FileItem(
            name="cli.py",
            path="src/cli.py",
            size=1152,
            type="Python",
            description="Command-line interface implementation using Click",
            tags=["python", "cli", "click"],
        ),
    ]


def run_fuzzyfinder_test(
    title: str, config: FuzzyFinderConfig, description: str
) -> Optional[FileItem]:
    """Run a specific FuzzyFinder test configuration."""
    print(f"\n{title}")
    print("=" * len(title))
    print(description)
    print()

    try:
        finder = FuzzyFinder(config)
        result = finder.run()

        if isinstance(result, Exception):
            print(f"Error occurred: {result}")
            return None

        return result
    except KeyboardInterrupt:
        print("\nExited by user.")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def main():
    """Main function to demonstrate various FuzzyFinder configurations."""
    print("Comprehensive FuzzyFinder Test Suite")
    print("=" * 50)
    print("This demo shows various configurations and features of FuzzyFinder.")
    print("Each test will show a different aspect of the functionality.")
    print()

    # Create sample data
    files = create_sample_files()

    # Test 1: Basic functionality with preview
    print("Test 1: Basic functionality with preview enabled")
    config1 = FuzzyFinderConfig(
        items=files,
        display_field="name",
        preview_field="description",
        enable_preview=True,
        prompt_text="Search files: ",
        max_results=6,
        score_threshold=60.0,
        scorer="partial_ratio",
        case_sensitive=False,
        highlight_color="bold white bg:#0066cc",
        normal_color="white",
        prompt_color="bold green",
        separator_color="gray",
    )

    result1 = run_fuzzyfinder_test(
        "Test 1: Basic with Preview",
        config1,
        "Search through files with preview pane showing descriptions. Try typing 'py' or 'test'.",
    )

    if result1:
        print(f"\nSelected: {result1.name}")
        print(f"Description: {result1.description}")

    # Test 2: Different scorer
    print("\nTest 2: Using token_sort_ratio scorer")
    config2 = FuzzyFinderConfig(
        items=files,
        display_field="name",
        preview_field="description",
        enable_preview=True,
        prompt_text="Search (token_sort): ",
        max_results=6,
        score_threshold=50.0,
        scorer="token_sort_ratio",
        case_sensitive=False,
        highlight_color="bold white bg:#cc6600",
        normal_color="white",
        prompt_color="bold orange",
        separator_color="gray",
    )

    result2 = run_fuzzyfinder_test(
        "Test 2: Token Sort Ratio Scorer",
        config2,
        "This scorer is better for word order variations. Try typing 'main test' or 'api python'.",
    )

    if result2:
        print(f"\nSelected: {result2.name}")
        print(f"Description: {result2.description}")

    # Test 3: Case sensitive search
    print("\nTest 3: Case sensitive search")
    config3 = FuzzyFinderConfig(
        items=files,
        display_field="name",
        preview_field="description",
        enable_preview=True,
        prompt_text="Search (case-sensitive): ",
        max_results=6,
        score_threshold=70.0,
        scorer="partial_ratio",
        case_sensitive=True,
        highlight_color="bold white bg:#6600cc",
        normal_color="white",
        prompt_color="bold purple",
        separator_color="gray",
    )

    result3 = run_fuzzyfinder_test(
        "Test 3: Case Sensitive Search",
        config3,
        "Case sensitive matching. Try 'PY' vs 'py' to see the difference.",
    )

    if result3:
        print(f"\nSelected: {result3.name}")
        print(f"Description: {result3.description}")

    # Test 4: Higher threshold
    print("\nTest 4: Higher score threshold")
    config4 = FuzzyFinderConfig(
        items=files,
        display_field="name",
        preview_field="description",
        enable_preview=True,
        prompt_text="Search (high threshold): ",
        max_results=6,
        score_threshold=85.0,
        scorer="partial_ratio",
        case_sensitive=False,
        highlight_color="bold white bg:#cc0066",
        normal_color="white",
        prompt_color="bold pink",
        separator_color="gray",
    )

    result4 = run_fuzzyfinder_test(
        "Test 4: High Score Threshold",
        config4,
        "Higher threshold means more exact matches required. Try partial matches.",
    )

    if result4:
        print(f"\nSelected: {result4.name}")
        print(f"Description: {result4.description}")

    print("\nAll tests completed!")
    print("You can run individual tests by modifying the script.")


if __name__ == "__main__":
    main()
