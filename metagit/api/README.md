# Metagit Detection API

A FastAPI-based service for asynchronously detecting repository metadata and storing MetagitRecord entries in OpenSearch.

## Features

- **Asynchronous Repository Detection**: Submit detection jobs that are processed in the background
- **OpenSearch Integration**: Store and search MetagitRecord entries with full-text search capabilities
- **Provider Support**: Integrate with GitHub, GitLab, and other git providers for enriched metadata
- **RESTful API**: Complete REST API with OpenAPI documentation
- **Job Management**: Track detection job status and progress
- **Scalable Architecture**: Built for horizontal scaling with async processing

## Architecture

The API consists of several key components:

- **FastAPI Application** (`app.py`): Main application with REST endpoints
- **Detection Service** (`detection.py`): Async job processing and repository analysis
- **OpenSearch Service** (`opensearch.py`): Data storage and search functionality
- **API Models** (`models.py`): Request/response models and data structures

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository and navigate to the project root**

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API tokens
   ```

3. **Start the services**
   ```bash
   docker-compose -f docker-compose.api.yml up -d
   ```

4. **Access the services**
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - OpenSearch Dashboards: http://localhost:5601

### Manual Setup

1. **Install dependencies**
   ```bash
   pip install -e ".[api]"
   ```

2. **Set up OpenSearch**
   - Install and start OpenSearch
   - Configure connection settings in environment variables

3. **Configure environment variables**
   ```bash
   export OPENSEARCH_HOST=localhost
   export OPENSEARCH_PORT=9200
   export GITHUB_TOKEN=your_github_token
   export GITLAB_TOKEN=your_gitlab_token
   ```

4. **Start the API**
   ```bash
   python -m metagit.api.main
   ```

## API Endpoints

### Detection Endpoints

- `POST /detect` - Submit a repository detection job
- `GET /detect/{detection_id}` - Get detection job status
- `GET /detect` - List all detection jobs

### Search Endpoints

- `POST /search` - Search MetagitRecord entries
- `GET /records/{record_id}` - Get a specific record
- `DELETE /records/{record_id}` - Delete a record

### System Endpoints

- `GET /health` - Health check
- `GET /providers` - List available git providers
- `GET /docs` - Interactive API documentation

## Usage Examples

### Submit a Detection Job

```bash
curl -X POST "http://localhost:8000/detect" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/username/repo",
    "priority": "normal",
    "force_refresh": false
  }'
```

Response:
```json
{
  "detection_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "repository_url": "https://github.com/username/repo",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

### Check Job Status

```bash
curl "http://localhost:8000/detect/550e8400-e29b-41d4-a716-446655440000"
```

Response:
```json
{
  "detection_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100.0,
  "message": "Detection completed successfully",
  "record_id": "abc123"
}
```

### Search Records

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python api",
    "filters": {"kind": "application"},
    "page": 1,
    "size": 10
  }'
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENSEARCH_HOST` | `localhost` | OpenSearch host |
| `OPENSEARCH_PORT` | `9200` | OpenSearch port |
| `OPENSEARCH_INDEX` | `metagit-records` | Index name |
| `OPENSEARCH_USERNAME` | `None` | OpenSearch username |
| `OPENSEARCH_PASSWORD` | `None` | OpenSearch password |
| `OPENSEARCH_USE_SSL` | `true` | Use SSL for OpenSearch |
| `API_HOST` | `0.0.0.0` | API host |
| `API_PORT` | `8000` | API port |
| `API_DEBUG` | `false` | Debug mode |
| `MAX_CONCURRENT_JOBS` | `5` | Max concurrent detection jobs |
| `GITHUB_TOKEN` | `None` | GitHub API token |
| `GITLAB_TOKEN` | `None` | GitLab API token |

### OpenSearch Mapping

The API automatically creates an OpenSearch index with the following mapping:

- **Text fields**: `name`, `description` (with standard analyzer)
- **Keyword fields**: `url`, `kind`, `branch_strategy`, `detection_source`
- **Date fields**: `detection_timestamp`
- **Nested objects**: `branches`, `metrics`, `metadata`
- **Arrays**: `language_detection`, `project_type_detection`

## Development

### Running Tests

```bash
pytest tests/test_api_*.py -v
```

### Code Formatting

```bash
black metagit/api/
isort metagit/api/
```

### Type Checking

```bash
mypy metagit/api/
```

## Deployment

### Production Considerations

1. **Security**: Enable OpenSearch security plugins
2. **Scaling**: Use multiple API instances behind a load balancer
3. **Monitoring**: Add Prometheus metrics and Grafana dashboards
4. **Backup**: Configure OpenSearch snapshots
5. **SSL/TLS**: Use proper certificates for production

### Kubernetes Deployment

Example deployment manifests are available in the `k8s/` directory.

## Troubleshooting

### Common Issues

1. **OpenSearch Connection Failed**
   - Check OpenSearch is running
   - Verify host/port configuration
   - Check SSL settings

2. **Detection Jobs Failing**
   - Check provider API tokens
   - Verify repository URLs are accessible
   - Check logs for specific error messages

3. **High Memory Usage**
   - Reduce `MAX_CONCURRENT_JOBS`
   - Increase OpenSearch heap size
   - Monitor job cleanup

### Logs

The API uses structured logging. Key log levels:
- `INFO`: General application events
- `DEBUG`: Detailed debugging information
- `ERROR`: Error conditions and exceptions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details. 