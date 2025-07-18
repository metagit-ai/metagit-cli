#!/usr/bin/env python3

"""
Example demonstrating how to load DetectionManagerConfig from YAML files.
"""

import sys
from pathlib import Path

import yaml

# Add the metagit package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metagit.core.detect.manager import DetectionManager, DetectionManagerConfig


def load_config_from_yaml(
    file_path: str, config_name: str = "default"
) -> DetectionManagerConfig:
    """
    Load a DetectionManagerConfig from a YAML file.

    Args:
        file_path: Path to the YAML configuration file
        config_name: Name of the configuration section to load

    Returns:
        DetectionManagerConfig instance
    """
    try:
        with open(file_path, "r") as f:
            configs = yaml.safe_load(f)

        if config_name not in configs:
            raise ValueError(f"Configuration '{config_name}' not found in {file_path}")

        config_data = configs[config_name]
        return DetectionManagerConfig(**config_data)

    except Exception as e:
        print(f"Error loading configuration: {e}")
        # Fallback to default configuration
        return DetectionManagerConfig()


def example_load_from_yaml():
    """Demonstrate loading configurations from YAML file."""
    print("=== Loading Configuration from YAML ===")

    config_file = Path(__file__).parent / "detection_config_example.yml"

    # Load different configurations
    configs_to_load = [
        "default",
        "minimal",
        "comprehensive",
        "cicd_focused",
        "directory_focused",
    ]

    for config_name in configs_to_load:
        print(f"\nLoading '{config_name}' configuration:")
        config = load_config_from_yaml(str(config_file), config_name)
        enabled_methods = config.get_enabled_methods()
        print(f"  Enabled methods: {', '.join(enabled_methods)}")

    print()


def example_use_loaded_config():
    """Demonstrate using a loaded configuration with DetectionManager."""
    print("=== Using Loaded Configuration ===")

    config_file = Path(__file__).parent / "detection_config_example.yml"

    # Load minimal configuration
    config = load_config_from_yaml(str(config_file), "minimal")
    print(f"Using 'minimal' configuration: {', '.join(config.get_enabled_methods())}")

    # Create DetectionManager with loaded config
    manager = DetectionManager(path="./", config=config)

    # Run analysis
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


def example_create_yaml_config():
    """Demonstrate creating a YAML configuration file programmatically."""
    print("=== Creating YAML Configuration ===")

    # Create different configurations
    configs = {
        "custom_analysis": DetectionManagerConfig(
            branch_analysis_enabled=True,
            ci_config_analysis_enabled=False,
            directory_summary_enabled=True,
            directory_details_enabled=True,
            commit_analysis_enabled=False,
            tag_analysis_enabled=False,
        ),
        "git_only": DetectionManagerConfig(
            branch_analysis_enabled=True,
            ci_config_analysis_enabled=False,
            directory_summary_enabled=False,
            directory_details_enabled=False,
            commit_analysis_enabled=True,
            tag_analysis_enabled=True,
        ),
    }

    # Convert to YAML
    yaml_data = {}
    for name, config in configs.items():
        yaml_data[name] = config.model_dump()

    # Print YAML
    yaml_output = yaml.dump(yaml_data, default_flow_style=False, sort_keys=False)
    print("Generated YAML configuration:")
    print(yaml_output)

    # Save to file
    output_file = Path(__file__).parent / "generated_config.yml"
    with open(output_file, "w") as f:
        f.write(yaml_output)

    print(f"Configuration saved to: {output_file}")
    print()


if __name__ == "__main__":
    print("DetectionManagerConfig YAML Loading Examples\n")

    try:
        example_load_from_yaml()
        example_use_loaded_config()
        example_create_yaml_config()

        print("All YAML configuration examples completed successfully!")

    except Exception as e:
        print(f"Error running examples: {e}")
        sys.exit(1)
