# Multi-Tenancy Support

Metagit now supports multi-tenancy, allowing you to isolate data and operations for different tenants (organizations, teams, or customers) within a single deployment.

## Overview

Multi-tenancy in Metagit provides:

- **Data Isolation**: Each tenant's records are completely isolated from other tenants
- **Access Control**: Tenants can only access their own data
- **Configurable**: Can be enabled/disabled via configuration
- **Backward Compatible**: Existing functionality remains unchanged when disabled
- **Flexible**: Supports both header-based and query parameter-based tenant identification

## Configuration

### Enable Multi-Tenancy

To enable multi-tenancy, update your `metagit.config.yaml`:

```yaml
config:
  version: "1.0.0"
  
  # Tenant configuration
  tenant:
    enabled: true
    default_tenant: "default"
    tenant_header: "X-Tenant-ID"
    tenant_required: true
    allowed_tenants:
      - "tenant-a"
      - "tenant-b"
      - "tenant-c"
      - "default"
  
  # ... rest of your configuration
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Whether multi-tenancy is enabled |
| `default_tenant` | string | `"default"` | Default tenant ID when none specified |
| `tenant_header` | string | `"X-Tenant-ID"` | HTTP header name for tenant ID |
| `tenant_required` | boolean | `true` | Whether tenant ID is required |
| `allowed_tenants` | list | `[]` | List of allowed tenant IDs (empty = all allowed) |

### Environment Variables

You can also configure multi-tenancy via environment variables:

```bash
# Enable multi-tenancy
export METAGIT_TENANT_ENABLED=true

# Set default tenant
export METAGIT_TENANT_DEFAULT=my-tenant

# Custom header name
export METAGIT_TENANT_HEADER=X-Custom-Tenant

# Make tenant optional
export METAGIT_TENANT_REQUIRED=false

# Allowed tenants (comma-separated)
export METAGIT_TENANT_ALLOWED=tenant-a,tenant-b,tenant-c
```

## Usage

### API Requests

When multi-tenancy is enabled, you must include a tenant identifier in your API requests.

#### Using HTTP Headers (Recommended)

```bash
# Submit detection for specific tenant
curl -X POST "http://localhost:8000/detect/submit" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-a" \
  -d '{
    "repository_url": "https://github.com/example/repo"
  }'

# Search records for specific tenant
curl -X POST "http://localhost:8000/records/search" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-a" \
  -d '{
    "query": "test"
  }'
```

#### Using Query Parameters

```bash
# Submit detection with tenant in query parameter
curl -X POST "http://localhost:8000/detect/submit?tenant_id=tenant-a" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/example/repo"
  }'

# Search records with tenant in query parameter
curl -X POST "http://localhost:8000/records/search?tenant_id=tenant-a" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test"
  }'
```

### Request Models

You can also include tenant information in request models:

```python
from metagit.api.models import DetectionRequest

# Include tenant in request
request = DetectionRequest(
    repository_url="https://github.com/example/repo",
    tenant_id="tenant-a",
    priority=1,
    metadata={"source": "api"}
)
```

### Python Client Example

```python
import requests

# Configure client with tenant
class MetagitClient:
    def __init__(self, base_url, tenant_id):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": tenant_id
        }
    
    def submit_detection(self, repository_url):
        response = requests.post(
            f"{self.base_url}/detect/submit",
            headers=self.headers,
            json={"repository_url": repository_url}
        )
        return response.json()
    
    def search_records(self, query):
        response = requests.post(
            f"{self.base_url}/records/search",
            headers=self.headers,
            json={"query": query}
        )
        return response.json()

# Usage
client = MetagitClient("http://localhost:8000", "tenant-a")
result = client.submit_detection("https://github.com/example/repo")
```

## Data Isolation

### OpenSearch Records

When multi-tenancy is enabled, all MetagitRecord entries include a `tenant_id` field:

```json
{
  "_id": "record-123",
  "_source": {
    "tenant_id": "tenant-a",
    "name": "example-repo",
    "url": "https://github.com/example/repo",
    "kind": "repository",
    "@timestamp": "2024-01-01T00:00:00Z",
    // ... other fields
  }
}
```

### Detection Jobs

Detection jobs are also tenant-aware:

```python
# Each detection job includes tenant context
{
  "detection_id": "job-123",
  "repository_url": "https://github.com/example/repo",
  "tenant_id": "tenant-a",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

## Security Features

### Tenant Validation

- **Required Tenants**: When `tenant_required=true`, requests without tenant ID are rejected
- **Allowed Tenants**: When `allowed_tenants` is configured, only listed tenants are accepted
- **Access Control**: Tenants can only access their own data

### Error Responses

```json
// Missing tenant ID
{
  "detail": "Tenant ID required. Use header 'X-Tenant-ID' or query parameter 'tenant_id'"
}

// Unauthorized tenant
{
  "detail": "Tenant 'unauthorized-tenant' not authorized. Allowed tenants: tenant-a, tenant-b, tenant-c"
}

// Access denied
{
  "detail": "Record record-123 not found or access denied"
}
```

## Migration

### From Single-Tenant to Multi-Tenant

1. **Backup your data** before enabling multi-tenancy
2. **Update configuration** to enable multi-tenancy
3. **Restart the service** - existing data will remain accessible via the default tenant
4. **Update clients** to include tenant headers/parameters

### Existing Data

- Existing records will be accessible via the `default` tenant
- No data migration is required
- The `tenant_id` field will be automatically added to new records

## Best Practices

### Tenant Naming

- Use consistent, descriptive tenant names
- Avoid special characters in tenant IDs
- Consider using UUIDs for tenant IDs in production

### Security

- Always validate tenant IDs on the client side
- Use HTTPS in production
- Consider implementing additional authentication/authorization
- Regularly audit tenant access

### Performance

- Tenant filtering is handled at the database level
- No performance impact for single-tenant deployments
- Consider index optimization for large multi-tenant deployments

### Monitoring

```python
# Monitor tenant usage
import logging

logger = logging.getLogger(__name__)

def log_tenant_access(tenant_id, operation):
    logger.info(f"Tenant {tenant_id} performed {operation}")
```

## Troubleshooting

### Common Issues

1. **403 Forbidden**: Check if tenant is in `allowed_tenants` list
2. **400 Bad Request**: Ensure tenant ID is provided when required
3. **404 Not Found**: Verify tenant has access to the requested resource

### Debugging

Enable debug logging to see tenant context:

```bash
export LOG_LEVEL=DEBUG
```

### Testing

Use the provided test suite to verify multi-tenant functionality:

```bash
pytest tests/test_tenant_config.py
pytest tests/test_tenant_middleware.py
pytest tests/test_tenant_services.py
```

## API Reference

### Endpoints

All existing endpoints support multi-tenancy when enabled:

- `POST /detect/submit` - Submit detection with tenant context
- `GET /detect/{detection_id}/status` - Get detection status (tenant-verified)
- `GET /detect` - List detections for current tenant
- `POST /records/search` - Search records with tenant filtering
- `GET /records/{record_id}` - Get record (tenant-verified)
- `DELETE /records/{record_id}` - Delete record (tenant-verified)

### Headers

- `X-Tenant-ID`: Tenant identifier (configurable name)
- `Content-Type`: `application/json`

### Query Parameters

- `tenant_id`: Alternative way to specify tenant identifier

## Examples

See `examples/tenant_config_example.yml` for a complete configuration example. 