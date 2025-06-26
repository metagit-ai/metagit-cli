#!/usr/bin/env python

"""
Debug test script for FuzzyFinder to verify fixes.
This script tests basic functionality with minimal configuration.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


def main():
    """Simple test to verify FuzzyFinder works."""
    print("FuzzyFinder Debug Test")
    print("=" * 30)
    print("Testing basic functionality...")
    print()

    # Simple string list
    items = ["python", "javascript", "typescript", "golang", "rust"]

    # Basic configuration
    config = FuzzyFinderConfig(
        items=items,
        prompt_text="Search: ",
        max_results=5,
        score_threshold=50.0,
        enable_preview=False,  # Disable preview for basic test
    )

    print("Starting FuzzyFinder...")
    print("Type to search, use arrow keys to navigate, Enter to select, Ctrl+C to exit")
    print()

    try:
        finder = FuzzyFinder(config)
        result = finder.run()

        if isinstance(result, Exception):
            print(f"Error occurred: {result}")
            return

        if result is None:
            print("No selection made.")
        else:
            print(f"Selected: {result}")

    except KeyboardInterrupt:
        print("\nExited by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
