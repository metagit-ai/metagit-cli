#!/usr/bin/env python3

"""
Example demonstrating the new DetectionManager as the single entrypoint for detection analysis.

This example shows how DetectionManager inherits from MetagitRecord and serves as the
unified interface for analyzing git repositories and projects.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.detect.manager import DetectionManager, DetectionManagerConfig


def example_local_repository_analysis():
    """Demonstrate analyzing a local repository."""
    print("=== Local Repository Analysis ===")

    # Create DetectionManager for local path
    manager = DetectionManager.from_path("./")
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    print(f"Created DetectionManager for: {manager.path}")
    print(f"Project name: {manager.name}")
    print(f"Detection source: {manager.detection_source}")

    # Run all analyses
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    print("Analysis completed successfully!")
    print(f"Detection timestamp: {manager.detection_timestamp}")
    print()


def example_remote_repository_analysis():
    """Demonstrate analyzing a remote repository."""
    print("=== Remote Repository Analysis ===")

    # Example repository URL
    repo_url = "https://github.com/octocat/Hello-World.git"

    # Create DetectionManager for remote URL
    manager = DetectionManager.from_url(repo_url)
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    print(f"Created DetectionManager for: {manager.url}")
    print(f"Project name: {manager.name}")
    print(f"Detection source: {manager.detection_source}")

    # Run all analyses
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    print("Analysis completed successfully!")
    print(f"Detection timestamp: {manager.detection_timestamp}")

    # Clean up cloned repository
    manager.cleanup()
    print()


def example_custom_configuration():
    """Demonstrate using custom detection configuration."""
    print("=== Custom Configuration ===")

    # Create custom configuration
    config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=True,
        directory_summary_enabled=False,  # Disable for faster analysis
        directory_details_enabled=False,  # Disable for faster analysis
        commit_analysis_enabled=False,
        tag_analysis_enabled=False,
    )

    print(f"Custom config enabled methods: {', '.join(config.get_enabled_methods())}")

    # Create DetectionManager with custom config
    manager = DetectionManager.from_path("./", config=config)
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    # Run analyses
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    print("Analysis completed with custom configuration")
    print()


def example_metagit_record_integration():
    """Demonstrate MetagitRecord integration."""
    print("=== MetagitRecord Integration ===")

    # Create DetectionManager
    manager = DetectionManager.from_path("./")
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    # Run analysis
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    # Access MetagitRecord fields
    print("MetagitRecord fields:")
    print(f"  Name: {manager.name}")
    print(f"  Description: {manager.description}")
    print(f"  Kind: {manager.kind}")
    print(f"  Domain: {manager.domain}")
    print(f"  Language: {manager.language}")
    print(f"  Language Version: {manager.language_version}")
    print(f"  Branch Strategy: {manager.branch_strategy}")
    print(f"  URL: {manager.url}")
    print(f"  Path: {manager.path}")

    # Access detection-specific fields
    print("\nDetection-specific fields:")
    print(f"  Detection Timestamp: {manager.detection_timestamp}")
    print(f"  Detection Source: {manager.detection_source}")
    print(f"  Detection Version: {manager.detection_version}")
    print(f"  Has Branch Analysis: {manager.branch_analysis is not None}")
    print(f"  Has CI/CD Analysis: {manager.ci_config_analysis is not None}")
    print(f"  Has Directory Summary: {manager.directory_summary is not None}")
    print(f"  Has Directory Details: {manager.directory_details is not None}")
    print(f"  Has Repository Analysis: {manager.repository_analysis is not None}")

    # Access detection results
    if manager.branch_analysis:
        print(f"  Branch Strategy Guess: {manager.branch_analysis.strategy_guess}")
        print(f"  Number of Branches: {len(manager.branch_analysis.branches)}")

    if manager.ci_config_analysis:
        print(f"  CI/CD Tool: {manager.ci_config_analysis.detected_tool}")

    if manager.directory_summary:
        print(f"  Total Files: {manager.directory_summary.num_files}")
        print(f"  File Types: {len(manager.directory_summary.file_types)}")

    print()


def example_output_formats():
    """Demonstrate different output formats."""
    print("=== Output Formats ===")

    # Create DetectionManager
    manager = DetectionManager.from_path("./")
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    # Run analysis
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    # Summary output
    summary = manager.summary()
    if isinstance(summary, Exception):
        print(f"Error getting summary: {summary}")
    else:
        print("Summary output:")
        print(summary[:200] + "..." if len(summary) > 200 else summary)
        print()

    # YAML output (includes all detection data)
    yaml_output = manager.to_yaml()
    if isinstance(yaml_output, Exception):
        print(f"Error converting to YAML: {yaml_output}")
    else:
        print("YAML output (first 200 chars):")
        print(yaml_output[:200] + "..." if len(yaml_output) > 200 else yaml_output)
        print()

    # JSON output (includes all detection data)
    json_output = manager.to_json()
    if isinstance(json_output, Exception):
        print(f"Error converting to JSON: {json_output}")
    else:
        print("JSON output (first 200 chars):")
        print(json_output[:200] + "..." if len(json_output) > 200 else json_output)
        print()


def example_existing_config_loading():
    """Demonstrate loading existing metagitconfig data."""
    print("=== Existing Config Loading ===")

    # Create DetectionManager (will automatically load .metagit.yml if it exists)
    manager = DetectionManager.from_path("./")
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    print(f"Project name: {manager.name}")
    print(f"Project description: {manager.description}")
    print(f"Project kind: {manager.kind}")

    # Check if existing config was loaded
    if manager.description and manager.description != "No description":
        print("✅ Existing metagitconfig data was loaded and merged")
    else:
        print("ℹ️  No existing metagitconfig found, using defaults")

    print()


def example_specific_analysis_methods():
    """Demonstrate running specific analysis methods."""
    print("=== Specific Analysis Methods ===")

    # Create DetectionManager with minimal config
    config = DetectionManagerConfig.minimal()
    manager = DetectionManager.from_path("./", config=config)
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

    # Run specific methods
    methods = ["branch_analysis", "ci_config_analysis"]

    for method in methods:
        print(f"Running {method}...")
        result = manager.run_specific(method)
        if result is not None:
            print(f"Error running {method}: {result}")
        else:
            print(f"✅ {method} completed successfully")

    print()


if __name__ == "__main__":
    print("DetectionManager Examples")
    print("=" * 60)

    try:
        example_local_repository_analysis()
        example_custom_configuration()
        example_metagit_record_integration()
        example_output_formats()
        example_existing_config_loading()
        example_specific_analysis_methods()

        # Uncomment to test remote repository analysis
        # example_remote_repository_analysis()

        print("All examples completed successfully!")

    except Exception as e:
        print(f"Error running examples: {e}")
        sys.exit(1)
