#!/usr/bin/env python
"""
Tests for the updated MetagitRecordManager.

This module tests the new functionality including:
- Storage backend abstraction
- Local file storage backend
- OpenSearch storage backend
- Record creation from config
- File operations
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.record.manager import (
    LocalFileStorageBackend,
    MetagitRecordManager,
    OpenSearchStorageBackend,
    RecordStorageBackend,
)
from metagit.core.record.models import MetagitRecord


class TestRecordStorageBackend:
    """Test the abstract RecordStorageBackend class."""

    def test_abstract_methods(self):
        """Test that RecordStorageBackend is abstract."""
        with pytest.raises(TypeError):
            RecordStorageBackend()


class TestLocalFileStorageBackend:
    """Test the LocalFileStorageBackend class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def backend(self, temp_dir):
        """Create a LocalFileStorageBackend instance."""
        return LocalFileStorageBackend(temp_dir)

    @pytest.fixture
    def sample_record(self):
        """Create a sample MetagitRecord for testing."""
        return MetagitRecord(
            name="test-project",
            description="A test project",
            url="https://github.com/test/test-project",
            kind="application",
            detection_timestamp="2024-01-01T00:00:00",
            detection_source="test",
            detection_version="1.0.0",
        )

    def test_init_creates_directory(self, temp_dir):
        """Test that initialization creates the storage directory."""
        backend = LocalFileStorageBackend(temp_dir)
        assert temp_dir.exists()
        assert (temp_dir / "index.json").exists()

    def test_ensure_index_exists(self, backend):
        """Test that index file is created if it doesn't exist."""
        index_file = backend.storage_dir / "index.json"
        assert index_file.exists()

        with open(index_file, "r") as f:
            index_data = json.load(f)

        assert "records" in index_data
        assert "next_id" in index_data
        assert index_data["next_id"] == 1

    def test_get_next_id(self, backend):
        """Test getting the next available ID."""
        first_id = backend._get_next_id()
        assert first_id == "1"

        second_id = backend._get_next_id()
        assert second_id == "2"

    @pytest.mark.asyncio
    async def test_store_record(self, backend, sample_record):
        """Test storing a record."""
        record_id = await backend.store_record(sample_record)

        assert isinstance(record_id, str)
        assert record_id == "1"

        # Check that record file was created
        record_file = backend.storage_dir / f"{record_id}.json"
        assert record_file.exists()

        # Check index was updated
        index_data = backend._load_index()
        assert record_id in index_data["records"]
        assert index_data["records"][record_id]["name"] == sample_record.name

    @pytest.mark.asyncio
    async def test_get_record(self, backend, sample_record):
        """Test retrieving a record."""
        # Store a record first
        record_id = await backend.store_record(sample_record)

        # Retrieve the record
        retrieved_record = await backend.get_record(record_id)

        assert isinstance(retrieved_record, MetagitRecord)
        assert retrieved_record.name == sample_record.name
        assert retrieved_record.description == sample_record.description

    @pytest.mark.asyncio
    async def test_get_record_not_found(self, backend):
        """Test retrieving a non-existent record."""
        result = await backend.get_record("nonexistent")
        assert isinstance(result, FileNotFoundError)

    @pytest.mark.asyncio
    async def test_update_record(self, backend, sample_record):
        """Test updating a record."""
        # Store a record first
        record_id = await backend.store_record(sample_record)

        # Update the record
        updated_record = MetagitRecord(
            name="updated-project",
            description="An updated test project",
            url="https://github.com/test/updated-project",
            kind="library",
            detection_timestamp="2024-01-01T00:00:00",
            detection_source="test",
            detection_version="1.0.0",
        )

        result = await backend.update_record(record_id, updated_record)
        assert result is True

        # Verify the record was updated
        retrieved_record = await backend.get_record(record_id)
        assert retrieved_record.name == "updated-project"
        assert retrieved_record.description == "An updated test project"

    @pytest.mark.asyncio
    async def test_delete_record(self, backend, sample_record):
        """Test deleting a record."""
        # Store a record first
        record_id = await backend.store_record(sample_record)

        # Delete the record
        result = await backend.delete_record(record_id)
        assert result is True

        # Verify the record was deleted
        get_result = await backend.get_record(record_id)
        assert isinstance(get_result, FileNotFoundError)

    @pytest.mark.asyncio
    async def test_search_records(self, backend, sample_record):
        """Test searching records."""
        # Store a record first
        await backend.store_record(sample_record)

        # Search for the record
        search_results = await backend.search_records("test")

        assert isinstance(search_results, dict)
        assert "records" in search_results
        assert len(search_results["records"]) == 1
        assert search_results["records"][0].name == sample_record.name

    @pytest.mark.asyncio
    async def test_list_records(self, backend, sample_record):
        """Test listing records."""
        # Store a record first
        await backend.store_record(sample_record)

        # List all records
        records = await backend.list_records()

        assert isinstance(records, list)
        assert len(records) == 1
        assert records[0].name == sample_record.name


class TestOpenSearchStorageBackend:
    """Test the OpenSearchStorageBackend class."""

    @pytest.fixture
    def mock_opensearch_service(self):
        """Create a mock OpenSearchService."""
        service = MagicMock()
        service.store_record = AsyncMock(return_value="test-id")
        service.get_record = AsyncMock(
            return_value=MetagitRecord(
                name="test-project",
                description="A test project",
                detection_timestamp="2024-01-01T00:00:00",
                detection_source="test",
                detection_version="1.0.0",
            )
        )
        service.update_record = AsyncMock(return_value=True)
        service.delete_record = AsyncMock(return_value=True)
        service.search_records = AsyncMock(
            return_value={
                "records": [],
                "total": 0,
                "page": 1,
                "size": 20,
            }
        )
        return service

    @pytest.fixture
    def backend(self, mock_opensearch_service):
        """Create an OpenSearchStorageBackend instance."""
        return OpenSearchStorageBackend(mock_opensearch_service)

    @pytest.fixture
    def sample_record(self):
        """Create a sample MetagitRecord for testing."""
        return MetagitRecord(
            name="test-project",
            description="A test project",
            detection_timestamp="2024-01-01T00:00:00",
            detection_source="test",
            detection_version="1.0.0",
        )

    @pytest.mark.asyncio
    async def test_store_record(self, backend, sample_record):
        """Test storing a record."""
        record_id = await backend.store_record(sample_record)
        assert record_id == "test-id"
        backend.opensearch_service.store_record.assert_called_once_with(sample_record)

    @pytest.mark.asyncio
    async def test_get_record(self, backend):
        """Test retrieving a record."""
        record = await backend.get_record("test-id")
        assert isinstance(record, MetagitRecord)
        assert record.name == "test-project"
        backend.opensearch_service.get_record.assert_called_once_with("test-id")

    @pytest.mark.asyncio
    async def test_update_record(self, backend, sample_record):
        """Test updating a record."""
        result = await backend.update_record("test-id", sample_record)
        assert result is True
        backend.opensearch_service.update_record.assert_called_once_with(
            "test-id", sample_record
        )

    @pytest.mark.asyncio
    async def test_delete_record(self, backend):
        """Test deleting a record."""
        result = await backend.delete_record("test-id")
        assert result is True
        backend.opensearch_service.delete_record.assert_called_once_with("test-id")

    @pytest.mark.asyncio
    async def test_search_records(self, backend):
        """Test searching records."""
        results = await backend.search_records("test")
        assert isinstance(results, dict)
        assert "records" in results
        backend.opensearch_service.search_records.assert_called_once_with(
            query="test", filters=None, page=1, size=20
        )

    @pytest.mark.asyncio
    async def test_list_records(self, backend):
        """Test listing records."""
        records = await backend.list_records()
        assert isinstance(records, list)
        backend.opensearch_service.search_records.assert_called_once_with(
            query="*", page=1, size=20
        )


class TestMetagitRecordManager:
    """Test the MetagitRecordManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def local_backend(self, temp_dir):
        """Create a LocalFileStorageBackend instance."""
        return LocalFileStorageBackend(temp_dir)

    @pytest.fixture
    def record_manager(self, local_backend):
        """Create a MetagitRecordManager instance."""
        return MetagitRecordManager(storage_backend=local_backend)

    @pytest.fixture
    def sample_config(self):
        """Create a sample MetagitConfig for testing."""
        return MetagitConfig(
            name="test-project",
            description="A test project",
            url="https://github.com/test/test-project",
            kind="application",
        )

    def test_init_without_backend(self):
        """Test initialization without storage backend."""
        manager = MetagitRecordManager()
        assert manager.storage_backend is None
        assert manager.config_manager is None
        assert manager.record is None

    def test_init_with_backend(self, local_backend):
        """Test initialization with storage backend."""
        manager = MetagitRecordManager(storage_backend=local_backend)
        assert manager.storage_backend == local_backend

    def test_init_with_config_manager(self, local_backend):
        """Test initialization with config manager."""
        config_manager = MetagitConfigManager()
        manager = MetagitRecordManager(
            storage_backend=local_backend,
            metagit_config_manager=config_manager,
        )
        assert manager.config_manager == config_manager

    def test_create_record_from_config(self, record_manager, sample_config):
        """Test creating a record from config."""
        record = record_manager.create_record_from_config(
            config=sample_config,
            detection_source="test",
            detection_version="1.0.0",
        )

        assert isinstance(record, MetagitRecord)
        assert record.name == sample_config.name
        assert record.description == sample_config.description
        assert record.detection_source == "test"
        assert record.detection_version == "1.0.0"
        assert record.detection_timestamp is not None

    def test_create_record_from_config_manager(self, local_backend):
        """Test creating a record using config manager."""
        config_manager = MetagitConfigManager()
        manager = MetagitRecordManager(
            storage_backend=local_backend,
            metagit_config_manager=config_manager,
        )

        # This should fail because no config file exists
        result = manager.create_record_from_config()
        assert isinstance(result, Exception)

    def test_create_record_with_additional_data(self, record_manager, sample_config):
        """Test creating a record with additional data."""
        additional_data = {
            "language": {"primary": "python", "secondary": ["javascript"]},
            "domain": "web",
        }

        record = record_manager.create_record_from_config(
            config=sample_config,
            detection_source="test",
            detection_version="1.0.0",
            additional_data=additional_data,
        )

        assert isinstance(record, MetagitRecord)
        assert record.language.primary == "python"
        assert record.domain == "web"

    def test_get_git_info(self, record_manager):
        """Test getting git information."""
        git_info = record_manager._get_git_info()
        assert isinstance(git_info, dict)
        assert "branch" in git_info
        assert "checksum" in git_info

    @pytest.mark.asyncio
    async def test_store_record_with_backend(self, record_manager, sample_config):
        """Test storing a record with storage backend."""
        record = record_manager.create_record_from_config(
            config=sample_config,
            detection_source="test",
            detection_version="1.0.0",
        )

        record_id = await record_manager.store_record(record)
        assert isinstance(record_id, str)

    @pytest.mark.asyncio
    async def test_store_record_without_backend(self):
        """Test storing a record without storage backend."""
        manager = MetagitRecordManager()
        record = MetagitRecord(
            name="test-project",
            description="A test project",
            detection_timestamp="2024-01-01T00:00:00",
            detection_source="test",
            detection_version="1.0.0",
        )

        result = await manager.store_record(record)
        assert isinstance(result, ValueError)

    @pytest.mark.asyncio
    async def test_get_record_with_backend(self, record_manager, sample_config):
        """Test getting a record with storage backend."""
        record = record_manager.create_record_from_config(
            config=sample_config,
            detection_source="test",
            detection_version="1.0.0",
        )

        record_id = await record_manager.store_record(record)
        retrieved_record = await record_manager.get_record(record_id)

        assert isinstance(retrieved_record, MetagitRecord)
        assert retrieved_record.name == sample_config.name

    @pytest.mark.asyncio
    async def test_get_record_without_backend(self):
        """Test getting a record without storage backend."""
        manager = MetagitRecordManager()
        result = await manager.get_record("test-id")
        assert isinstance(result, ValueError)

    def test_save_record_to_file(self, record_manager, sample_config, temp_dir):
        """Test saving a record to file."""
        record = record_manager.create_record_from_config(
            config=sample_config,
            detection_source="test",
            detection_version="1.0.0",
        )

        file_path = temp_dir / "test-record.yml"
        result = record_manager.save_record_to_file(record, file_path)

        assert result is None
        assert file_path.exists()

    def test_load_record_from_file(self, record_manager, sample_config, temp_dir):
        """Test loading a record from file."""
        record = record_manager.create_record_from_config(
            config=sample_config,
            detection_source="test",
            detection_version="1.0.0",
        )

        file_path = temp_dir / "test-record.yml"
        record_manager.save_record_to_file(record, file_path)

        loaded_record = record_manager.load_record_from_file(file_path)
        assert isinstance(loaded_record, MetagitRecord)
        assert loaded_record.name == sample_config.name

    def test_load_record_from_nonexistent_file(self, record_manager):
        """Test loading a record from a non-existent file."""
        result = record_manager.load_record_from_file(Path("nonexistent.yml"))
        assert isinstance(result, FileNotFoundError)


if __name__ == "__main__":
    pytest.main([__file__])
