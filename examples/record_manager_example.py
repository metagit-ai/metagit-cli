#!/usr/bin/env python
"""
Example script demonstrating the updated MetagitRecordManager.

This script shows how to:
1. Create records from existing metagit config data
2. Store records using local file storage backend
3. Store records using OpenSearch storage backend
4. Search and retrieve records
"""

import asyncio
from pathlib import Path

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.record.manager import (
    LocalFileStorageBackend,
    MetagitRecordManager,
    OpenSearchStorageBackend,
)
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger


async def example_local_file_storage():
    """Example using local file storage backend."""
    print("=== Local File Storage Example ===")

    # Initialize logger
    logger = UnifiedLogger(LoggerConfig(log_level="INFO", minimal_console=True))

    # Create local file storage backend
    storage_dir = Path("./records")
    local_backend = LocalFileStorageBackend(storage_dir)

    # Initialize record manager with local backend
    record_manager = MetagitRecordManager(
        storage_backend=local_backend,
        logger=logger,
    )

    # Create a sample config manager
    config_manager = MetagitConfigManager()

    # Create a sample config
    sample_config = config_manager.create_config(
        name="example-project",
        description="An example project for testing",
        url="https://github.com/example/example-project",
        kind="application",
    )

    if isinstance(sample_config, Exception):
        print(f"Error creating config: {sample_config}")
        return

    # Create record from config
    record = record_manager.create_record_from_config(
        config=sample_config,
        detection_source="local",
        detection_version="1.0.0",
        additional_data={
            "language": {"primary": "python", "secondary": ["javascript"]},
            "domain": "web",
        },
    )

    if isinstance(record, Exception):
        print(f"Error creating record: {record}")
        return

    print(f"Created record: {record.name}")

    # Store the record
    record_id = await record_manager.store_record(record)
    if isinstance(record_id, Exception):
        print(f"Error storing record: {record_id}")
        return

    print(f"Stored record with ID: {record_id}")

    # Retrieve the record
    retrieved_record = await record_manager.get_record(record_id)
    if isinstance(retrieved_record, Exception):
        print(f"Error retrieving record: {retrieved_record}")
        return

    print(f"Retrieved record: {retrieved_record.name}")

    # Search records
    search_results = await record_manager.search_records("example")
    if isinstance(search_results, Exception):
        print(f"Error searching records: {search_results}")
        return

    print(f"Search results: {len(search_results['records'])} records found")

    # List all records
    all_records = await record_manager.list_records()
    if isinstance(all_records, Exception):
        print(f"Error listing records: {all_records}")
        return

    print(f"Total records: {len(all_records)}")


async def example_opensearch_storage():
    """Example using OpenSearch storage backend."""
    print("\n=== OpenSearch Storage Example ===")

    # Note: This example requires a running OpenSearch instance
    # You would need to configure the OpenSearchService first

    try:
        # Import OpenSearchService (this would fail if opensearchpy is not installed)
        from metagit.api.opensearch import OpenSearchService

        # Initialize OpenSearch service
        opensearch_service = OpenSearchService(
            hosts=[{"host": "localhost", "port": 9200}],
            index_name="metagit-records-example",
            use_ssl=False,
            verify_certs=False,
        )

        # Create OpenSearch storage backend
        opensearch_backend = OpenSearchStorageBackend(opensearch_service)

        # Initialize record manager with OpenSearch backend
        record_manager = MetagitRecordManager(
            storage_backend=opensearch_backend,
        )

        # Create a sample config
        config_manager = MetagitConfigManager()
        sample_config = config_manager.create_config(
            name="opensearch-example",
            description="Example project for OpenSearch testing",
            url="https://github.com/example/opensearch-example",
            kind="library",
        )

        if isinstance(sample_config, Exception):
            print(f"Error creating config: {sample_config}")
            return

        # Create record from config
        record = record_manager.create_record_from_config(
            config=sample_config,
            detection_source="github",
            detection_version="1.0.0",
        )

        if isinstance(record, Exception):
            print(f"Error creating record: {record}")
            return

        print(f"Created record: {record.name}")

        # Store the record
        record_id = await record_manager.store_record(record)
        if isinstance(record_id, Exception):
            print(f"Error storing record: {record_id}")
            return

        print(f"Stored record with ID: {record_id}")

        # Search records
        search_results = await record_manager.search_records("opensearch")
        if isinstance(search_results, Exception):
            print(f"Error searching records: {search_results}")
            return

        print(f"Search results: {len(search_results['records'])} records found")

    except ImportError:
        print("OpenSearch example skipped - opensearchpy not available")
    except Exception as e:
        print(f"OpenSearch example failed: {e}")


def example_file_operations():
    """Example of direct file operations."""
    print("\n=== File Operations Example ===")

    # Initialize record manager without storage backend
    record_manager = MetagitRecordManager()

    # Create a sample config
    config_manager = MetagitConfigManager()
    sample_config = config_manager.create_config(
        name="file-example",
        description="Example project for file operations",
        url="https://github.com/example/file-example",
        kind="cli",
    )

    if isinstance(sample_config, Exception):
        print(f"Error creating config: {sample_config}")
        return

    # Create record from config
    record = record_manager.create_record_from_config(
        config=sample_config,
        detection_source="local",
        detection_version="1.0.0",
    )

    if isinstance(record, Exception):
        print(f"Error creating record: {record}")
        return

    print(f"Created record: {record.name}")

    # Save record to file
    file_path = Path("./example-record.yml")
    save_result = record_manager.save_record_to_file(record, file_path)
    if isinstance(save_result, Exception):
        print(f"Error saving record: {save_result}")
        return

    print(f"Saved record to: {file_path}")

    # Load record from file
    loaded_record = record_manager.load_record_from_file(file_path)
    if isinstance(loaded_record, Exception):
        print(f"Error loading record: {loaded_record}")
        return

    print(f"Loaded record: {loaded_record.name}")

    # Clean up
    file_path.unlink(missing_ok=True)
    print("Cleaned up example file")


async def main():
    """Run all examples."""
    print("MetagitRecordManager Examples")
    print("=" * 50)

    # Run local file storage example
    await example_local_file_storage()

    # Run OpenSearch storage example
    await example_opensearch_storage()

    # Run file operations example
    example_file_operations()

    print("\nExamples completed!")


if __name__ == "__main__":
    asyncio.run(main())
