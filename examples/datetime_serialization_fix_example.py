#!/usr/bin/env python
"""
Example demonstrating the datetime serialization fix for metagit records.

This example shows how the DateTimeEncoder handles datetime objects when
serializing MetagitRecord objects to JSON, fixing the "Object of type datetime
is not JSON serializable" error.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.record.manager import LocalFileStorageBackend, MetagitRecordManager
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger


def demonstrate_datetime_serialization_fix():
    """Demonstrate the datetime serialization fix."""
    print("🔧 Datetime Serialization Fix Demonstration")
    print("=" * 50)

    # Show the problem (without DateTimeEncoder)
    print("\n1. The Problem:")
    print(
        "   When trying to serialize datetime objects to JSON without a custom encoder:"
    )

    test_data = {
        "name": "test-project",
        "description": "A test project",
        "detection_timestamp": datetime.now(),
        "last_updated": datetime.now(),
    }

    try:
        # This would fail without DateTimeEncoder
        json.dumps(test_data)
        print("   ✓ JSON serialization works (with fix)")
    except TypeError as e:
        print(f"   ✗ JSON serialization fails: {e}")

    # Show the solution
    print("\n2. The Solution:")
    print("   Using DateTimeEncoder to handle datetime objects:")

    class DateTimeEncoder(json.JSONEncoder):
        """Custom JSON encoder that handles datetime objects."""

        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)

    try:
        json_str = json.dumps(test_data, cls=DateTimeEncoder, indent=2)
        print("   ✓ JSON serialization works with DateTimeEncoder")
        print(f"   Serialized output:\n{json_str}")
    except Exception as e:
        print(f"   ✗ JSON serialization still fails: {e}")

    return True


async def demonstrate_record_creation():
    """Demonstrate record creation with datetime handling."""
    print("\n3. Record Creation with Datetime Handling:")
    print("=" * 50)

    try:
        # Check if config file exists
        config_path = Path("metagit.config.yaml")
        if not config_path.exists():
            print("   ⚠️  metagit.config.yaml not found, creating a simple example...")

            # Create a simple config for demonstration
            from metagit.core.config.models import (
                MetagitConfig,
                ProjectKind,
                ProjectType,
            )

            config = MetagitConfig(
                name="example-project",
                description="An example project for datetime serialization testing",
                type=ProjectType.APPLICATION,
                kind=ProjectKind.WEB_APP,
                detection_timestamp=datetime.now(),
            )
        else:
            # Load existing config
            config_manager = MetagitConfigManager(config_path=config_path)
            config_result = config_manager.load_config()

            if isinstance(config_result, Exception):
                print(f"   ✗ Failed to load config: {config_result}")
                return False

            config = config_result

        # Create record manager with local storage
        storage_dir = Path("./example_records")
        backend = LocalFileStorageBackend(storage_dir)
        logger = UnifiedLogger(LoggerConfig(log_level="INFO", minimal_console=True))
        record_manager = MetagitRecordManager(
            storage_backend=backend,
            metagit_config_manager=(
                config_manager if "config_manager" in locals() else None
            ),
            logger=logger,
        )

        # Create record from config
        record = record_manager.create_record_from_config(
            config=config, detection_source="example", detection_version="1.0.0"
        )

        if isinstance(record, Exception):
            print(f"   ✗ Failed to create record: {record}")
            return False

        print("   ✓ Record created successfully")
        print(f"   - Name: {record.name}")
        print(f"   - Description: {record.description}")
        print(f"   - Detection timestamp: {record.detection_timestamp}")
        print(f"   - Detection source: {record.detection_source}")

        # Store the record (this is where datetime serialization happens)
        record_id = await record_manager.store_record(record)

        if isinstance(record_id, Exception):
            print(f"   ✗ Failed to store record: {record_id}")
            return False

        print(f"   ✓ Record stored successfully with ID: {record_id}")

        # Verify the stored record can be retrieved
        retrieved_record = await record_manager.get_record(record_id)

        if isinstance(retrieved_record, Exception):
            print(f"   ✗ Failed to retrieve record: {retrieved_record}")
            return False

        print("   ✓ Record retrieved successfully")
        print(f"   - Retrieved name: {retrieved_record.name}")
        print(f"   - Retrieved timestamp: {retrieved_record.detection_timestamp}")

        # Clean up
        await record_manager.delete_record(record_id)
        print("   ✓ Record cleaned up")

        return True

    except Exception as e:
        print(f"   ✗ Record creation failed: {e}")
        return False


def main():
    """Run the datetime serialization fix demonstration."""
    print("🚀 Metagit Datetime Serialization Fix Example")
    print("=" * 60)

    # Demonstrate the fix
    if not demonstrate_datetime_serialization_fix():
        print("\n❌ Datetime serialization demonstration failed")
        return

    # Demonstrate record creation
    try:
        success = asyncio.run(demonstrate_record_creation())
        if success:
            print("\n🎉 All demonstrations completed successfully!")
            print("\n✅ The datetime serialization fix is working correctly.")
            print("   You can now use 'metagit.cli.main record create' without errors.")
        else:
            print("\n❌ Record creation demonstration failed")
    except Exception as e:
        print(f"\n❌ Demonstration failed with error: {e}")


if __name__ == "__main__":
    main()
