#!/usr/bin/env python
"""
OpenSearch service for storing and retrieving MetagitRecord entries.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from opensearchpy import OpenSearch, helpers

from metagit.core.record.models import MetagitRecord
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)


class OpenSearchService:
    """Service for interacting with OpenSearch for MetagitRecord storage."""

    def __init__(
        self,
        hosts: List[Dict[str, Any]],
        index_name: str = "metagit-records",
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = False,
        verify_certs: bool = False,
        ssl_show_warn: bool = False,
    ):
        """
        Initialize OpenSearch service.

        Args:
            hosts: List of OpenSearch hosts
            index_name: Name of the index for MetagitRecord entries
            username: OpenSearch username
            password: OpenSearch password
            use_ssl: Whether to use SSL
            verify_certs: Whether to verify SSL certificates
            ssl_show_warn: Whether to show SSL warnings
        """
        self.index_name = index_name
        self.client = OpenSearch(
            hosts=hosts,
            http_auth=(username, password) if username and password else None,
            use_ssl=use_ssl,
            verify_certs=verify_certs,
            ssl_show_warn=ssl_show_warn,
        )

        # Initialize index if it doesn't exist
        self._ensure_index_exists()

    def _ensure_index_exists(self) -> None:
        """Ensure the index exists with proper mapping."""
        if not self.client.indices.exists(index=self.index_name):
            logger.info(f"Creating index: {self.index_name}")

            # Define mapping for MetagitRecord
            mapping = {
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "name": {"type": "text", "analyzer": "standard"},
                        "description": {"type": "text", "analyzer": "standard"},
                        "url": {"type": "keyword"},
                        "kind": {"type": "keyword"},
                        "branch_strategy": {"type": "keyword"},
                        "detection_timestamp": {"type": "date"},
                        "detection_source": {"type": "keyword"},
                        "detection_version": {"type": "keyword"},
                        "branches": {
                            "type": "nested",
                            "properties": {
                                "name": {"type": "keyword"},
                                "environment": {"type": "keyword"},
                            },
                        },
                        "metrics": {
                            "type": "object",
                            "properties": {
                                "stars": {"type": "integer"},
                                "forks": {"type": "integer"},
                                "open_issues": {"type": "integer"},
                                "contributors": {"type": "integer"},
                                "commit_frequency": {"type": "keyword"},
                            },
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "tags": {"type": "keyword"},
                                "license": {"type": "keyword"},
                                "has_ci": {"type": "boolean"},
                                "has_tests": {"type": "boolean"},
                                "has_docs": {"type": "boolean"},
                                "has_docker": {"type": "boolean"},
                                "has_iac": {"type": "boolean"},
                            },
                        },
                        "language_detection": {
                            "type": "object",
                            "properties": {
                                "primary": {"type": "keyword"},
                                "secondary": {"type": "keyword"},
                                "frameworks": {"type": "keyword"},
                                "package_managers": {"type": "keyword"},
                            },
                        },
                        "project_type_detection": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "keyword"},
                                "domain": {"type": "keyword"},
                                "confidence": {"type": "float"},
                            },
                        },
                    }
                },
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1,
                    "index": {"max_result_window": 10000},
                },
            }

            self.client.indices.create(index=self.index_name, body=mapping)
            logger.info(f"Index {self.index_name} created successfully")
        else:
            # Check if existing index has compatible mapping
            if not self._check_mapping_compatibility():
                logger.warning(
                    f"Index {self.index_name} has incompatible mapping, recreating..."
                )
                if not self._recreate_index():
                    logger.error(f"Failed to recreate index {self.index_name}")
                    raise RuntimeError(
                        f"Index {self.index_name} has incompatible mapping and recreation failed"
                    )

    def _check_mapping_compatibility(self) -> bool:
        """
        Check if the current index mapping is compatible with our expected schema.

        Returns:
            True if compatible, False if needs recreation
        """
        try:
            if not self.client.indices.exists(index=self.index_name):
                return False

            mapping = self.client.indices.get_mapping(index=self.index_name)
            properties = mapping[self.index_name]["mappings"]["properties"]

            # Check if @timestamp field exists and is of type date
            if "@timestamp" not in properties:
                logger.warning("Index missing @timestamp field in mapping")
                return False

            if properties["@timestamp"]["type"] != "date":
                logger.warning("Index @timestamp field is not of type date")
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking mapping compatibility: {e}")
            return False

    def _recreate_index(self) -> bool:
        """
        Recreate the index with the correct mapping.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Recreating index {self.index_name} with correct mapping")

            # Delete existing index if it exists
            if self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
                logger.info(f"Deleted existing index {self.index_name}")

            # Create new index with correct mapping
            self._ensure_index_exists()
            logger.info(f"Successfully recreated index {self.index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to recreate index: {e}")
            return False

    async def store_record(self, record: MetagitRecord) -> Union[str, Exception]:
        """
        Store a MetagitRecord in OpenSearch.

        Args:
            record: MetagitRecord to store

        Returns:
            Document ID or Exception
        """
        try:
            # Convert record to dict
            record_dict = record.model_dump(exclude_none=True, exclude_unset=True)

            # Normalize URL if present
            if "url" in record_dict:
                record_dict["url"] = normalize_git_url(record_dict["url"])

            # Add timestamp for indexing
            record_dict["@timestamp"] = datetime.utcnow().isoformat()

            # Index the document
            response = self.client.index(
                index=self.index_name, body=record_dict, refresh=True
            )

            doc_id = response["_id"]
            logger.info(f"Stored MetagitRecord with ID: {doc_id}")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to store MetagitRecord: {e}")
            return e

    async def get_record(self, record_id: str) -> Union[MetagitRecord, Exception]:
        """
        Retrieve a MetagitRecord by ID.

        Args:
            record_id: Document ID

        Returns:
            MetagitRecord or Exception
        """
        try:
            response = self.client.get(index=self.index_name, id=record_id)
            source = response["_source"]

            # Remove internal fields
            source.pop("@timestamp", None)
            source.pop("_id", None)

            # Create MetagitRecord from source
            record = MetagitRecord(**source)
            return record

        except Exception as e:
            logger.error(f"Failed to retrieve MetagitRecord {record_id}: {e}")
            return e

    async def search_records(
        self,
        query: str,
        _: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        size: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Union[Dict[str, Any], Exception]:
        """
        Search MetagitRecord entries.

        Args:
            query: Search query
            tenant_id: Tenant identifier (ignored in base service for compatibility)
            filters: Search filters
            page: Page number
            size: Results per page
            sort_by: Sort field
            sort_order: Sort order

        Returns:
            Search results or Exception
        """
        try:
            # Build search body
            if query.strip():
                # Use multi_match query when there's a search term
                search_body = {
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": [
                                            "name^2",
                                            "description",
                                            "metadata.tags",
                                        ],
                                        "type": "best_fields",
                                        "fuzziness": "AUTO",
                                    }
                                }
                            ]
                        }
                    },
                    "from": (page - 1) * size,
                    "size": size,
                }
            else:
                # Use match_all query when there's no search term
                search_body = {
                    "query": {"match_all": {}},
                    "from": (page - 1) * size,
                    "size": size,
                }

            # Add filters
            if filters:
                filter_queries = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        filter_queries.append({"terms": {key: value}})
                    else:
                        filter_queries.append({"term": {key: value}})

                if filter_queries:
                    # If we have filters, wrap the existing query in a bool query
                    if "bool" not in search_body["query"]:
                        search_body["query"] = {
                            "bool": {"must": [search_body["query"]]}
                        }
                    search_body["query"]["bool"]["filter"] = filter_queries

            # Add sorting
            if sort_by:
                # Validate that the sort field exists in the mapping
                try:
                    # Try to sort by the specified field
                    search_body["sort"] = [{sort_by: {"order": sort_order}}]
                except Exception as e:
                    logger.warning(
                        f"Invalid sort field '{sort_by}', using default sort: {e}"
                    )
                    # Fall back to default sort
                    search_body["sort"] = [{"detection_timestamp": {"order": "desc"}}]
            else:
                # Default sort by detection_timestamp (most recent first)
                # This field is guaranteed to exist in our mapping
                search_body["sort"] = [{"detection_timestamp": {"order": "desc"}}]

            # Execute search
            response = self.client.search(index=self.index_name, body=search_body)

            # Process results
            hits = response["hits"]["hits"]
            total = response["hits"]["total"]["value"]

            results = []
            for hit in hits:
                source = hit["_source"]
                source["_id"] = hit["_id"]
                source.pop("@timestamp", None)
                results.append(source)

            return {
                "total": total,
                "page": page,
                "size": size,
                "results": results,
                "aggregations": response.get("aggregations"),
            }

        except Exception as e:
            logger.error(f"Failed to search MetagitRecord entries: {e}")
            return e

    async def update_record(
        self, record_id: str, record: MetagitRecord
    ) -> Union[bool, Exception]:
        """
        Update a MetagitRecord.

        Args:
            record_id: Document ID
            record: Updated MetagitRecord

        Returns:
            Success status or Exception
        """
        try:
            record_dict = record.model_dump(exclude_none=True, exclude_unset=True)

            # Normalize URL if present
            if "url" in record_dict:
                record_dict["url"] = normalize_git_url(record_dict["url"])

            record_dict["@timestamp"] = datetime.utcnow().isoformat()

            self.client.update(
                index=self.index_name,
                id=record_id,
                body={"doc": record_dict},
                refresh=True,
            )

            logger.info(f"Updated MetagitRecord with ID: {record_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update MetagitRecord {record_id}: {e}")
            return e

    async def delete_record(
        self, record_id: str, _: Optional[str] = None
    ) -> Union[bool, Exception]:
        """
        Delete a MetagitRecord.

        Args:
            record_id: Document ID
            tenant_id: Tenant identifier (ignored in base service for compatibility)

        Returns:
            Success status or Exception
        """
        try:
            self.client.delete(index=self.index_name, id=record_id, refresh=True)
            logger.info(f"Deleted MetagitRecord with ID: {record_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete MetagitRecord {record_id}: {e}")
            return e

    async def bulk_store_records(
        self, records: List[MetagitRecord]
    ) -> Union[List[str], Exception]:
        """
        Bulk store multiple MetagitRecord entries.

        Args:
            records: List of MetagitRecord entries

        Returns:
            List of document IDs or Exception
        """
        try:
            actions = []
            for record in records:
                record_dict = record.model_dump(exclude_none=True, exclude_unset=True)

                # Normalize URL if present
                if "url" in record_dict:
                    record_dict["url"] = normalize_git_url(record_dict["url"])

                record_dict["@timestamp"] = datetime.utcnow().isoformat()

                actions.append({"_index": self.index_name, "_source": record_dict})

            # Use bulk API
            success, failed = 0, 0
            doc_ids = []

            for ok, result in helpers.streaming_bulk(
                self.client, actions, refresh=True, raise_on_error=False
            ):
                if ok:
                    success += 1
                    doc_ids.append(result["index"]["_id"])
                else:
                    failed += 1
                    logger.error(f"Failed to index document: {result}")

            logger.info(f"Bulk indexed {success} documents, {failed} failed")
            return (
                doc_ids
                if failed == 0
                else Exception(f"Failed to index {failed} documents")
            )

        except Exception as e:
            logger.error(f"Failed to bulk store MetagitRecord entries: {e}")
            return e

    async def get_health(self) -> Dict[str, Any]:
        """
        Get OpenSearch cluster health.

        Returns:
            Health information
        """
        try:
            cluster_health = self.client.cluster.health()
            return {
                "status": "healthy",
                "cluster_health": cluster_health,
                "index_exists": self.client.indices.exists(index=self.index_name),
            }
        except Exception as e:
            logger.error(f"Failed to get OpenSearch health: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Index statistics
        """
        try:
            stats = self.client.indices.stats(index=self.index_name)
            return {
                "total_docs": stats["indices"][self.index_name]["total"]["docs"][
                    "count"
                ],
                "total_size": stats["indices"][self.index_name]["total"]["store"][
                    "size_in_bytes"
                ],
                "indexing_stats": stats["indices"][self.index_name]["total"][
                    "indexing"
                ],
                "search_stats": stats["indices"][self.index_name]["total"]["search"],
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"error": str(e)}

    async def get_index_mapping(self) -> Dict[str, Any]:
        """
        Get index mapping.

        Returns:
            Index mapping
        """
        try:
            mapping = self.client.indices.get_mapping(index=self.index_name)
            return mapping[self.index_name]["mappings"]
        except Exception as e:
            logger.error(f"Failed to get index mapping: {e}")
            return {"error": str(e)}

    async def get_index_settings(self) -> Dict[str, Any]:
        """
        Get index settings.

        Returns:
            Index settings
        """
        try:
            settings = self.client.indices.get_settings(index=self.index_name)
            return settings[self.index_name]["settings"]["index"]
        except Exception as e:
            logger.error(f"Failed to get index settings: {e}")
            return {"error": str(e)}
