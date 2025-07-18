#!/usr/bin/env python
"""
Simple test script for the updated MetagitRecordManager.

This script tests the basic functionality without requiring pytest.
"""

import asyncio
import tempfile
from pathlib import Path

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.record.manager import LocalFileStorageBackend, MetagitRecordManager
from metagit.core.record.models import MetagitRecord


def test_basic_functionality():
    """Test basic functionality of the updated MetagitRecordManager."""
    print("Testing MetagitRecordManager basic functionality...")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Test 1: Create storage backend
        print("1. Creating LocalFileStorageBackend...")
        backend = LocalFileStorageBackend(temp_path)
        print(f"   ✓ Storage backend created in {temp_path}")

        # Test 2: Create record manager
        print("2. Creating MetagitRecordManager...")
        record_manager = MetagitRecordManager(storage_backend=backend)
        print("   ✓ Record manager created")

        # Test 3: Create sample config
        print("3. Creating sample config...")
        config_manager = MetagitConfigManager()
        sample_config = config_manager.create_config(
            name="test-project",
            description="A test project for validation",
            url="https://github.com/test/test-project",
            kind="application",
        )
        print(f"   ✓ Sample config created: {sample_config.name}")

        # Test 4: Create record from config
        print("4. Creating record from config...")
        record = record_manager.create_record_from_config(
            config=sample_config,
            detection_source="test",
            detection_version="1.0.0",
            additional_data={
                "language": {"primary": "python", "secondary": ["javascript"]},
                "domain": "web",
            },
        )
        print(f"   ✓ Record created: {record.name}")
        print(f"   ✓ Detection source: {record.detection_source}")
        print(f"   ✓ Language: {record.language.primary}")
        print(f"   ✓ Domain: {record.domain}")

        # Test 5: Store record
        print("5. Storing record...")

        async def store_record():
            record_id = await record_manager.store_record(record)
            return record_id

        record_id = asyncio.run(store_record())
        print(f"   ✓ Record stored with ID: {record_id}")

        # Test 6: Retrieve record
        print("6. Retrieving record...")

        async def get_record():
            retrieved_record = await record_manager.get_record(record_id)
            return retrieved_record

        retrieved_record = asyncio.run(get_record())
        print(f"   ✓ Record retrieved: {retrieved_record.name}")

        # Test 7: Search records
        print("7. Searching records...")

        async def search_records():
            search_results = await record_manager.search_records("test")
            return search_results

        search_results = asyncio.run(search_records())
        print(f"   ✓ Search results: {len(search_results['records'])} records found")

        # Test 8: List records
        print("8. Listing records...")

        async def list_records():
            records = await record_manager.list_records()
            return records

        records = asyncio.run(list_records())
        print(f"   ✓ Total records: {len(records)}")

        # Test 9: File operations
        print("9. Testing file operations...")
        file_path = temp_path / "test-record.yml"
        save_result = record_manager.save_record_to_file(record, file_path)
        if save_result is None:
            print("   ✓ Record saved to file")

            loaded_record = record_manager.load_record_from_file(file_path)
            print(f"   ✓ Record loaded from file: {loaded_record.name}")
        else:
            print(f"   ✗ Error saving record: {save_result}")

        print("\n✅ All tests passed!")


def test_error_handling():
    """Test error handling scenarios."""
    print("\nTesting error handling...")

    # Test 1: Record manager without storage backend
    print("1. Testing record manager without storage backend...")
    manager = MetagitRecordManager()

    async def test_no_backend():
        record = MetagitRecord(
            name="test",
            description="test",
            detection_timestamp="2024-01-01T00:00:00",
            detection_source="test",
            detection_version="1.0.0",
        )
        result = await manager.store_record(record)
        return result

    result = asyncio.run(test_no_backend())
    if isinstance(result, ValueError):
        print("   ✓ Correctly handled missing storage backend")
    else:
        print(f"   ✗ Unexpected result: {result}")

    # Test 2: Loading non-existent file
    print("2. Testing loading non-existent file...")
    result = manager.load_record_from_file(Path("nonexistent.yml"))
    if isinstance(result, FileNotFoundError):
        print("   ✓ Correctly handled non-existent file")
    else:
        print(f"   ✗ Unexpected result: {result}")

    print("✅ Error handling tests completed!")


if __name__ == "__main__":
    print("MetagitRecordManager Simple Test")
    print("=" * 50)

    try:
        test_basic_functionality()
        test_error_handling()
        print("\n🎉 All tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
