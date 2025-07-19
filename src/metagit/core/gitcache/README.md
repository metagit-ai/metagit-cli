# Git Cache Management System

The Git Cache Management System provides a comprehensive solution for caching git repositories and local directories with support for both synchronous and asynchronous operations.

## Features

- **Dual Operation Modes**: Support for both synchronous and asynchronous operations
- **Multiple Source Types**: Cache both git repositories and local directories
- **Provider Integration**: Use existing git provider configurations for authentication
- **Smart Caching**: Check for existing cache and pull updates for git repositories
- **Local Directory Support**: Full directory copying for local sources
- **Cache Management**: List, remove, and refresh cache entries
- **Timeout Management**: Configurable cache timeout with automatic stale detection
- **Size Management**: Track and limit cache size
- **Error Handling**: Comprehensive error handling with detailed status tracking

## Architecture

### Core Components

1. **GitCacheConfig**: Central configuration management using Pydantic models
2. **GitCacheEntry**: Individual cache entry representation
3. **GitCacheManager**: Main manager class handling all cache operations

### File Structure

```
metagit/core/gitcache/
├── __init__.py          # Module exports
├── config.py           # Configuration models
├── manager.py          # Main cache manager
└── README.md           # This file
```

## Usage

### Basic Setup

```python
from metagit.core.gitcache import GitCacheConfig, GitCacheManager
from pathlib import Path

# Create configuration
config = GitCacheConfig(
    cache_root=Path("./.metagit/.cache"),
    default_timeout_minutes=60,
    max_cache_size_gb=10.0
)

# Create manager
manager = GitCacheManager(config)
```

### Caching Git Repositories

```python
# Cache a git repository
entry = manager.cache_repository("https://github.com/octocat/Hello-World.git")

if isinstance(entry, Exception):
    print(f"Error: {entry}")
else:
    print(f"Cached: {entry.name}")
    print(f"Path: {entry.cache_path}")
    print(f"Status: {entry.status}")
```

### Caching Local Directories

```python
# Cache a local directory
entry = manager.cache_repository("/path/to/local/project", name="my-project")

if isinstance(entry, Exception):
    print(f"Error: {entry}")
else:
    print(f"Cached: {entry.name}")
    print(f"Type: {entry.cache_type}")
```

### Asynchronous Operations

```python
import asyncio

async def cache_multiple_repos():
    # Cache multiple repositories concurrently
    tasks = [
        manager.cache_repository_async("https://github.com/user/repo1.git"),
        manager.cache_repository_async("https://github.com/user/repo2.git"),
        manager.cache_repository_async("/path/to/local/project")
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"Error: {result}")
        else:
            print(f"Successfully cached: {result.name}")

# Run async function
asyncio.run(cache_multiple_repos())
```

### Cache Management

```python
# List all cache entries
entries = manager.list_cache_entries()
for entry in entries:
    print(f"{entry.name}: {entry.cache_type} ({entry.status})")

# Get cache statistics
stats = manager.get_cache_stats()
print(f"Total entries: {stats['total_entries']}")
print(f"Total size: {stats['total_size_gb']:.2f} GB")

# Get cached repository path
cache_path = manager.get_cached_repository("repo-name")
if isinstance(cache_path, Exception):
    print(f"Error: {cache_path}")
else:
    print(f"Cache path: {cache_path}")

# Refresh cache entry
entry = manager.refresh_cache_entry("repo-name")

# Remove cache entry
result = manager.remove_cache_entry("repo-name")

# Clear all cache
result = manager.clear_cache()
```

### Provider Integration

```python
from metagit.core.providers.github import GitHubProvider

# Register a git provider
provider = GitHubProvider(api_token="your-token")
manager.register_provider(provider)

# The manager will use the provider for authentication when cloning
entry = manager.cache_repository("https://github.com/private/repo.git")
```

## Configuration

### GitCacheConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `cache_root` | Path | `./.metagit/.cache` | Root directory for cache storage |
| `default_timeout_minutes` | int | 60 | Default cache timeout in minutes |
| `max_cache_size_gb` | float | 10.0 | Maximum cache size in GB |
| `enable_async` | bool | True | Enable async operations |
| `git_config` | Dict | {} | Git configuration options |
| `provider_config` | Dict | None | Provider-specific configuration |

### Git Configuration

```python
config = GitCacheConfig(
    git_config={
        "user.name": "Your Name",
        "user.email": "your.email@example.com",
        "http.extraheader": "AUTHORIZATION: basic <base64-encoded-token>"
    }
)
```

## Cache Entry Status

Cache entries have the following statuses:

- **FRESH**: Cache is up-to-date and within timeout
- **STALE**: Cache exists but is older than timeout
- **MISSING**: Cache entry exists but files are missing
- **ERROR**: Cache operation failed

## Error Handling

All operations return either the expected result or an Exception. This allows for comprehensive error handling:

```python
entry = manager.cache_repository("https://github.com/user/repo.git")

if isinstance(entry, Exception):
    # Handle error
    print(f"Cache failed: {entry}")
    # Check if it's a specific type of error
    if "Authentication failed" in str(entry):
        print("Please check your credentials")
    elif "Repository not found" in str(entry):
        print("Repository does not exist or is private")
else:
    # Handle success
    print(f"Successfully cached: {entry.name}")
```

## Best Practices

1. **Use Provider Configuration**: Register git providers for authentication
2. **Handle Errors Gracefully**: Always check return types for exceptions
3. **Monitor Cache Size**: Use `get_cache_stats()` to monitor cache usage
4. **Refresh Stale Cache**: Use `refresh_cache_entry()` for important repositories
5. **Clean Up Regularly**: Remove unused cache entries to save space
6. **Use Async for Multiple Operations**: Use async methods when caching multiple repositories

## Examples

See `examples/gitcache_example.py` for comprehensive usage examples including:

- Synchronous operations
- Asynchronous operations
- Cache management
- Error handling
- Provider integration

## Testing

Run the test suite:

```bash
python -m pytest tests/test_gitcache.py -v
```

The test suite covers:

- Configuration validation
- Cache entry management
- Repository cloning
- Local directory copying
- Async operations
- Error scenarios
- Cache statistics

## Integration

The Git Cache Management System integrates with:

- **Git Providers**: Use existing provider configurations for authentication
- **Project Management**: Cache repositories for analysis
- **CI/CD Pipelines**: Cache dependencies and tools
- **Development Workflows**: Local development with cached repositories 