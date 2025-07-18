#!/usr/bin/env python
"""
Example script demonstrating the new record CLI commands.

This script shows how to use the record management commands programmatically.
"""

import subprocess
from pathlib import Path


def run_metagit_command(args: list) -> tuple[int, str, str]:
    """Run a metagit command and return the result."""
    try:
        result = subprocess.run(
            ["python", "-m", "metagit.cli.main"] + args,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def create_sample_config():
    """Create a sample .metagit.yml file for testing."""
    config_content = """
name: example-project
description: An example project for testing record management
url: https://github.com/example/example-project
kind: application
documentation:
  - README.md
  - docs/
license:
  kind: MIT
  file: LICENSE
maintainers:
  - name: John Doe
    email: john@example.com
    role: Maintainer
branch_strategy: trunk
taskers:
  - kind: Taskfile
artifacts:
  - type: docker
    definition: Dockerfile
    location: docker.io/example/project
    version_strategy: semver
cicd:
  platform: GitHub
  pipelines:
    - name: CI
      ref: .github/workflows/ci.yml
deployment:
  strategy: rolling
  environments:
    - name: staging
      url: https://staging.example.com
    - name: production
      url: https://example.com
observability:
  logging_provider: console
  monitoring_providers:
    - prometheus
  alerting_channels:
    - name: slack
      type: slack
      url: https://hooks.slack.com/services/xxx
"""

    with open(".metagit.yml", "w") as f:
        f.write(config_content)

    print("Created sample .metagit.yml file")


def example_record_commands():
    """Demonstrate the record CLI commands."""
    print("Metagit Record CLI Examples")
    print("=" * 50)

    # Create sample config
    print("1. Creating sample configuration...")
    create_sample_config()

    # Test record create
    print("\n2. Creating a record from configuration...")
    returncode, stdout, stderr = run_metagit_command(
        [
            "record",
            "create",
            "--config-path",
            ".metagit.yml",
            "--detection-source",
            "cli-example",
            "--detection-version",
            "1.0.0",
            "--output-file",
            "example-record.yml",
        ]
    )

    if returncode == 0:
        print("✅ Record created successfully")
        print(f"Output: {stdout}")
    else:
        print(f"❌ Failed to create record: {stderr}")
        return

    # Test record show (list all)
    print("\n3. Listing all records...")
    returncode, stdout, stderr = run_metagit_command(["record", "show"])

    if returncode == 0:
        print("✅ Records listed successfully")
        print(f"Output: {stdout}")
    else:
        print(f"❌ Failed to list records: {stderr}")

    # Test record search
    print("\n4. Searching for records...")
    returncode, stdout, stderr = run_metagit_command(
        ["record", "search", "example", "--format", "table"]
    )

    if returncode == 0:
        print("✅ Search completed successfully")
        print(f"Output: {stdout}")
    else:
        print(f"❌ Failed to search records: {stderr}")

    # Test record stats
    print("\n5. Getting record statistics...")
    returncode, stdout, stderr = run_metagit_command(["record", "stats"])

    if returncode == 0:
        print("✅ Statistics retrieved successfully")
        print(f"Output: {stdout}")
    else:
        print(f"❌ Failed to get statistics: {stderr}")

    # Test record export
    print("\n6. Exporting a record...")
    returncode, stdout, stderr = run_metagit_command(
        ["record", "export", "1", "exported-record.yml", "--format", "yaml"]
    )

    if returncode == 0:
        print("✅ Record exported successfully")
        print(f"Output: {stdout}")
    else:
        print(f"❌ Failed to export record: {stderr}")

    # Test record import
    print("\n7. Importing a record...")
    returncode, stdout, stderr = run_metagit_command(
        [
            "record",
            "import",
            "exported-record.yml",
            "--detection-source",
            "imported",
            "--detection-version",
            "2.0.0",
        ]
    )

    if returncode == 0:
        print("✅ Record imported successfully")
        print(f"Output: {stdout}")
    else:
        print(f"❌ Failed to import record: {stderr}")

    # Test OpenSearch backend (if available)
    print("\n8. Testing OpenSearch backend...")
    returncode, stdout, stderr = run_metagit_command(
        [
            "record",
            "--storage-type",
            "opensearch",
            "--opensearch-hosts",
            "localhost:9200",
            "--opensearch-index",
            "metagit-records-test",
            "show",
        ]
    )

    if returncode == 0:
        print("✅ OpenSearch backend test successful")
        print(f"Output: {stdout}")
    else:
        print(
            f"⚠️  OpenSearch backend test failed (expected if OpenSearch not running): {stderr}"
        )

    print("\n🎉 Record CLI examples completed!")


def cleanup():
    """Clean up test files."""
    files_to_remove = [
        ".metagit.yml",
        "example-record.yml",
        "exported-record.yml",
    ]

    for file_path in files_to_remove:
        if Path(file_path).exists():
            Path(file_path).unlink()
            print(f"Cleaned up: {file_path}")


if __name__ == "__main__":
    try:
        example_record_commands()
    finally:
        cleanup()
