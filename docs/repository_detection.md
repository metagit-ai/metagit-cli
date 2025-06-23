# Repository Detection Module

The `metagit.core.detect.repository` module provides comprehensive repository analysis capabilities for both local paths and remote git repositories. It automatically detects various aspects of a codebase and generates a complete `MetagitConfig` object.

## Features

### Language and Technology Detection
- **Programming Languages**: Detects primary and secondary programming languages
- **Frameworks**: Identifies frameworks like React, Vue, Angular, Terraform, Kubernetes
- **Package Managers**: Recognizes package manager files (requirements.txt, package.json, go.mod, etc.)
- **Build Tools**: Detects build systems and tools

### Project Type Classification
- **Application Types**: CLI, Library, Microservice, Web Application, Data Science
- **Domains**: Web, Mobile, DevOps, ML, Security, etc.
- **Confidence Scoring**: Provides confidence levels for type detection

### Repository Analysis
- **Git Integration**: Analyzes git repositories for branches, strategies, and metadata
- **CI/CD Detection**: Identifies CI/CD tools and configurations
- **File Structure**: Categorizes files by type (testing, documentation, infrastructure, etc.)
- **Metadata Extraction**: Extracts project name, description, license, and maintainers

### MetagitConfig Generation
- **Complete Configuration**: Generates fully populated `MetagitConfig` objects
- **Workspace Setup**: Creates workspace configurations with project paths
- **Branch Strategy**: Maps detected git strategies to Metagit branch strategies
- **CI/CD Integration**: Converts detected CI/CD tools to Metagit CI/CD configurations

## Usage

### Basic Usage

```python
from metagit.core.detect.repository import RepositoryAnalysis

# Analyze a local repository
analysis = RepositoryAnalysis.from_path("./my-project")

# Analyze a remote repository
analysis = RepositoryAnalysis.from_url("https://github.com/user/repo.git")

# Generate MetagitConfig
config = analysis.to_metagit_config()

# Get analysis summary
summary = analysis.summary()
print(summary)
```

### CLI Usage

```bash
# Analyze current directory
metagit detect repository

# Analyze specific local path
metagit detect repository --path /path/to/repo

# Analyze remote repository
metagit detect repository --url https://github.com/user/repo.git

# Output as YAML
metagit detect repository --path /path/to/repo --output yaml

# Generate and save .metagit.yml
metagit detect repository --path /path/to/repo --output config
```

## API Reference

### RepositoryAnalysis Class

#### Class Methods

##### `from_path(path: str, logger: Optional[Any] = None) -> Union[RepositoryAnalysis, Exception]`
Analyze a local repository path.

**Parameters:**
- `path`: Local path to analyze
- `logger`: Logger instance (optional)

**Returns:**
- `RepositoryAnalysis` object or `Exception` if analysis fails

##### `from_url(url: str, logger: Optional[Any] = None, temp_dir: Optional[str] = None) -> Union[RepositoryAnalysis, Exception]`
Clone and analyze a repository from URL.

**Parameters:**
- `url`: Git repository URL
- `logger`: Logger instance (optional)
- `temp_dir`: Temporary directory for cloning (optional)

**Returns:**
- `RepositoryAnalysis` object or `Exception` if analysis fails

#### Instance Methods

##### `to_metagit_config() -> Union[MetagitConfig, Exception]`
Convert analysis results to a complete `MetagitConfig` object.

**Returns:**
- `MetagitConfig` object or `Exception` if conversion fails

##### `summary() -> Union[str, Exception]`
Generate a human-readable summary of the analysis.

**Returns:**
- Summary string or `Exception` if generation fails

##### `cleanup() -> None`
Clean up temporary resources (for cloned repositories).

## Detection Capabilities

### Language Detection
The module detects programming languages through:
- File extensions (.py, .js, .go, .rs, .java, etc.)
- Package manager files (requirements.txt, package.json, go.mod, etc.)
- Build configuration files

### Framework Detection
Frameworks are detected by:
- File content analysis
- Directory structure patterns
- Configuration file presence
- Import statements and dependencies

### Project Type Detection
Project types are determined by:
- Language and framework combinations
- File structure patterns
- Configuration files
- Directory naming conventions

### Git Analysis
For git repositories, the module analyzes:
- Branch structure and naming
- Git flow strategies
- Remote repository information
- Commit history and contributors

### CI/CD Detection
CI/CD tools are identified by:
- Configuration file presence (.github/workflows, .gitlab-ci.yml, etc.)
- Build tool configurations
- Deployment scripts

## Example Output

### Analysis Summary
```
Repository Analysis Summary
Path: /path/to/repo
Git Repository: True
Primary Language: Python
Secondary Languages: JavaScript, Shell
Frameworks: React, Terraform
Package Managers: requirements.txt, package.json
Project Type: application
Domain: web
Confidence: 0.85
Branch Strategy: GitHub Flow
Number of Branches: 3
CI/CD Tool: GitHub Actions
Has Docker: True
Has Tests: True
Has Documentation: True
Has Infrastructure as Code: True
```

### Generated MetagitConfig
The module generates a complete `MetagitConfig` object with:
- Project metadata (name, description, URL)
- Language and framework information
- Branch strategy and branch information
- CI/CD configuration
- Repository metadata (has tests, has docs, etc.)
- Workspace configuration with project paths

## Error Handling

The module uses a consistent error handling pattern:
- All methods return `Union[Result, Exception]`
- Exceptions are logged with appropriate context
- Temporary resources are cleaned up automatically
- Analysis continues even if some components fail

## Integration

The repository detection module integrates with:
- Existing `ProjectAnalysis` class
- CLI command structure
- Metagit configuration system
- Logging and error handling infrastructure

## Future Enhancements

Potential improvements include:
- More sophisticated language detection algorithms
- Machine learning-based project type classification
- Enhanced framework detection
- Support for more CI/CD platforms
- Repository metrics and analytics
- Dependency analysis and visualization 