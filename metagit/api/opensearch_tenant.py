#!/usr/bin/env python
"""
Tenant-aware OpenSearch service for storing and retrieving MetagitRecord entries.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from opensearchpy import OpenSearch, helpers

from metagit.core.config.models import MetagitRecord
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)


class TenantAwareOpenSearchService:
    """Tenant-aware OpenSearch service for MetagitRecord storage."""

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
        Initialize tenant-aware OpenSearch service.

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
        """Ensure the index exists with proper mapping including tenant support."""
        if not self.client.indices.exists(index=self.index_name):
            logger.info(f"Creating index: {self.index_name}")

            # Define mapping for MetagitRecord with tenant support
            mapping = {
                "mappings": {
                    "properties": {
                        "@timestamp": {"type": "date"},
                        "tenant_id": {"type": "keyword"},  # Tenant field
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
            # Check if existing index has tenant field, add if missing
            self._ensure_tenant_mapping()

    def _ensure_tenant_mapping(self) -> None:
        """Ensure tenant_id field exists in mapping."""
        try:
            mapping = self.client.indices.get_mapping(index=self.index_name)
            properties = mapping[self.index_name]["mappings"]["properties"]

            # Check if tenant_id field exists
            if "tenant_id" not in properties:
                logger.info("Adding tenant_id field to existing index mapping")
                mapping_update = {"properties": {"tenant_id": {"type": "keyword"}}}
                self.client.indices.put_mapping(
                    index=self.index_name, body=mapping_update
                )
                logger.info("Successfully added tenant_id field to index mapping")
            else:
                logger.debug("tenant_id field already exists in index mapping")

        except Exception as e:
            logger.error(f"Error ensuring tenant mapping: {e}")
            raise

    async def store_record(
        self, record: MetagitRecord, tenant_id: str
    ) -> Union[str, Exception]:
        """
        Store a MetagitRecord in OpenSearch with tenant context.

        Args:
            record: MetagitRecord to store
            tenant_id: Tenant identifier

        Returns:
            Record ID or Exception
        """
        try:
            # Convert record to dict and add tenant context
            record_dict = record.model_dump()
            record_dict["tenant_id"] = tenant_id
            record_dict["@timestamp"] = datetime.utcnow().isoformat()

            # Store in OpenSearch
            response = self.client.index(
                index=self.index_name, body=record_dict, refresh=True
            )

            record_id = response["_id"]
            logger.info(f"Stored record {record_id} for tenant {tenant_id}")
            return record_id

        except Exception as e:
            logger.error(f"Failed to store record for tenant {tenant_id}: {e}")
            return e

    async def get_record(
        self, record_id: str, tenant_id: str
    ) -> Union[MetagitRecord, Exception]:
        """
        Get a MetagitRecord by ID with tenant filtering.

        Args:
            record_id: Record ID to retrieve
            tenant_id: Tenant identifier for filtering

        Returns:
            MetagitRecord or Exception
        """
        try:
            response = self.client.get(index=self.index_name, id=record_id)

            source = response["_source"]

            # Verify tenant ownership
            if source.get("tenant_id") != tenant_id:
                return Exception("Record not found or access denied")

            return MetagitRecord(**source)

        except Exception as e:
            logger.error(
                f"Failed to get record {record_id} for tenant {tenant_id}: {e}"
            )
            return e

    async def search_records(
        self,
        query: str,
        tenant_id: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        size: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
    ) -> Union[Dict[str, Any], Exception]:
        """
        Search records with tenant filtering.

        Args:
            query: Search query
            tenant_id: Tenant identifier for filtering
            filters: Additional search filters
            page: Page number
            size: Results per page
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Search results or Exception
        """
        try:
            # Build search query with tenant filter
            search_body = {
                "query": {
                    "bool": {
                        "must": [{"term": {"tenant_id": tenant_id}}]  # Tenant filter
                    }
                },
                "from": (page - 1) * size,
                "size": size,
            }

            # Add text search if query provided
            if query.strip():
                search_body["query"]["bool"]["must"].append(
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["name^2", "description", "url"],
                            "type": "best_fields",
                        }
                    }
                )

            # Add additional filters
            if filters:
                for key, value in filters.items():
                    if key != "tenant_id":  # Don't allow overriding tenant filter
                        if isinstance(value, list):
                            search_body["query"]["bool"]["must"].append(
                                {"terms": {key: value}}
                            )
                        else:
                            search_body["query"]["bool"]["must"].append(
                                {"term": {key: value}}
                            )

            # Add sorting
            if sort_by:
                search_body["sort"] = [{sort_by: {"order": sort_order}}]
            else:
                search_body["sort"] = [{"@timestamp": {"order": "desc"}}]

            response = self.client.search(index=self.index_name, body=search_body)

            # Process results
            hits = response["hits"]["hits"]
            total = response["hits"]["total"]["value"]

            results = []
            for hit in hits:
                source = hit["_source"]
                source["_id"] = hit["_id"]
                results.append(source)

            return {
                "total": total,
                "page": page,
                "size": size,
                "results": results,
                "aggregations": response.get("aggregations"),
            }

        except Exception as e:
            logger.error(f"Failed to search records for tenant {tenant_id}: {e}")
            return e

    async def update_record(
        self, record_id: str, record: MetagitRecord, tenant_id: str
    ) -> Union[bool, Exception]:
        """
        Update a MetagitRecord with tenant verification.

        Args:
            record_id: Record ID to update
            record: Updated MetagitRecord
            tenant_id: Tenant identifier for verification

        Returns:
            Success status or Exception
        """
        try:
            # First verify tenant ownership
            existing_record = await self.get_record(record_id, tenant_id)
            if isinstance(existing_record, Exception):
                return existing_record

            # Update record
            record_dict = record.model_dump()
            record_dict["tenant_id"] = tenant_id  # Ensure tenant is preserved
            record_dict["@timestamp"] = datetime.utcnow().isoformat()

            self.client.update(
                index=self.index_name,
                id=record_id,
                body={"doc": record_dict},
                refresh=True,
            )

            logger.info(f"Updated record {record_id} for tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to update record {record_id} for tenant {tenant_id}: {e}"
            )
            return e

    async def delete_record(
        self, record_id: str, tenant_id: str
    ) -> Union[bool, Exception]:
        """
        Delete a MetagitRecord with tenant verification.

        Args:
            record_id: Record ID to delete
            tenant_id: Tenant identifier for verification

        Returns:
            Success status or Exception
        """
        try:
            # First verify tenant ownership
            existing_record = await self.get_record(record_id, tenant_id)
            if isinstance(existing_record, Exception):
                return existing_record

            # Delete record
            self.client.delete(index=self.index_name, id=record_id, refresh=True)

            logger.info(f"Deleted record {record_id} for tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete record {record_id} for tenant {tenant_id}: {e}"
            )
            return e

    async def get_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            cluster_health = self.client.cluster.health()
            return {
                "status": "healthy",
                "cluster_status": cluster_health["status"],
                "number_of_nodes": cluster_health["number_of_nodes"],
                "active_shards": cluster_health["active_shards"],
                "index_count": len(self.client.cat.indices(format="json")),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
