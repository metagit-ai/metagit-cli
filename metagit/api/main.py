#!/usr/bin/env python
"""
Main entry point for the metagit detection API.
"""

import uvicorn

from metagit.api.config import config


def main():
    """Start the FastAPI application."""
    uvicorn.run(
        "metagit.api.app:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.debug,
        log_level="debug" if config.api.debug else "info",
    )


if __name__ == "__main__":
    main()
