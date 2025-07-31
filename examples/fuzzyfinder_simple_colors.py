#!/usr/bin/env python
"""
Simple example showing how to use custom colors in FuzzyFinder.
This demonstrates coloring items based on their type or priority.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


def main():
    """Demonstrate custom colors with a simple task list."""

    # Create a list of tasks with different types
    tasks = [
        "bug_fix_login",
        "bug_fix_payment",
        "feature_dashboard",
        "feature_notifications",
        "docs_api_reference",
        "docs_user_guide",
        "test_user_flow",
        "test_integration",
    ]

    # Define colors based on task type (prefix)
    task_colors = {
        "bug_fix_login": "bold red",  # Critical bugs in red
        "bug_fix_payment": "bold red",  # Critical bugs in red
        "feature_dashboard": "green",  # Features in green
        "feature_notifications": "green",  # Features in green
        "docs_api_reference": "blue",  # Documentation in blue
        "docs_user_guide": "blue",  # Documentation in blue
        "test_user_flow": "cyan",  # Tests in cyan
        "test_integration": "cyan",  # Tests in cyan
    }

    print("🎨 Custom Colors FuzzyFinder Example")
    print("=" * 40)
    print("Each task type has its own color:")
    print("🔴 Bugs: Red")
    print("🟢 Features: Green")
    print("🔵 Documentation: Blue")
    print("🟦 Tests: Cyan")
    print()

    # Configure FuzzyFinder with custom colors
    config = FuzzyFinderConfig(
        items=tasks,
        prompt_text="🔍 Search tasks: ",
        custom_colors=task_colors,
        max_results=10,
        highlight_color="bold white bg:#4400aa",
        item_opacity=0.9,
    )

    # Run the finder
    finder = FuzzyFinder(config)

    print("Starting FuzzyFinder with custom colors...")
    print("Notice how each task type is colored differently!")

    try:
        result = finder.run()

        if result:
            task_type = result.split("_")[0]
            print(f"\n✅ Selected: {result}")
            print(f"📋 Task type: {task_type}")
        else:
            print("\n👋 No selection made.")

    except KeyboardInterrupt:
        print("\n👋 Exited by user.")


if __name__ == "__main__":
    main()
