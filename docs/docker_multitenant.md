# Multi-Tenant Docker Deployment

This guide explains how to deploy Metagit with multi-tenancy support using Docker Compose.

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- Git repository cloned
- Optional: GitHub/GitLab tokens for enhanced functionality

### 2. Environment Setup

Create a `.env` file in the project root (optional):

```bash
# Provider tokens (optional)
GITHUB_TOKEN=your_github_token_here
GITLAB_TOKEN=your_gitlab_token_here

# Custom configuration (optional)
OPENSEARCH_HOST=opensearch
OPENSEARCH_PORT=9200
OPENSEARCH_INDEX=metagit-records
```

### 3. Start the Multi-Tenant Deployment

```bash
# Start all services
docker-compose -f docker-compose.multitenant.yml up -d

# View logs
docker-compose -f docker-compose.multitenant.yml logs -f

# Stop services
docker-compose -f docker-compose.multitenant.yml down
```

## Services Overview

### Core Services

| Service | Port | Description |
|---------|------|-------------|
| `opensearch` | 9200 | OpenSearch database for storing records |
| `opensearch-dashboards` | 5601 | Web interface for OpenSearch data visualization |
| `metagit-api` | 8000 | Metagit API with multi-tenancy enabled |
| `metagit-web` | 8080 | Web interface for testing the API |

### Testing Services

| Service | Description |
|---------|-------------|
| `metagit-client` | Automated test client that validates multi-tenant functionality |

## Access Points

### API Endpoints

- **API Base URL**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

### Web Interfaces

- **API Tester**: `http://localhost:8080` - Interactive web interface for testing
- **OpenSearch Dashboards**: `http://localhost:5601` - Data visualization and management

## Multi-Tenant Configuration

The deployment is pre-configured with the following tenant settings:

```yaml
# Allowed tenants
- tenant-a
- tenant-b  
- tenant-c
- default

# Configuration
- Tenant header: X-Tenant-ID
- Tenant required: true
- Default tenant: default
```

## Testing Multi-Tenancy

### 1. Using the Web Interface

1. Open `http://localhost:8080` in your browser
2. Select a tenant from the dropdown
3. Test various API endpoints
4. Try unauthorized tenants to see access control in action

### 2. Using curl

```bash
# Submit detection for tenant-a
curl -X POST "http://localhost:8000/detect/submit" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-a" \
  -d '{
    "repository_url": "https://github.com/octocat/Hello-World"
  }'

# Search records for tenant-b
curl -X POST "http://localhost:8000/records/search" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-b" \
  -d '{
    "query": "test"
  }'

# Try unauthorized tenant (should fail)
curl -X POST "http://localhost:8000/detect/submit" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: unauthorized-tenant" \
  -d '{
    "repository_url": "https://github.com/octocat/test"
  }'
```

### 3. Automated Testing

The `metagit-client` service automatically runs tests:

```bash
# View test results
docker-compose -f docker-compose.multitenant.yml logs metagit-client
```

## Data Isolation

### OpenSearch Records

Each record includes a `tenant_id` field:

```json
{
  "_id": "record-123",
  "_source": {
    "tenant_id": "tenant-a",
    "name": "example-repo",
    "url": "https://github.com/example/repo",
    "kind": "repository"
  }
}
```

### Detection Jobs

Jobs are tenant-aware and isolated:

```json
{
  "detection_id": "job-123",
  "repository_url": "https://github.com/example/repo",
  "tenant_id": "tenant-a",
  "status": "pending"
}
```

## Monitoring and Debugging

### Health Checks

All services include health checks:

```bash
# Check service health
docker-compose -f docker-compose.multitenant.yml ps

# View health check logs
docker-compose -f docker-compose.multitenant.yml logs --tail=50
```

### OpenSearch Dashboards

1. Open `http://localhost:5601`
2. Navigate to "Discover"
3. Select the `metagit-records` index
4. Filter by `tenant_id` to see tenant-specific data

### API Logs

```bash
# View API logs
docker-compose -f docker-compose.multitenant.yml logs -f metagit-api

# View specific tenant requests
docker-compose -f docker-compose.multitenant.yml logs metagit-api | grep "tenant-a"
```

## Customization

### Adding New Tenants

1. Update the environment variable in `docker-compose.multitenant.yml`:

```yaml
environment:
  - METAGIT_TENANT_ALLOWED=tenant-a,tenant-b,tenant-c,tenant-d,default
```

2. Restart the API service:

```bash
docker-compose -f docker-compose.multitenant.yml restart metagit-api
```

### Changing Tenant Configuration

Modify the environment variables in `docker-compose.multitenant.yml`:

```yaml
environment:
  # Make tenant optional
  - METAGIT_TENANT_REQUIRED=false
  
  # Change default tenant
  - METAGIT_TENANT_DEFAULT=my-default-tenant
  
  # Custom header name
  - METAGIT_TENANT_HEADER=X-Custom-Tenant
```

### Scaling

To scale the API service:

```bash
# Scale to 3 instances
docker-compose -f docker-compose.multitenant.yml up -d --scale metagit-api=3
```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   docker-compose -f docker-compose.multitenant.yml logs
   
   # Check disk space
   df -h
   ```

2. **OpenSearch connection issues**
   ```bash
   # Wait for OpenSearch to be ready
   docker-compose -f docker-compose.multitenant.yml logs opensearch
   
   # Check OpenSearch health
   curl http://localhost:9200/_cluster/health
   ```

3. **Tenant access denied**
   - Verify tenant is in `METAGIT_TENANT_ALLOWED` list
   - Check tenant header format
   - Ensure `METAGIT_TENANT_REQUIRED=true` if tenant is required

4. **Data not appearing**
   - Check OpenSearch Dashboards at `http://localhost:5601`
   - Verify tenant filtering in queries
   - Check API logs for errors

### Performance Tuning

1. **Increase OpenSearch memory**:
   ```yaml
   environment:
     - "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g"
   ```

2. **Adjust API concurrency**:
   ```yaml
   environment:
     - MAX_CONCURRENT_JOBS=10
   ```

3. **Enable API debugging**:
   ```yaml
   environment:
     - API_DEBUG=true
     - LOG_LEVEL=DEBUG
   ```

## Security Considerations

### Production Deployment

1. **Enable OpenSearch Security**:
   ```yaml
   environment:
     - DISABLE_SECURITY_PLUGIN=false
   ```

2. **Use HTTPS**:
   - Configure SSL certificates
   - Update API base URLs

3. **Network Security**:
   - Use internal networks only
   - Configure firewalls
   - Implement proper authentication

4. **Data Backup**:
   ```bash
   # Backup OpenSearch data
   docker run --rm -v opensearch-mt-data:/data -v $(pwd):/backup alpine tar czf /backup/opensearch-backup.tar.gz -C /data .
   ```

## Cleanup

### Remove All Data

```bash
# Stop and remove containers
docker-compose -f docker-compose.multitenant.yml down

# Remove volumes (WARNING: This deletes all data)
docker-compose -f docker-compose.multitenant.yml down -v

# Remove images
docker-compose -f docker-compose.multitenant.yml down --rmi all
```

### Preserve Data

```bash
# Stop services but keep data
docker-compose -f docker-compose.multitenant.yml down

# Data is preserved in the `opensearch-mt-data` volume
```

## Next Steps

1. **Customize Configuration**: Modify `examples/tenant_config_example.yml`
2. **Add Authentication**: Implement proper auth for production
3. **Monitor Performance**: Set up monitoring and alerting
4. **Scale Deployment**: Add load balancers and multiple instances
5. **Backup Strategy**: Implement automated backups

For more information, see the [Multi-Tenancy Documentation](multi_tenancy.md). 