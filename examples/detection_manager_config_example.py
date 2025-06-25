#!/usr/bin/env python3

"""
Example demonstrating the use of DetectionManagerConfig to control which analysis methods are enabled.
"""

import sys
from pathlib import Path

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.detect.manager import DetectionManager, DetectionManagerConfig


def example_basic_usage():
    """Demonstrate basic usage with default configuration."""
    print("=== Basic Usage (Default Configuration) ===")

    # Create a DetectionManager with default config (all enabled)
    manager = DetectionManager(path="./")

    # Run all enabled analyses
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    # Print summary
    summary = manager.summary()
    if isinstance(summary, Exception):
        print(f"Error getting summary: {summary}")
    else:
        print(summary)
    print()


def example_custom_config():
    """Demonstrate usage with custom configuration."""
    print("=== Custom Configuration ===")

    # Create a custom configuration
    config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=True,
        directory_summary_enabled=False,  # Disable directory summary
        directory_details_enabled=False,  # Disable directory details
        commit_analysis_enabled=False,
        tag_analysis_enabled=False,
    )

    # Create manager with custom config
    manager = DetectionManager(path="./", config=config)

    print(f"Enabled methods: {', '.join(config.get_enabled_methods())}")

    # Run all enabled analyses
    result = manager.run_all()
    if result is not None:
        print(f"Error running analysis: {result}")
        return

    # Print summary
    summary = manager.summary()
    if isinstance(summary, Exception):
        print(f"Error getting summary: {summary}")
    else:
        print(summary)
    print()


def example_preset_configs():
    """Demonstrate usage with preset configurations."""
    print("=== Preset Configurations ===")

    # Use minimal configuration
    minimal_config = DetectionManagerConfig.minimal()
    print(
        f"Minimal config enabled methods: {', '.join(minimal_config.get_enabled_methods())}"
    )

    # Use all enabled configuration
    all_enabled_config = DetectionManagerConfig.all_enabled()
    print(
        f"All enabled config methods: {', '.join(all_enabled_config.get_enabled_methods())}"
    )
    print()


def example_specific_method():
    """Demonstrate running a specific analysis method."""
    print("=== Running Specific Method ===")

    # Create a configuration with only branch analysis enabled
    config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=False,
        directory_summary_enabled=False,
        directory_details_enabled=False,
        commit_analysis_enabled=False,
        tag_analysis_enabled=False,
    )

    manager = DetectionManager(path="./", config=config)

    # Run only branch analysis
    result = manager.run_specific("branch_analysis")
    if result is not None:
        print(f"Error running branch analysis: {result}")
        return

    print("Branch analysis completed successfully")
    if manager.branch_analysis:
        print(f"Detected strategy: {manager.branch_analysis.strategy_guess}")
    print()


def example_config_serialization():
    """Demonstrate serializing and deserializing configurations."""
    print("=== Configuration Serialization ===")

    # Create a custom configuration
    config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=False,
        directory_summary_enabled=True,
        directory_details_enabled=False,
    )

    # Convert to dict
    config_dict = config.model_dump()
    print(f"Config as dict: {config_dict}")

    # Convert to JSON
    config_json = config.model_dump_json()
    print(f"Config as JSON: {config_json}")

    # Recreate from dict
    recreated_config = DetectionManagerConfig(**config_dict)
    print(
        f"Recreated config enabled methods: {', '.join(recreated_config.get_enabled_methods())}"
    )
    print()


if __name__ == "__main__":
    print("DetectionManagerConfig Examples\n")

    try:
        example_basic_usage()
        example_custom_config()
        example_preset_configs()
        example_specific_method()
        example_config_serialization()

        print("All examples completed successfully!")

    except Exception as e:
        print(f"Error running examples: {e}")
        sys.exit(1)
