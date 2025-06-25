# Per-Tenant Configuration System

Metagit now supports per-tenant AppConfigs, allowing each tenant to have their own configuration for providers, LLM settings, workspace settings, and custom configurations while maintaining the global system configuration.

## Overview

The per-tenant configuration system provides:

- **Isolated Configuration**: Each tenant can have their own provider tokens, LLM settings, and workspace configurations
- **Merged Configuration**: Tenant-specific settings are merged with global settings for a complete configuration
- **Dynamic Configuration**: Tenant configurations can be updated via API without restarting the service
- **Caching**: Configurations are cached for performance
- **Backward Compatibility**: Existing functionality remains unchanged

## Architecture

### Components

1. **TenantAppConfig**: Model for tenant-specific configuration
2. **TenantConfigManager**: Utility for loading/saving tenant configurations
3. **TenantConfigService**: Service layer for managing tenant configurations
4. **API Endpoints**: REST API for managing tenant configurations

### Configuration Hierarchy

```
Global AppConfig (metagit.config.yaml)
    ↓
Tenant-Specific Config (tenant-id.yml)
    ↓
Merged Configuration (used by services)
```

## Configuration Structure

### TenantAppConfig Model

```python
class TenantAppConfig(BaseModel):
    tenant_id: str                    # Tenant identifier
    name: str                         # Tenant display name
    description: str                  # Tenant description
    
    # Provider configuration
    providers: Providers              # Git provider settings
    
    # LLM configuration
    llm: LLM                         # LLM settings
    
    # Workspace configuration
    workspace: Workspace             # Workspace settings
    
    # Detection settings
    max_concurrent_jobs: int         # Max concurrent jobs
    detection_timeout: int           # Detection timeout
    
    # Custom settings
    settings: Dict[str, any]         # Custom tenant settings
    
    # Metadata
    created_at: Optional[str]        # Creation timestamp
    updated_at: Optional[str]        # Last update timestamp
    is_active: bool                  # Whether tenant is active
```

### Example Tenant Configuration

```yaml
tenant_config:
  tenant_id: "tenant-a"
  name: "Acme Corporation"
  description: "Acme Corporation's development team configuration"
  
  providers:
    github:
      enabled: true
      api_token: "${GITHUB_TOKEN_ACME}"
      base_url: "https://api.github.com"
    gitlab:
      enabled: false
      api_token: ""
      base_url: "https://gitlab.com/api/v4"
  
  llm:
    enabled: true
    provider: "openrouter"
    provider_model: "gpt-4o-mini"
    embedder: "ollama"
    embedder_model: "nomic-embed-text"
    api_key: "${OPENROUTER_API_KEY_ACME}"
  
  workspace:
    path: "./.metagit-acme"
    default_project: "acme-main"
  
  max_concurrent_jobs: 10
  detection_timeout: 600
  
  settings:
    organization_name: "Acme Corporation"
    team_id: "dev-team-1"
    allowed_repositories:
      - "acme/*"
      - "acme-dev/*"
    notification_email: "dev-team@acme.com"
    auto_scan_enabled: true
    scan_frequency: "daily"
  
  created_at: "2024-01-15T10:00:00Z"
  updated_at: "2024-01-15T10:00:00Z"
  is_active: true
```

## API Endpoints

### Tenant Configuration Management

#### Get Tenant Configuration
```http
GET /tenant-config/
X-Tenant-ID: tenant-a
```

Response:
```json
{
  "tenant_id": "tenant-a",
  "name": "Acme Corporation",
  "description": "Acme Corporation's development team configuration",
  "providers": {
    "github": {
      "enabled": true,
      "api_token": "***",
      "base_url": "https://api.github.com"
    },
    "gitlab": {
      "enabled": false,
      "api_token": "",
      "base_url": "https://gitlab.com/api/v4"
    }
  },
  "llm": {
    "enabled": true,
    "provider": "openrouter",
    "provider_model": "gpt-4o-mini",
    "embedder": "ollama",
    "embedder_model": "nomic-embed-text",
    "api_key": "***"
  },
  "workspace": {
    "path": "./.metagit-acme",
    "default_project": "acme-main"
  },
  "max_concurrent_jobs": 10,
  "detection_timeout": 600,
  "settings": {
    "organization_name": "Acme Corporation",
    "team_id": "dev-team-1",
    "allowed_repositories": ["acme/*", "acme-dev/*"],
    "notification_email": "dev-team@acme.com",
    "auto_scan_enabled": true,
    "scan_frequency": "daily"
  },
  "is_active": true
}
```

#### Update Tenant Configuration
```http
PUT /tenant-config/
X-Tenant-ID: tenant-a
Content-Type: application/json

{
  "name": "Updated Acme Corporation",
  "max_concurrent_jobs": 15,
  "settings": {
    "scan_frequency": "hourly"
  }
}
```

#### Get Tenant Providers
```http
GET /tenant-config/providers
X-Tenant-ID: tenant-a
```

#### Get Tenant LLM Configuration
```http
GET /tenant-config/llm
X-Tenant-ID: tenant-a
```

#### Get Tenant Settings
```http
GET /tenant-config/settings
X-Tenant-ID: tenant-a
```

#### Update Tenant Setting
```http
PUT /tenant-config/settings/scan_frequency
X-Tenant-ID: tenant-a
Content-Type: application/json

{
  "key": "scan_frequency",
  "value": "hourly"
}
```

#### Get Merged Configuration
```http
GET /tenant-config/merged
X-Tenant-ID: tenant-a
```

### Admin Endpoints

#### List All Tenant Configurations
```http
GET /tenant-config/admin/list
X-Tenant-ID: default
```

#### Create New Tenant Configuration
```http
POST /tenant-config/admin/create/new-tenant-id
X-Tenant-ID: default
Content-Type: application/json

{
  "name": "New Tenant",
  "description": "New tenant configuration",
  "max_concurrent_jobs": 5
}
```

#### Delete Tenant Configuration
```http
DELETE /tenant-config/admin/tenant-id-to-delete
X-Tenant-ID: default
```

## Usage Examples

### Python Client Example

```python
import requests

# Get tenant configuration
response = requests.get(
    "http://localhost:8000/tenant-config/",
    headers={"X-Tenant-ID": "tenant-a"}
)
config = response.json()

# Update tenant configuration
update_data = {
    "max_concurrent_jobs": 20,
    "settings": {
        "auto_scan_enabled": False
    }
}
response = requests.put(
    "http://localhost:8000/tenant-config/",
    headers={"X-Tenant-ID": "tenant-a"},
    json=update_data
)

# Get merged configuration
response = requests.get(
    "http://localhost:8000/tenant-config/merged",
    headers={"X-Tenant-ID": "tenant-a"}
)
merged_config = response.json()
```

### cURL Examples

```bash
# Get tenant configuration
curl -X GET "http://localhost:8000/tenant-config/" \
  -H "X-Tenant-ID: tenant-a"

# Update tenant configuration
curl -X PUT "http://localhost:8000/tenant-config/" \
  -H "X-Tenant-ID: tenant-a" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Tenant",
    "max_concurrent_jobs": 15
  }'

# Get merged configuration
curl -X GET "http://localhost:8000/tenant-config/merged" \
  -H "X-Tenant-ID: tenant-a"
```

## Configuration File Locations

### Default Locations

- **Global Config**: `~/.config/metagit/config.yml`
- **Tenant Configs**: `~/.config/metagit/tenants/{tenant-id}.yml`

### Custom Locations

You can customize the tenant configuration directory by setting the `config_dir` in the global AppConfig:

```yaml
config:
  tenant_config_manager:
    config_dir: "/custom/path/to/tenant/configs"
```

## Environment Variables

### Tenant-Specific Environment Variables

You can use environment variables in tenant configurations:

```yaml
tenant_config:
  providers:
    github:
      api_token: "${GITHUB_TOKEN_TENANT_A}"
  llm:
    api_key: "${OPENROUTER_API_KEY_TENANT_A}"
```

### Global Environment Variables

Global environment variables still apply and can be overridden by tenant-specific settings.

## Best Practices

### Security

1. **Secure Storage**: Store sensitive tokens in environment variables
2. **Access Control**: Use proper authentication/authorization for admin endpoints
3. **Audit Logging**: Log configuration changes for audit purposes
4. **Token Rotation**: Regularly rotate API tokens

### Performance

1. **Caching**: Configurations are cached for performance
2. **Lazy Loading**: Configurations are loaded on-demand
3. **Cache Invalidation**: Clear cache when configurations are updated

### Management

1. **Version Control**: Keep tenant configurations in version control
2. **Backup**: Regularly backup tenant configurations
3. **Documentation**: Document tenant-specific settings and their purposes
4. **Testing**: Test configuration changes in a staging environment

## Migration Guide

### From Single-Tenant to Multi-Tenant

1. **Enable Multi-Tenancy**: Update global configuration to enable multi-tenancy
2. **Create Default Tenant**: Create a default tenant configuration
3. **Migrate Existing Data**: Existing data will be accessible via the default tenant
4. **Create Tenant Configurations**: Create configurations for each tenant
5. **Update Clients**: Update client applications to include tenant headers

### Example Migration Script

```python
from metagit.api.tenant_config import TenantConfigService
from metagit.core.appconfig.models import AppConfig

# Load global config
global_config = AppConfig.load("metagit.config.yaml")

# Initialize tenant config service
tenant_service = TenantConfigService(global_config)

# Create default tenant config from existing global config
default_config = tenant_service.create_tenant_config(
    "default",
    name="Default Tenant",
    description="Default tenant configuration",
    providers=global_config.providers,
    llm=global_config.llm,
    workspace=global_config.workspace
)

print(f"Created default tenant configuration: {default_config.tenant_id}")
```

## Troubleshooting

### Common Issues

1. **Configuration Not Found**: Ensure tenant configuration file exists in the correct location
2. **Permission Denied**: Check file permissions for tenant configuration directory
3. **Invalid Configuration**: Validate YAML syntax and required fields
4. **Cache Issues**: Clear configuration cache if changes are not reflected

### Debug Commands

```bash
# List all tenant configurations
curl -X GET "http://localhost:8000/tenant-config/admin/list" \
  -H "X-Tenant-ID: default"

# Get merged configuration for debugging
curl -X GET "http://localhost:8000/tenant-config/merged" \
  -H "X-Tenant-ID: tenant-a"

# Check tenant configuration file
ls -la ~/.config/metagit/tenants/
cat ~/.config/metagit/tenants/tenant-a.yml
```

### Logging

Enable debug logging to see configuration loading details:

```bash
export LOG_LEVEL=DEBUG
```

## Future Enhancements

1. **Configuration Validation**: Add schema validation for tenant configurations
2. **Configuration Templates**: Provide templates for common tenant types
3. **Configuration Import/Export**: Add bulk import/export functionality
4. **Configuration Versioning**: Add versioning support for configuration changes
5. **Configuration Inheritance**: Support configuration inheritance between tenants
6. **Configuration Monitoring**: Add monitoring and alerting for configuration changes 