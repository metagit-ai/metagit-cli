#!/usr/bin/env python
"""
FastAPI application for metagit repository detection service.
"""

import logging
import os
import socket
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from metagit.api.detection import DetectionService

# Include routers
from metagit.api.endpoints import config, detect, records, system
from metagit.api.opensearch import OpenSearchService
from metagit.core.appconfig.models import AppConfig
from metagit.core.providers import registry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
opensearch_service: Optional[OpenSearchService] = None
detection_service: Optional[DetectionService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global opensearch_service, detection_service

    logger.info("Starting metagit detection API...")

    try:
        # Load configuration
        config_path = "metagit.config.yaml"
        app_config_result = AppConfig.load(config_path)
        if isinstance(app_config_result, Exception):
            logger.warning(
                f"Could not load config from {config_path}: {app_config_result}"
            )
            app_config = AppConfig()
        else:
            app_config = app_config_result

        # Configure OpenSearch
        opensearch_host = os.getenv("OPENSEARCH_HOST", "localhost")
        opensearch_port = int(os.getenv("OPENSEARCH_PORT", "9200"))
        opensearch_hosts = [{"host": opensearch_host, "port": opensearch_port}]

        # --- Retry logic for OpenSearch connection ---
        max_wait = 60  # seconds
        wait_interval = 2  # seconds
        waited = 0
        logger.info(
            f"Waiting for OpenSearch at {opensearch_host}:{opensearch_port} ..."
        )
        while waited < max_wait:
            try:
                with socket.create_connection(
                    (opensearch_host, opensearch_port), timeout=2
                ):
                    logger.info("OpenSearch is available!")
                    break
            except OSError:
                logger.info(
                    f"OpenSearch not available yet, retrying in {wait_interval}s..."
                )
                time.sleep(wait_interval)
                waited += wait_interval
        else:
            logger.error(f"OpenSearch not available after {max_wait} seconds. Exiting.")
            raise RuntimeError(
                f"OpenSearch not available at {opensearch_host}:{opensearch_port}"
            )
        # --- End retry logic ---

        opensearch_service = OpenSearchService(
            hosts=opensearch_hosts,
            index_name=os.getenv("OPENSEARCH_INDEX", "metagit-records"),
            username=os.getenv("OPENSEARCH_USERNAME"),
            password=os.getenv("OPENSEARCH_PASSWORD"),
            use_ssl=os.getenv("OPENSEARCH_USE_SSL", "true").lower() == "true",
            verify_certs=os.getenv("OPENSEARCH_VERIFY_CERTS", "true").lower() == "true",
        )

        registry.configure_from_app_config(app_config)
        registry.configure_from_environment()

        detection_service = DetectionService(
            opensearch_service=opensearch_service,
            max_concurrent_jobs=int(os.getenv("MAX_CONCURRENT_JOBS", "5")),
        )
        await detection_service.start()
        logger.info("Metagit detection API started successfully")

    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        raise

    yield

    logger.info("Shutting down metagit detection API...")
    if detection_service:
        await detection_service.stop()
    logger.info("Metagit detection API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Metagit Detection API",
    description="API for asynchronously detecting repository metadata and storing MetagitRecord entries",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(detect.router)
app.include_router(records.router)
app.include_router(config.router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "metagit.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
