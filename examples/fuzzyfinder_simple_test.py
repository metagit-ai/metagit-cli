#!/usr/bin/env python

"""
Simple test script demonstrating basic FuzzyFinder functionality.
This script shows how to use the FuzzyFinder with a simple list of strings.
"""

import sys
from pathlib import Path
from typing import List

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


def create_sample_strings() -> List[str]:
    """Create a list of sample strings for testing."""
    return [
        "python",
        "javascript",
        "typescript",
        "golang",
        "rust",
        "c++",
        "java",
        "kotlin",
        "swift",
        "dart",
        "flutter",
        "react",
        "vue",
        "angular",
        "node.js",
        "express",
        "fastapi",
        "django",
        "flask",
        "spring",
        "laravel",
        "rails",
        "asp.net",
        "php",
        "ruby",
        "scala",
        "clojure",
        "haskell",
        "erlang",
        "elixir",
        "metagit",
        "metagit_cli",
        "metagit_api",
        "metagit_web",
    ]


def main():
    """Main function to demonstrate basic FuzzyFinder functionality."""
    print("Simple FuzzyFinder Test")
    print("=" * 30)
    print("This demo shows FuzzyFinder with a simple list of programming languages.")
    print("Use arrow keys to navigate, type to search, and Enter to select.")
    print()

    # Create sample data
    languages = create_sample_strings()

    # Configure FuzzyFinder
    config = FuzzyFinderConfig(
        items=languages,
        prompt_text="Search languages: ",
        max_results=10,
        score_threshold=50.0,
        scorer="partial_ratio",
        case_sensitive=False,
        # Custom styling
        highlight_color="bold white bg:#00aa00",
        normal_color="white",
        prompt_color="bold blue",
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
            print(f"\nSelected language: {result}")

    except KeyboardInterrupt:
        print("\nExited by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
