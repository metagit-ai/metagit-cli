#!/usr/bin/env python
"""
Record endpoints for the metagit API.
"""

import logging
import urllib.parse
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from metagit.api.models import SearchRequest, SearchResponse
from metagit.api.opensearch import OpenSearchService
from metagit.core.config.models import MetagitRecord
from metagit.core.utils.common import normalize_git_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/records", tags=["records"])


def get_opensearch_service() -> OpenSearchService:
    """Dependency to get OpenSearch service."""
    from metagit.api.app import opensearch_service

    if not opensearch_service:
        raise HTTPException(status_code=503, detail="OpenSearch service not available")
    return opensearch_service


@router.post("/search", response_model=SearchResponse)
async def search_records(
    request: SearchRequest,
    opensearch: OpenSearchService = Depends(get_opensearch_service),
):
    """Search MetagitRecord entries."""
    try:
        result = await opensearch.search_records(
            query=request.query,
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
    opensearch: OpenSearchService = Depends(get_opensearch_service),
):
    """Get MetagitRecord entries by git URL."""
    try:
        logger.info(f"Searching for records with URL: {url}")

        # URL decode the git URL and normalize it
        decoded_url = urllib.parse.unquote(url)
        normalized_url = normalize_git_url(decoded_url)
        logger.info(f"Decoded and normalized URL: {normalized_url}")

        # Search for records by URL
        logger.info("Executing OpenSearch search...")
        result = await opensearch.search_records(
            query="",  # Empty query to match all
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
            internal_fields = ["@timestamp", "_id", "_index", "_score"]
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
    opensearch: OpenSearchService = Depends(get_opensearch_service),
):
    """Delete all MetagitRecord entries in the index."""
    try:
        logger.warning("Attempting to delete ALL records in the index")

        # Search for all records
        result = await opensearch.search_records(
            query="",
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
            batch_result = await opensearch.search_records(
                query="",
                filters={},
                page=page,
                size=batch_size,
            )

            if isinstance(batch_result, Exception):
                logger.error(f"Failed to get batch {page}: {batch_result}")
                continue

            for record_data in batch_result["results"]:
                record_id = record_data.get("_id")
                if record_id:
                    delete_result = await opensearch.delete_record(record_id)
                    if isinstance(delete_result, Exception):
                        logger.error(
                            f"Failed to delete record {record_id}: {delete_result}"
                        )
                        total_failed += 1
                        failed_ids.append(record_id)
                    else:
                        total_deleted += 1

        logger.warning(f"Deleted {total_deleted} records, {total_failed} failed")

        return {
            "message": f"Deleted {total_deleted} records, {total_failed} failed",
            "deleted_count": total_deleted,
            "failed_count": total_failed,
            "total_found": result["total"],
            "failed_ids": failed_ids[
                :10
            ],  # Return first 10 failed IDs to avoid huge responses
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting all records: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/by-url")
async def delete_records_by_url(
    url: str,
    opensearch: OpenSearchService = Depends(get_opensearch_service),
):
    """Delete all MetagitRecord entries for a specific git URL."""
    try:
        logger.info(f"Deleting records for URL: {url}")

        # URL decode the git URL and normalize it
        decoded_url = urllib.parse.unquote(url)
        normalized_url = normalize_git_url(decoded_url)
        logger.info(f"Decoded and normalized URL: {normalized_url}")

        # Search for records by URL
        result = await opensearch.search_records(
            query="",
            filters={"url": normalized_url},
            page=1,
            size=100,  # Get up to 100 records
        )

        if isinstance(result, Exception):
            logger.error(f"Search failed: {result}")
            raise HTTPException(status_code=500, detail=f"Search failed: {result}")

        if result["total"] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No MetagitRecord found for URL: {normalized_url}",
            )

        # Delete each record
        deleted_count = 0
        failed_count = 0
        for record_data in result["results"]:
            record_id = record_data.get("_id")
            if record_id:
                delete_result = await opensearch.delete_record(record_id)
                if isinstance(delete_result, Exception):
                    logger.error(
                        f"Failed to delete record {record_id}: {delete_result}"
                    )
                    failed_count += 1
                else:
                    deleted_count += 1

        return {
            "message": f"Deleted {deleted_count} records for URL: {normalized_url}",
            "deleted_count": deleted_count,
            "failed_count": failed_count,
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
    opensearch: OpenSearchService = Depends(get_opensearch_service),
):
    """Delete multiple MetagitRecord entries by their IDs."""
    try:
        logger.info(f"Bulk deleting {len(record_ids)} records")

        deleted_count = 0
        failed_count = 0
        failed_ids = []

        for record_id in record_ids:
            delete_result = await opensearch.delete_record(record_id)
            if isinstance(delete_result, Exception):
                logger.error(f"Failed to delete record {record_id}: {delete_result}")
                failed_count += 1
                failed_ids.append(record_id)
            else:
                deleted_count += 1

        return {
            "message": f"Bulk delete completed: {deleted_count} deleted, {failed_count} failed",
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "failed_ids": failed_ids,
        }

    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/by-filter")
async def delete_records_by_filter(
    filters: dict,
    opensearch: OpenSearchService = Depends(get_opensearch_service),
):
    """Delete MetagitRecord entries matching the specified filters."""
    try:
        logger.info(f"Deleting records with filters: {filters}")

        # Search for records matching the filters
        result = await opensearch.search_records(
            query="",
            filters=filters,
            page=1,
            size=100,  # Get up to 100 records
        )

        if isinstance(result, Exception):
            logger.error(f"Search failed: {result}")
            raise HTTPException(status_code=500, detail=f"Search failed: {result}")

        if result["total"] == 0:
            return {
                "message": "No records found matching the specified filters",
                "deleted_count": 0,
                "failed_count": 0,
                "total_found": 0,
            }

        # Delete each record
        deleted_count = 0
        failed_count = 0
        for record_data in result["results"]:
            record_id = record_data.get("_id")
            if record_id:
                delete_result = await opensearch.delete_record(record_id)
                if isinstance(delete_result, Exception):
                    logger.error(
                        f"Failed to delete record {record_id}: {delete_result}"
                    )
                    failed_count += 1
                else:
                    deleted_count += 1

        return {
            "message": f"Deleted {deleted_count} records matching filters",
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "total_found": result["total"],
            "filters_applied": filters,
        }

    except Exception as e:
        logger.error(f"Error deleting records by filter: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{record_id}")
async def get_record(
    record_id: str,
    opensearch: OpenSearchService = Depends(get_opensearch_service),
):
    """Get a specific MetagitRecord by ID."""
    try:
        record = await opensearch.get_record(record_id)

        if isinstance(record, Exception):
            raise HTTPException(status_code=404, detail="Record not found")

        return record.model_dump()

    except Exception as e:
        logger.error(f"Error retrieving record {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{record_id}")
async def delete_record(
    record_id: str,
    opensearch: OpenSearchService = Depends(get_opensearch_service),
):
    """Delete a MetagitRecord by ID."""
    try:
        result = await opensearch.delete_record(record_id)

        if isinstance(result, Exception):
            raise HTTPException(status_code=404, detail="Record not found")

        return {"message": "Record deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting record {record_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
