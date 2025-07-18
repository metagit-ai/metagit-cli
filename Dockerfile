# Build stage
FROM python:3.13-slim AS builder

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
COPY README.md ./
COPY LICENSE ./
# Copy application code
COPY src ./src

# Install dependencies using uv
RUN uv sync --frozen


# Build wheel file using uv
RUN uv build --wheel

# Final stage - only the installed application
FROM python:3.13-slim

RUN apt-get update && apt-get install -y git

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install uv
RUN pip install uv

# Copy the wheel file from builder stage
COPY --from=builder /app/dist/*.whl /tmp/

# Install the wheel file
RUN uv pip install --system /tmp/*.whl && rm -rf /tmp/*.whl

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

# Run the application as a CLI
ENTRYPOINT ["metagit"]
CMD []