#!/usr/bin/env python
"""
Record management subcommands for metagit.

This module provides CLI commands for managing metagit records using the
MetagitRecordManager with support for multiple storage backends.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from metagit import __version__
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.record.manager import (
    LocalFileStorageBackend,
    MetagitRecordManager,
    OpenSearchStorageBackend,
)
from metagit.core.utils.yaml_class import yaml


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@click.group(name="record", invoke_without_command=True)
@click.option(
    "--storage-type",
    type=click.Choice(["local", "opensearch"]),
    default="local",
    help="Storage backend type for records",
)
@click.option(
    "--storage-path",
    help="Path for local storage (used when storage-type is 'local')",
    default="./records",
)
@click.option(
    "--opensearch-hosts",
    help="OpenSearch hosts (comma-separated, used when storage-type is 'opensearch')",
    default="localhost:9200",
)
@click.option(
    "--opensearch-index",
    help="OpenSearch index name (used when storage-type is 'opensearch')",
    default="metagit-records",
)
@click.option(
    "--opensearch-username",
    help="OpenSearch username (used when storage-type is 'opensearch')",
    default=None,
)
@click.option(
    "--opensearch-password",
    help="OpenSearch password (used when storage-type is 'opensearch')",
    default=None,
)
@click.option(
    "--opensearch-use-ssl",
    is_flag=True,
    help="Use SSL for OpenSearch connection",
)
@click.pass_context
def record(
    ctx: click.Context,
    storage_type: str,
    storage_path: str,
    opensearch_hosts: str,
    opensearch_index: str,
    opensearch_username: str,
    opensearch_password: str,
    opensearch_use_ssl: bool,
) -> None:
    """Record management subcommands"""
    try:
        # If no subcommand is provided, show help
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            return

        # Store storage configuration in context
        ctx.obj["storage_type"] = storage_type
        ctx.obj["storage_path"] = storage_path
        ctx.obj["opensearch_hosts"] = opensearch_hosts
        ctx.obj["opensearch_index"] = opensearch_index
        ctx.obj["opensearch_username"] = opensearch_username
        ctx.obj["opensearch_password"] = opensearch_password
        ctx.obj["opensearch_use_ssl"] = opensearch_use_ssl

    except Exception as e:
        logger = ctx.obj.get("logger")
        if logger:
            logger.error(f"An error occurred in the record command: {e}")
        else:
            click.echo(f"An error occurred: {e}", err=True)
        ctx.abort()


def _get_record_manager(ctx: click.Context) -> MetagitRecordManager:
    """Get a configured MetagitRecordManager instance."""
    logger = ctx.obj["logger"]
    storage_type = ctx.obj["storage_type"]

    try:
        if storage_type == "local":
            storage_path = Path(ctx.obj["storage_path"])
            backend = LocalFileStorageBackend(storage_path)
            logger.debug(f"Using local storage backend at {storage_path}")

        elif storage_type == "opensearch":
            # Import OpenSearchService here to avoid import issues if not installed
            try:
                from metagit.api.opensearch import OpenSearchService
            except ImportError as exc:
                raise ImportError(
                    "opensearch-py is required for OpenSearch backend. Install with: pip install opensearch-py"
                ) from exc

            # Parse hosts
            hosts = []
            for host_str in ctx.obj["opensearch_hosts"].split(","):
                if ":" in host_str:
                    host, port = host_str.split(":", 1)
                    hosts.append({"host": host.strip(), "port": int(port.strip())})
                else:
                    hosts.append({"host": host_str.strip(), "port": 9200})

            opensearch_service = OpenSearchService(
                hosts=hosts,
                index_name=ctx.obj["opensearch_index"],
                username=ctx.obj["opensearch_username"],
                password=ctx.obj["opensearch_password"],
                use_ssl=ctx.obj["opensearch_use_ssl"],
                verify_certs=False,
                ssl_show_warn=False,
            )
            backend = OpenSearchStorageBackend(opensearch_service)
            logger.debug(
                f"Using OpenSearch backend with index {ctx.obj['opensearch_index']}"
            )

        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")

        return MetagitRecordManager(storage_backend=backend, logger=logger)

    except Exception as e:
        logger.error(f"Failed to initialize record manager: {e}")
        raise


@record.command("create")
@click.option(
    "--config-path",
    help="Path to the metagit configuration file",
    default=".metagit.yml",
)
@click.option(
    "--detection-source",
    help="Source of the detection",
    default="local",
)
@click.option(
    "--detection-version",
    help="Version of the detection system",
    default=__version__,
)
@click.option(
    "--output-file",
    help="Save record to file (optional)",
    default=None,
)
@click.pass_context
def record_create(
    ctx: click.Context,
    config_path: str,
    detection_source: str,
    detection_version: str,
    output_file: Optional[str],
) -> None:
    """Create a record from metagit configuration"""
    logger = ctx.obj["logger"]

    try:
        # Load configuration
        config_manager = MetagitConfigManager(config_path=Path(config_path))
        config_result = config_manager.load_config()
        if isinstance(config_result, Exception):
            raise config_result

        # Create record manager
        record_manager = _get_record_manager(ctx)

        # Create record from config
        record = record_manager.create_record_from_config(
            config=config_result,
            detection_source=detection_source,
            detection_version=detection_version,
        )

        if isinstance(record, Exception):
            raise record

        logger.success(f"Created record for project: {record.name}")
        logger.info(f"Detection source: {record.detection_source}")
        logger.info(f"Detection version: {record.detection_version}")

        # Save to file if requested
        if output_file:
            file_path = Path(output_file)
            save_result = record_manager.save_record_to_file(record, file_path)
            if isinstance(save_result, Exception):
                raise save_result
            logger.success(f"Record saved to: {file_path}")

        # Store in backend
        async def store_record():
            return await record_manager.store_record(record)

        record_id = asyncio.run(store_record())
        if isinstance(record_id, Exception):
            raise record_id

        logger.success(f"Record stored with ID: {record_id}")

    except Exception as e:
        logger.error(f"Failed to create record: {e}")
        ctx.abort()


@record.command("show")
@click.argument("record_id", required=False)
@click.option(
    "--format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format",
)
@click.pass_context
def record_show(ctx: click.Context, record_id: Optional[str], format: str) -> None:
    """Show record(s)"""
    logger = ctx.obj["logger"]

    try:
        record_manager = _get_record_manager(ctx)

        if record_id:
            # Show specific record
            async def get_record():
                return await record_manager.get_record(record_id)

            record = asyncio.run(get_record())
            if isinstance(record, Exception):
                raise record

            if format == "yaml":
                yaml.Dumper.ignore_aliases = lambda *args: True  # noqa: ARG005
                output = yaml.dump(
                    record.model_dump(exclude_none=True, exclude_defaults=True),
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                )
                logger.echo(output)
            else:  # json
                logger.echo(
                    record.model_dump_json(
                        exclude_none=True, exclude_defaults=True, indent=2
                    )
                )

        else:
            # List all records
            async def list_records():
                return await record_manager.list_records()

            records = asyncio.run(list_records())
            if isinstance(records, Exception):
                raise records

            if not records:
                logger.info("No records found")
                return

            logger.info(f"Found {len(records)} record(s):")
            for record in records:
                logger.echo(f"  ID: {getattr(record, 'record_id', 'N/A')}")
                logger.echo(f"  Name: {record.name}")
                logger.echo(f"  Description: {record.description or 'N/A'}")
                logger.echo(f"  Detection Source: {record.detection_source}")
                logger.echo(f"  Detection Timestamp: {record.detection_timestamp}")
                logger.echo("  ---")

    except Exception as e:
        logger.error(f"Failed to show record(s): {e}")
        ctx.abort()


@record.command("search")
@click.argument("query", required=True)
@click.option(
    "--page",
    type=int,
    default=1,
    help="Page number for pagination",
)
@click.option(
    "--size",
    type=int,
    default=20,
    help="Number of records per page",
)
@click.option(
    "--format",
    type=click.Choice(["yaml", "json", "table"]),
    default="table",
    help="Output format",
)
@click.pass_context
def record_search(
    ctx: click.Context, query: str, page: int, size: int, format: str
) -> None:
    """Search records"""
    logger = ctx.obj["logger"]

    try:
        record_manager = _get_record_manager(ctx)

        async def search_records():
            return await record_manager.search_records(query, page=page, size=size)

        results = asyncio.run(search_records())
        if isinstance(results, Exception):
            raise results

        records = results.get("records", [])
        total = results.get("total", 0)
        current_page = results.get("page", 1)
        total_pages = results.get("pages", 1)

        logger.info(f"Search results for '{query}': {total} total records")
        logger.info(f"Page {current_page} of {total_pages}")

        if not records:
            logger.info("No records found")
            return

        if format == "table":
            # Simple table format
            logger.echo("ID\tName\tDescription\tSource\tTimestamp")
            logger.echo("-" * 80)
            for record in records:
                record_id = getattr(record, "record_id", "N/A")
                description = record.description or "N/A"
                if len(description) > 30:
                    description = description[:27] + "..."
                logger.echo(
                    f"{record_id}\t{record.name}\t{description}\t{record.detection_source}\t{record.detection_timestamp}"
                )

        elif format == "yaml":
            yaml.Dumper.ignore_aliases = lambda *args: True  # noqa: ARG005
            output = yaml.dump(
                [
                    record.model_dump(exclude_none=True, exclude_defaults=True)
                    for record in records
                ],
                default_flow_style=False,
                sort_keys=False,
                indent=2,
            )
            logger.echo(output)

        else:  # json
            output = json.dumps(
                [
                    record.model_dump(exclude_none=True, exclude_defaults=True)
                    for record in records
                ],
                indent=2,
                cls=DateTimeEncoder,
            )
            logger.echo(output)

    except Exception as e:
        logger.error(f"Failed to search records: {e}")
        ctx.abort()


@record.command("update")
@click.argument("record_id", required=True)
@click.option(
    "--config-path",
    help="Path to the updated metagit configuration file",
    default=".metagit.yml",
)
@click.option(
    "--detection-source",
    help="Updated detection source",
    default=None,
)
@click.option(
    "--detection-version",
    help="Updated detection version",
    default=None,
)
@click.pass_context
def record_update(
    ctx: click.Context,
    record_id: str,
    config_path: str,
    detection_source: Optional[str],
    detection_version: Optional[str],
) -> None:
    """Update an existing record"""
    logger = ctx.obj["logger"]

    try:
        record_manager = _get_record_manager(ctx)

        # Get existing record
        async def get_record():
            return await record_manager.get_record(record_id)

        existing_record = asyncio.run(get_record())
        if isinstance(existing_record, Exception):
            raise existing_record

        # Load updated config if provided
        if Path(config_path).exists():
            config_manager = MetagitConfigManager(config_path=Path(config_path))
            config_result = config_manager.load_config()
            if isinstance(config_result, Exception):
                raise config_result

            # Create updated record
            updated_record = record_manager.create_record_from_config(
                config=config_result,
                detection_source=detection_source or existing_record.detection_source,
                detection_version=detection_version
                or existing_record.detection_version,
            )

            if isinstance(updated_record, Exception):
                raise updated_record
        else:
            # Update only specific fields
            updated_record = existing_record
            if detection_source:
                updated_record.detection_source = detection_source
            if detection_version:
                updated_record.detection_version = detection_version
            updated_record.detection_timestamp = (
                None  # Will be set by create_record_from_config
            )

        # Update the record
        async def update_record():
            return await record_manager.update_record(record_id, updated_record)

        result = asyncio.run(update_record())
        if isinstance(result, Exception):
            raise result

        logger.success(f"Record {record_id} updated successfully")

    except Exception as e:
        logger.error(f"Failed to update record: {e}")
        ctx.abort()


@record.command("delete")
@click.argument("record_id", required=True)
@click.option(
    "--force",
    is_flag=True,
    help="Force deletion without confirmation",
)
@click.pass_context
def record_delete(ctx: click.Context, record_id: str, force: bool) -> None:
    """Delete a record"""
    logger = ctx.obj["logger"]

    try:
        if not force:
            # Show record info before deletion
            record_manager = _get_record_manager(ctx)

            async def get_record():
                return await record_manager.get_record(record_id)

            record = asyncio.run(get_record())
            if isinstance(record, Exception):
                raise record

            logger.info("About to delete record:")
            logger.info(f"  ID: {record_id}")
            logger.info(f"  Name: {record.name}")
            logger.info(f"  Description: {record.description or 'N/A'}")

            if not click.confirm("Are you sure you want to delete this record?"):
                logger.info("Deletion cancelled")
                return

        # Delete the record
        record_manager = _get_record_manager(ctx)

        async def delete_record():
            return await record_manager.delete_record(record_id)

        result = asyncio.run(delete_record())
        if isinstance(result, Exception):
            raise result

        logger.success(f"Record {record_id} deleted successfully")

    except Exception as e:
        logger.error(f"Failed to delete record: {e}")
        ctx.abort()


@record.command("export")
@click.argument("record_id", required=True)
@click.argument("output_file", required=True)
@click.option(
    "--format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Export format",
)
@click.pass_context
def record_export(
    ctx: click.Context, record_id: str, output_file: str, format: str
) -> None:
    """Export a record to file"""
    logger = ctx.obj["logger"]

    try:
        record_manager = _get_record_manager(ctx)

        # Get the record
        async def get_record():
            return await record_manager.get_record(record_id)

        record = asyncio.run(get_record())
        if isinstance(record, Exception):
            raise record

        # Export to file
        file_path = Path(output_file)

        if format == "yaml":
            save_result = record_manager.save_record_to_file(record, file_path)
            if isinstance(save_result, Exception):
                raise save_result
        else:  # json
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    record.model_dump(exclude_none=True, exclude_defaults=True),
                    f,
                    indent=2,
                    cls=DateTimeEncoder,
                )

        logger.success(f"Record exported to: {file_path}")

    except Exception as e:
        logger.error(f"Failed to export record: {e}")
        ctx.abort()


@record.command("import")
@click.argument("input_file", required=True)
@click.option(
    "--detection-source",
    help="Override detection source",
    default=None,
)
@click.option(
    "--detection-version",
    help="Override detection version",
    default=None,
)
@click.pass_context
def record_import(
    ctx: click.Context,
    input_file: str,
    detection_source: Optional[str],
    detection_version: Optional[str],
) -> None:
    """Import a record from file"""
    logger = ctx.obj["logger"]

    try:
        record_manager = _get_record_manager(ctx)

        # Load record from file
        file_path = Path(input_file)
        record = record_manager.load_record_from_file(file_path)
        if isinstance(record, Exception):
            raise record

        # Override fields if specified
        if detection_source:
            record.detection_source = detection_source
        if detection_version:
            record.detection_version = detection_version

        # Store the record
        async def store_record():
            return await record_manager.store_record(record)

        record_id = asyncio.run(store_record())
        if isinstance(record_id, Exception):
            raise record_id

        logger.success(f"Record imported with ID: {record_id}")
        logger.info(f"Name: {record.name}")
        logger.info(f"Detection source: {record.detection_source}")

    except Exception as e:
        logger.error(f"Failed to import record: {e}")
        ctx.abort()


@record.command("stats")
@click.pass_context
def record_stats(ctx: click.Context) -> None:
    """Show record storage statistics"""
    logger = ctx.obj["logger"]

    try:
        record_manager = _get_record_manager(ctx)

        # Get all records for statistics
        async def list_records():
            return await record_manager.list_records(page=1, size=1000)

        records = asyncio.run(list_records())
        if isinstance(records, Exception):
            raise records

        total_records = len(records)

        if total_records == 0:
            logger.info("No records found")
            return

        # Calculate statistics
        sources = {}
        kinds = {}
        languages = {}

        for record in records:
            # Count by detection source
            source = record.detection_source or "unknown"
            sources[source] = sources.get(source, 0) + 1

            # Count by project kind
            kind = record.kind or "unknown"
            kinds[kind] = kinds.get(kind, 0) + 1

            # Count by primary language
            if record.language and record.language.primary:
                lang = record.language.primary
                languages[lang] = languages.get(lang, 0) + 1

        # Display statistics
        logger.info("Record Statistics:")
        logger.info(f"  Total records: {total_records}")
        logger.info(f"  Storage type: {ctx.obj['storage_type']}")

        logger.info("\nBy Detection Source:")
        for source, count in sorted(sources.items()):
            logger.info(f"  {source}: {count}")

        logger.info("\nBy Project Kind:")
        for kind, count in sorted(kinds.items()):
            logger.info(f"  {kind}: {count}")

        logger.info("\nBy Primary Language:")
        for lang, count in sorted(languages.items()):
            logger.info(f"  {lang}: {count}")

    except Exception as e:
        logger.error(f"Failed to get record statistics: {e}")
        ctx.abort()
