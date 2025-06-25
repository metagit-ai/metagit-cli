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
    manager = DetectionManager.from_path("./")
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

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

    manager = DetectionManager.from_path("./", config=config)
    if isinstance(manager, Exception):
        print(f"Error creating DetectionManager: {manager}")
        return

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
    """Demonstrate configuration serialization."""
    print("=== Configuration Serialization ===")

    # Create a configuration
    config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=True,
        directory_summary_enabled=False,
        directory_details_enabled=True,
    )

    # Convert to dict
    config_dict = config.model_dump()
    print(f"Configuration as dict: {config_dict}")

    # Create from dict
    new_config = DetectionManagerConfig(**config_dict)
    print(
        f"Recreated config enabled methods: {', '.join(new_config.get_enabled_methods())}"
    )
    print()


def example_metagit_record_integration():
    """Demonstrate MetagitRecord integration."""
    print("=== MetagitRecord Integration ===")

    # Create DetectionManager (inherits from MetagitRecord)
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
    print(f"Project name: {manager.name}")
    print(f"Project path: {manager.path}")
    print(f"Detection timestamp: {manager.detection_timestamp}")
    print(f"Detection source: {manager.detection_source}")
    print(f"Detection version: {manager.detection_version}")

    # Access detection-specific fields
    print(
        f"Branch analysis enabled: {manager.detection_config.branch_analysis_enabled}"
    )
    print(f"Has branch analysis: {manager.branch_analysis is not None}")
    print(f"Has CI/CD analysis: {manager.ci_config_analysis is not None}")

    # Convert to YAML (includes both MetagitRecord and detection data)
    yaml_output = manager.to_yaml()
    if isinstance(yaml_output, Exception):
        print(f"Error converting to YAML: {yaml_output}")
    else:
        print("Successfully converted to YAML (includes all detection data)")
    print()


if __name__ == "__main__":
    print("DetectionManagerConfig Examples\n")

    try:
        example_basic_usage()
        example_custom_config()
        example_preset_configs()
        example_specific_method()
        example_config_serialization()
        example_metagit_record_integration()

        print("All examples completed successfully!")

    except Exception as e:
        print(f"Error running examples: {e}")
        sys.exit(1)
