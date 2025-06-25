#!/usr/bin/env python
"""
Record endpoints for the metagit API.
"""

import logging
import urllib.parse
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from metagit.api.dependencies import (
    get_current_tenant,
    get_tenant_aware_opensearch_service,
)
from metagit.api.models import SearchRequest, SearchResponse
from metagit.core.config.models import MetagitRecord
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/records", tags=["records"])


@router.post("/search", response_model=SearchResponse)
async def search_records(
    request: SearchRequest,
    current_tenant: str = Depends(get_current_tenant),
    opensearch_service=Depends(get_tenant_aware_opensearch_service),
):
    """Search MetagitRecord entries with tenant filtering."""
    try:
        # Use tenant from request if provided, otherwise use current tenant
        tenant_id = request.tenant_id or current_tenant

        result = await opensearch_service.search_records(
            query=request.query,
            tenant_id=tenant_id,
            filters=request.filters,
            page=request.page,
            size=request.size,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
        )

        if isinstance(result, Exception):
            raise HTTPException(status_code=500, detail=f"Search failed: {result}")

        return SearchResponse(
            total=result["total"],
            page=result["page"],
            size=result["size"],
            results=result["results"],
            aggregations=result.get("aggregations"),
        )

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/by-url")
async def get_records_by_url(
    url: str,
    current_tenant: str = Depends(get_current_tenant),
    opensearch_service=Depends(get_tenant_aware_opensearch_service),
):
    """Get MetagitRecord entries by git URL with tenant filtering."""
    try:
        logger.info(
            f"Searching for records with URL: {url} for tenant: {current_tenant}"
        )

        # URL decode the git URL and normalize it
        decoded_url = urllib.parse.unquote(url)
        normalized_url = normalize_git_url(decoded_url)
        logger.info(f"Decoded and normalized URL: {normalized_url}")

        # Search for records by URL with tenant filtering
        logger.info("Executing OpenSearch search...")
        result = await opensearch_service.search_records(
            query="",  # Empty query to match all
            tenant_id=current_tenant,
            filters={"url": normalized_url},
            page=1,
            size=10,  # Allow multiple results in case of duplicates
        )

        if isinstance(result, Exception):
            logger.error(f"OpenSearch search failed: {result}")
            raise HTTPException(status_code=500, detail=f"Search failed: {result}")

        logger.info(f"Search returned {result.get('total', 0)} results")

        if result["total"] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No MetagitRecord found for URL: {normalized_url}",
            )

        # Process results
        records = []
        for i, record_data in enumerate(result["results"]):
            logger.info(f"Processing record {i + 1}/{len(result['results'])}")
            record_id = record_data.pop("_id", None)
            logger.info(f"Record ID: {record_id}")

            # Remove internal OpenSearch fields that aren't part of MetagitRecord
            internal_fields = ["@timestamp", "_id", "_index", "_score", "tenant_id"]
            for field in internal_fields:
                record_data.pop(field, None)

            logger.info(f"Record data keys: {list(record_data.keys())}")

            try:
                # Create MetagitRecord from the data
                record = MetagitRecord(**record_data)
                logger.info(f"Successfully created MetagitRecord for {record_id}")

                records.append(
                    {
                        "record_id": record_id,
                        "record": record.model_dump(),
                    }
                )
            except ValidationError as e:
                logger.warning(f"Validation error for record {record_id}: {e}")
                logger.warning(f"Record data: {record_data}")
                # Return raw data if validation fails
                records.append(
                    {
                        "record_id": record_id,
                        "record": record_data,
                        "validation_error": str(e),
                    }
                )
            except Exception as e:
                logger.error(f"Error processing record {record_id}: {e}")
                logger.error(f"Record data: {record_data}")
                records.append(
                    {
                        "record_id": record_id,
                        "record": record_data,
                        "error": str(e),
                    }
                )

        logger.info(f"Successfully processed {len(records)} records")
        return {
            "url": normalized_url,
            "total": result["total"],
            "records": records,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving records for URL {url}: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/all")
async def delete_all_records(
    current_tenant: str = Depends(get_current_tenant),
    opensearch_service=Depends(get_tenant_aware_opensearch_service),
):
    """Delete all MetagitRecord entries for the current tenant."""
    try:
        logger.warning(f"Attempting to delete ALL records for tenant: {current_tenant}")

        # Search for all records for the tenant
        result = await opensearch_service.search_records(
            query="",
            tenant_id=current_tenant,
            filters={},
            page=1,
            size=1000,  # Get up to 1000 records per batch
        )

        if isinstance(result, Exception):
            logger.error(f"Search failed: {result}")
            raise HTTPException(status_code=500, detail=f"Search failed: {result}")

        if result["total"] == 0:
            return {
                "message": "No records found to delete",
                "deleted_count": 0,
                "failed_count": 0,
                "total_found": 0,
            }

        # Delete records in batches to avoid overwhelming the system
        batch_size = 100
        total_deleted = 0
        total_failed = 0
        failed_ids = []

        for page in range(1, (result["total"] // batch_size) + 2):
            batch_result = await opensearch_service.search_records(
                query="",
                tenant_id=current_tenant,
                filters={},
                page=page,
                size=batch_size,
            )

            if isinstance(batch_result, Exception):
                logger.error(f"Batch search failed: {batch_result}")
                continue

            for record_data in batch_result["results"]:
                record_id = record_data.get("_id")
                if record_id:
                    delete_result = await opensearch_service.delete_record(
                        record_id, current_tenant
                    )
                    if isinstance(delete_result, Exception):
                        logger.error(
                            f"Failed to delete record {record_id}: {delete_result}"
                        )
                        total_failed += 1
                        failed_ids.append(record_id)
                    else:
                        total_deleted += 1

        logger.info(
            f"Deleted {total_deleted} records, failed to delete {total_failed} records"
        )
        return {
            "message": f"Deleted {total_deleted} records for tenant {current_tenant}",
            "deleted_count": total_deleted,
            "failed_count": total_failed,
            "failed_ids": failed_ids,
            "total_found": result["total"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting all records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/by-url")
async def delete_records_by_url(
    url: str,
    current_tenant: str = Depends(get_current_tenant),
    opensearch_service=Depends(get_tenant_aware_opensearch_service),
):
    """Delete MetagitRecord entries by git URL with tenant verification."""
    try:
        logger.info(f"Deleting records with URL: {url} for tenant: {current_tenant}")

        # URL decode the git URL and normalize it
        decoded_url = urllib.parse.unquote(url)
        normalized_url = normalize_git_url(decoded_url)
        logger.info(f"Decoded and normalized URL: {normalized_url}")

        # Search for records by URL with tenant filtering
        result = await opensearch_service.search_records(
            query="",
            tenant_id=current_tenant,
            filters={"url": normalized_url},
            page=1,
            size=100,  # Get up to 100 records
        )

        if isinstance(result, Exception):
            logger.error(f"Search failed: {result}")
            raise HTTPException(status_code=500, detail=f"Search failed: {result}")

        if result["total"] == 0:
            return {
                "message": f"No records found for URL: {normalized_url}",
                "deleted_count": 0,
                "failed_count": 0,
            }

        # Delete records
        total_deleted = 0
        total_failed = 0
        failed_ids = []

        for record_data in result["results"]:
            record_id = record_data.get("_id")
            if record_id:
                delete_result = await opensearch_service.delete_record(
                    record_id, current_tenant
                )
                if isinstance(delete_result, Exception):
                    logger.error(
                        f"Failed to delete record {record_id}: {delete_result}"
                    )
                    total_failed += 1
                    failed_ids.append(record_id)
                else:
                    total_deleted += 1

        logger.info(
            f"Deleted {total_deleted} records, failed to delete {total_failed} records"
        )
        return {
            "message": f"Deleted {total_deleted} records for URL: {normalized_url}",
            "deleted_count": total_deleted,
            "failed_count": total_failed,
            "failed_ids": failed_ids,
            "total_found": result["total"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting records for URL {url}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/bulk")
async def bulk_delete_records(
    record_ids: List[str],
    current_tenant: str = Depends(get_current_tenant),
    opensearch_service=Depends(get_tenant_aware_opensearch_service),
):
    """Delete multiple MetagitRecord entries by ID with tenant verification."""
    try:
        logger.info(
            f"Bulk deleting {len(record_ids)} records for tenant: {current_tenant}"
        )

        total_deleted = 0
        total_failed = 0
        failed_ids = []

        for record_id in record_ids:
            delete_result = await opensearch_service.delete_record(
                record_id, current_tenant
            )
            if isinstance(delete_result, Exception):
                logger.error(f"Failed to delete record {record_id}: {delete_result}")
                total_failed += 1
                failed_ids.append(record_id)
            else:
                total_deleted += 1

        logger.info(
            f"Bulk delete completed: {total_deleted} deleted, {total_failed} failed"
        )
        return {
            "message": f"Bulk delete completed for tenant {current_tenant}",
            "deleted_count": total_deleted,
            "failed_count": total_failed,
            "failed_ids": failed_ids,
            "total_requested": len(record_ids),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/by-filter")
async def delete_records_by_filter(
    filters: dict,
    current_tenant: str = Depends(get_current_tenant),
    opensearch_service=Depends(get_tenant_aware_opensearch_service),
):
    """Delete MetagitRecord entries by filter with tenant verification."""
    try:
        logger.info(f"Deleting records by filter for tenant: {current_tenant}")
        logger.info(f"Filters: {filters}")

        # Search for records matching the filter with tenant filtering
        result = await opensearch_service.search_records(
            query="",
            tenant_id=current_tenant,
            filters=filters,
            page=1,
            size=1000,  # Get up to 1000 records
        )

        if isinstance(result, Exception):
            logger.error(f"Search failed: {result}")
            raise HTTPException(status_code=500, detail=f"Search failed: {result}")

        if result["total"] == 0:
            return {
                "message": "No records found matching the filter",
                "deleted_count": 0,
                "failed_count": 0,
                "total_found": 0,
            }

        # Delete records
        total_deleted = 0
        total_failed = 0
        failed_ids = []

        for record_data in result["results"]:
            record_id = record_data.get("_id")
            if record_id:
                delete_result = await opensearch_service.delete_record(
                    record_id, current_tenant
                )
                if isinstance(delete_result, Exception):
                    logger.error(
                        f"Failed to delete record {record_id}: {delete_result}"
                    )
                    total_failed += 1
                    failed_ids.append(record_id)
                else:
                    total_deleted += 1

        logger.info(
            f"Filter delete completed: {total_deleted} deleted, {total_failed} failed"
        )
        return {
            "message": f"Filter delete completed for tenant {current_tenant}",
            "deleted_count": total_deleted,
            "failed_count": total_failed,
            "failed_ids": failed_ids,
            "total_found": result["total"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting records by filter: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{record_id}")
async def get_record(
    record_id: str,
    current_tenant: str = Depends(get_current_tenant),
    opensearch_service=Depends(get_tenant_aware_opensearch_service),
):
    """Get a MetagitRecord by ID with tenant verification."""
    try:
        result = await opensearch_service.get_record(record_id, current_tenant)

        if isinstance(result, Exception):
            raise HTTPException(
                status_code=404, detail=f"Record {record_id} not found or access denied"
            )

        return {"record": result.model_dump()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting record {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{record_id}")
async def delete_record(
    record_id: str,
    current_tenant: str = Depends(get_current_tenant),
    opensearch_service=Depends(get_tenant_aware_opensearch_service),
):
    """Delete a MetagitRecord by ID with tenant verification."""
    try:
        result = await opensearch_service.delete_record(record_id, current_tenant)

        if isinstance(result, Exception):
            raise HTTPException(
                status_code=404, detail=f"Record {record_id} not found or access denied"
            )

        return {"message": f"Record {record_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting record {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
