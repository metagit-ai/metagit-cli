#!/usr/bin/env python
"""
Class for managing metagit records.

This package provides a class for managing metagit records with support for
multiple storage backends (OpenSearch and local files) and the ability to
create records from existing metagit configuration data.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from git import Repo

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.record.models import MetagitRecord
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.utils.yaml_class import yaml


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class RecordStorageBackend(ABC):
    """Abstract base class for record storage backends."""

    @abstractmethod
    async def store_record(self, record: MetagitRecord) -> Union[str, Exception]:
        """Store a record and return the record ID."""
        pass

    @abstractmethod
    async def get_record(self, record_id: str) -> Union[MetagitRecord, Exception]:
        """Retrieve a record by ID."""
        pass

    @abstractmethod
    async def update_record(
        self, record_id: str, record: MetagitRecord
    ) -> Union[bool, Exception]:
        """Update an existing record."""
        pass

    @abstractmethod
    async def delete_record(self, record_id: str) -> Union[bool, Exception]:
        """Delete a record by ID."""
        pass

    @abstractmethod
    async def search_records(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        size: int = 20,
    ) -> Union[Dict[str, Any], Exception]:
        """Search records with optional filters."""
        pass

    @abstractmethod
    async def list_records(
        self, page: int = 1, size: int = 20
    ) -> Union[List[MetagitRecord], Exception]:
        """List all records with pagination."""
        pass


class LocalFileStorageBackend(RecordStorageBackend):
    """Local file-based storage backend for records."""

    def __init__(self, storage_dir: Path):
        """
        Initialize local file storage backend.

        Args:
            storage_dir: Directory to store record files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self._ensure_index_exists()

    def _ensure_index_exists(self) -> None:
        """Ensure the index file exists."""
        if not self.index_file.exists():
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump({"records": {}, "next_id": 1}, f)

    def _load_index(self) -> Dict[str, Any]:
        """Load the index file."""
        with open(self.index_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_index(self, index_data: Dict[str, Any]) -> None:
        """Save the index file."""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2)

    def _get_next_id(self) -> str:
        """Get the next available record ID."""
        index_data = self._load_index()
        next_id = index_data["next_id"]
        index_data["next_id"] += 1
        self._save_index(index_data)
        return str(next_id)

    async def store_record(self, record: MetagitRecord) -> Union[str, Exception]:
        """Store a record to local file."""
        try:
            record_id = self._get_next_id()
            record_file = self.storage_dir / f"{record_id}.json"

            # Add metadata
            record_data = record.model_dump(exclude_none=True, exclude_defaults=True)
            record_data["record_id"] = record_id
            record_data["created_at"] = datetime.now().isoformat()
            record_data["updated_at"] = datetime.now().isoformat()

            with open(record_file, "w", encoding="utf-8") as f:
                json.dump(record_data, f, indent=2, cls=DateTimeEncoder)

            # Update index
            index_data = self._load_index()
            index_data["records"][record_id] = {
                "name": record.name,
                "file": str(record_file),
                "created_at": record_data["created_at"],
                "updated_at": record_data["updated_at"],
            }
            self._save_index(index_data)

            return record_id
        except Exception as e:
            return e

    async def get_record(self, record_id: str) -> Union[MetagitRecord, Exception]:
        """Retrieve a record by ID."""
        try:
            record_file = self.storage_dir / f"{record_id}.json"
            if not record_file.exists():
                return FileNotFoundError(f"Record not found: {record_id}")

            with open(record_file, "r", encoding="utf-8") as f:
                record_data = json.load(f)

            # Remove metadata fields before creating record
            record_data.pop("record_id", None)
            record_data.pop("created_at", None)
            record_data.pop("updated_at", None)

            return MetagitRecord(**record_data)
        except Exception as e:
            return e

    async def update_record(
        self, record_id: str, record: MetagitRecord
    ) -> Union[bool, Exception]:
        """Update an existing record."""
        try:
            record_file = self.storage_dir / f"{record_id}.json"
            if not record_file.exists():
                return FileNotFoundError(f"Record not found: {record_id}")

            # Load existing data to preserve metadata
            with open(record_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)

            # Update record data
            record_data = record.model_dump(exclude_none=True, exclude_defaults=True)
            record_data["record_id"] = record_id
            record_data["created_at"] = existing_data.get("created_at")
            record_data["updated_at"] = datetime.now().isoformat()

            with open(record_file, "w", encoding="utf-8") as f:
                json.dump(record_data, f, indent=2, cls=DateTimeEncoder)

            # Update index
            index_data = self._load_index()
            if record_id in index_data["records"]:
                index_data["records"][record_id]["updated_at"] = record_data[
                    "updated_at"
                ]
                self._save_index(index_data)

            return True
        except Exception as e:
            return e

    async def delete_record(self, record_id: str) -> Union[bool, Exception]:
        """Delete a record by ID."""
        try:
            record_file = self.storage_dir / f"{record_id}.json"
            if not record_file.exists():
                return FileNotFoundError(f"Record not found: {record_id}")

            record_file.unlink()

            # Update index
            index_data = self._load_index()
            index_data["records"].pop(record_id, None)
            self._save_index(index_data)

            return True
        except Exception as e:
            return e

    async def search_records(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        size: int = 20,
    ) -> Union[Dict[str, Any], Exception]:
        """Search records with optional filters."""
        try:
            all_records = await self.list_records(
                page=1, size=1000
            )  # Get all for search
            if isinstance(all_records, Exception):
                return all_records

            # Simple text search
            filtered_records = []
            for record in all_records:
                if query.lower() in record.name.lower() or (
                    record.description and query.lower() in record.description.lower()
                ):
                    filtered_records.append(record)

            # Apply additional filters
            if filters:
                filtered_records = [
                    record
                    for record in filtered_records
                    if all(
                        getattr(record, key, None) == value
                        for key, value in filters.items()
                    )
                ]

            # Pagination
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_records = filtered_records[start_idx:end_idx]

            return {
                "records": paginated_records,
                "total": len(filtered_records),
                "page": page,
                "size": size,
                "pages": (len(filtered_records) + size - 1) // size,
            }
        except Exception as e:
            return e

    async def list_records(
        self, page: int = 1, size: int = 20
    ) -> Union[List[MetagitRecord], Exception]:
        """List all records with pagination."""
        try:
            index_data = self._load_index()
            record_ids = list(index_data["records"].keys())

            # Pagination
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paginated_ids = record_ids[start_idx:end_idx]

            records = []
            for record_id in paginated_ids:
                record_result = await self.get_record(record_id)
                if isinstance(record_result, Exception):
                    continue  # Skip failed records
                records.append(record_result)

            return records
        except Exception as e:
            return e


class OpenSearchStorageBackend(RecordStorageBackend):
    """OpenSearch-based storage backend for records."""

    def __init__(self, opensearch_service):
        """
        Initialize OpenSearch storage backend.

        Args:
            opensearch_service: Configured OpenSearchService instance
        """
        self.opensearch_service = opensearch_service

    async def store_record(self, record: MetagitRecord) -> Union[str, Exception]:
        """Store a record to OpenSearch."""
        return await self.opensearch_service.store_record(record)

    async def get_record(self, record_id: str) -> Union[MetagitRecord, Exception]:
        """Retrieve a record by ID."""
        return await self.opensearch_service.get_record(record_id)

    async def update_record(
        self, record_id: str, record: MetagitRecord
    ) -> Union[bool, Exception]:
        """Update an existing record."""
        return await self.opensearch_service.update_record(record_id, record)

    async def delete_record(self, record_id: str) -> Union[bool, Exception]:
        """Delete a record by ID."""
        return await self.opensearch_service.delete_record(record_id)

    async def search_records(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        size: int = 20,
    ) -> Union[Dict[str, Any], Exception]:
        """Search records with optional filters."""
        return await self.opensearch_service.search_records(
            query=query,
            filters=filters,
            page=page,
            size=size,
        )

    async def list_records(
        self, page: int = 1, size: int = 20
    ) -> Union[List[MetagitRecord], Exception]:
        """List all records with pagination."""
        try:
            search_result = await self.opensearch_service.search_records(
                query="*", page=page, size=size
            )
            if isinstance(search_result, Exception):
                return search_result

            return search_result.get("records", [])
        except Exception as e:
            return e


class MetagitRecordManager:
    """
    Manager class for handling metagit records.

    This class provides methods for loading, validating, and creating
    metagit records with proper error handling and validation.
    Supports multiple storage backends (OpenSearch and local files).
    """

    def __init__(
        self,
        storage_backend: Optional[RecordStorageBackend] = None,
        metagit_config_manager: Optional[MetagitConfigManager] = None,
        logger: Optional[UnifiedLogger] = None,
    ):
        """
        Initialize the MetagitRecordManager.

        Args:
            storage_backend: Storage backend for records (OpenSearch or local file)
            metagit_config_manager: Optional MetagitConfigManager instance
            logger: Optional logger instance
        """
        self.storage_backend = storage_backend
        self.config_manager: MetagitConfigManager = metagit_config_manager
        self.logger = logger or UnifiedLogger(
            LoggerConfig(log_level="INFO", minimal_console=True)
        )
        self.record: Optional[MetagitRecord] = None

    def create_record_from_config(
        self,
        config: Optional[MetagitConfig] = None,
        detection_source: str = "local",
        detection_version: str = "1.0.0",
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Union[MetagitRecord, Exception]:
        """
        Create a MetagitRecord from existing MetagitConfig data.

        Args:
            config: MetagitConfig to convert. If None, uses config from config_manager.
            detection_source: Source of the detection (e.g., 'github', 'gitlab', 'local')
            detection_version: Version of the detection system used
            additional_data: Additional data to include in the record

        Returns:
            MetagitRecord: The created record
        """
        try:
            # Get config from parameter or config manager
            if config is None:
                if self.config_manager is None:
                    return ValueError(
                        "No config provided and no config_manager available"
                    )

                config_result = self.config_manager.load_config()
                if isinstance(config_result, Exception):
                    return config_result
                config = config_result

            # Get current git information
            git_info = self._get_git_info()

            # Create record data
            record_data = config.model_dump(exclude_none=True, exclude_defaults=True)

            # Add detection-specific fields
            record_data.update(
                {
                    "detection_timestamp": datetime.now(),
                    "detection_source": detection_source,
                    "detection_version": detection_version,
                    "branch": git_info.get("branch"),
                    "checksum": git_info.get("checksum"),
                    "last_updated": datetime.now(),
                }
            )

            # Add additional data if provided
            if additional_data:
                record_data.update(additional_data)

            # Create and validate record
            record = MetagitRecord(**record_data)
            return record

        except Exception as e:
            return e

    def _get_git_info(self) -> Dict[str, Optional[str]]:
        """Get current git repository information."""
        try:
            repo = Repo(Path.cwd())
            return {
                "branch": repo.active_branch.name if repo.head.is_valid() else None,
                "checksum": repo.head.commit.hexsha if repo.head.is_valid() else None,
            }
        except Exception:
            return {
                "branch": None,
                "checksum": None,
            }

    async def store_record(self, record: MetagitRecord) -> Union[str, Exception]:
        """
        Store a record using the configured storage backend.

        Args:
            record: MetagitRecord to store

        Returns:
            str: Record ID if successful, Exception otherwise
        """
        if self.storage_backend is None:
            return ValueError("No storage backend configured")

        return await self.storage_backend.store_record(record)

    async def get_record(self, record_id: str) -> Union[MetagitRecord, Exception]:
        """
        Retrieve a record by ID.

        Args:
            record_id: ID of the record to retrieve

        Returns:
            MetagitRecord: The retrieved record, or Exception if failed
        """
        if self.storage_backend is None:
            return ValueError("No storage backend configured")

        return await self.storage_backend.get_record(record_id)

    async def update_record(
        self, record_id: str, record: MetagitRecord
    ) -> Union[bool, Exception]:
        """
        Update an existing record.

        Args:
            record_id: ID of the record to update
            record: Updated MetagitRecord

        Returns:
            bool: True if successful, Exception otherwise
        """
        if self.storage_backend is None:
            return ValueError("No storage backend configured")

        return await self.storage_backend.update_record(record_id, record)

    async def delete_record(self, record_id: str) -> Union[bool, Exception]:
        """
        Delete a record by ID.

        Args:
            record_id: ID of the record to delete

        Returns:
            bool: True if successful, Exception otherwise
        """
        if self.storage_backend is None:
            return ValueError("No storage backend configured")

        return await self.storage_backend.delete_record(record_id)

    async def search_records(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        size: int = 20,
    ) -> Union[Dict[str, Any], Exception]:
        """
        Search records with optional filters.

        Args:
            query: Search query string
            filters: Optional filters to apply
            page: Page number for pagination
            size: Number of records per page

        Returns:
            Dict: Search results with pagination info
        """
        if self.storage_backend is None:
            return ValueError("No storage backend configured")

        return await self.storage_backend.search_records(
            query=query, filters=filters, page=page, size=size
        )

    async def list_records(
        self, page: int = 1, size: int = 20
    ) -> Union[List[MetagitRecord], Exception]:
        """
        List all records with pagination.

        Args:
            page: Page number for pagination
            size: Number of records per page

        Returns:
            List[MetagitRecord]: List of records
        """
        if self.storage_backend is None:
            return ValueError("No storage backend configured")

        return await self.storage_backend.list_records(page=page, size=size)

    def save_record_to_file(
        self, record: MetagitRecord, file_path: Path
    ) -> Union[None, Exception]:
        """
        Save a record to a local YAML file.

        Args:
            record: MetagitRecord to save
            file_path: Path where to save the record

        Returns:
            None if successful, Exception otherwise
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    record.model_dump(exclude_none=True, exclude_defaults=True),
                    f,
                    default_flow_style=False,
                )
            return None
        except Exception as e:
            return e

    def load_record_from_file(self, file_path: Path) -> Union[MetagitRecord, Exception]:
        """
        Load a record from a local YAML file.

        Args:
            file_path: Path to the record file

        Returns:
            MetagitRecord: The loaded record, or Exception if failed
        """
        try:
            if not file_path.exists():
                return FileNotFoundError(f"Record file not found: {file_path}")

            with open(file_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            return MetagitRecord(**yaml_data)
        except Exception as e:
            return e
