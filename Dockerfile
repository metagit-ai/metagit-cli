# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install uv
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy pyproject.toml and lock file (if exists)
COPY pyproject.toml ./
COPY uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy application code
COPY metagit/ ./metagit/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Run the application as a CLI
ENTRYPOINT ["uv", "run", "python", "-m", "metagit.cli.main"]
CMD []