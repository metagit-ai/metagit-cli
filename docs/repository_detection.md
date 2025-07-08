# Repository Detection

The repository detection module provides comprehensive analysis of git repositories, including language detection, project classification, branch analysis, CI/CD detection, and metrics collection.

## Features

- **Language Detection**: Identifies primary and secondary programming languages, frameworks, and build tools
- **Project Classification**: Determines project type (application, library, CLI, etc.) and domain
- **Branch Analysis**: Detects branching strategies and analyzes branch patterns
- **CI/CD Detection**: Identifies CI/CD configurations and platforms
- **Metrics Collection**: Gathers repository metrics including stars, forks, issues, and contributor information
- **Git Provider Integration**: Supports real-time metrics from GitHub and GitLab APIs
- **AppConfig Integration**: Dynamic provider configuration through application settings

## Usage

### Basic Repository Analysis

```python
from metagit.core.detect import DetectionManager

# Analyze a local repository
analysis = DetectionManager.from_path("/path/to/repo")

# Analyze a remote repository (clones it temporarily)
analysis = DetectionManager.from_url("https://github.com/username/repo")

# Generate summary
summary = analysis.summary()
print(summary)

# Convert to MetagitConfig
config = analysis.to_metagit_config()
```

### CLI Usage

```bash
# Analyze current directory
metagit detect repository

# Analyze specific path
metagit detect repository --path /path/to/repo

# Analyze remote repository
metagit detect repository --url https://github.com/username/repo

# Save configuration to .metagit.yml
metagit detect repository --save

# Output in different formats
metagit detect repository --output yaml
metagit detect repository --output json
```

## Git Provider Plugins

The repository detection system supports git provider plugins that enable fetching real-time metrics from hosting platforms like GitHub and GitLab.

### Supported Providers

- **GitHub**: Fetches stars, forks, issues, pull requests, and contributor data
- **GitLab**: Fetches project statistics, merge requests, and member information

### Configuration Methods

#### 1. AppConfig (Recommended)

Configure providers through the application configuration file:

```yaml
# ~/.config/metagit/config.yml or metagit.config.yml
config:
  providers:
    github:
      enabled: true
      api_token: "ghp_your_github_token_here"
      base_url: "https://api.github.com"  # For GitHub Enterprise
    
    gitlab:
      enabled: false
      api_token: "glpat_your_gitlab_token_here"
      base_url: "https://gitlab.com/api/v4"  # For self-hosted GitLab
```

**Benefits:**
- Persistent configuration across sessions
- No need to set environment variables
- Easy to manage multiple environments
- Supports enterprise instances

#### 2. Environment Variables

Set API tokens as environment variables:

```bash
export GITHUB_TOKEN="your_github_personal_access_token"
export GITLAB_TOKEN="your_gitlab_personal_access_token"
```

#### 3. CLI Options

Override configuration for specific commands:

```bash
# Use GitHub token
metagit detect repository --github-token "your_token"

# Use GitLab token
metagit detect repository --gitlab-token "your_token"

# Custom API URLs (for self-hosted instances)
metagit detect repository --github-url "https://github.company.com/api/v3"
metagit detect repository --gitlab-url "https://gitlab.company.com/api/v4"

# Disable AppConfig and use environment variables only
metagit detect repository --use-app-config=false
```

### Configuration Priority

The system uses the following priority order for provider configuration:

1. **CLI Options** (highest priority) - Override all other settings
2. **AppConfig** - Persistent configuration from config files
3. **Environment Variables** - Fallback for legacy support

### Provider Features

#### GitHub Provider

- **Authentication**: Personal Access Token
- **Metrics**: Stars, forks, open issues, pull requests, contributors
- **Metadata**: Repository description, topics, creation date, license
- **URL Support**: github.com, GitHub Enterprise
- **Configuration**: `providers.github.enabled`, `providers.github.api_token`, `providers.github.base_url`

#### GitLab Provider

- **Authentication**: Personal Access Token
- **Metrics**: Star count, forks, open issues, merge requests, members
- **Metadata**: Project description, topics, visibility, namespace
- **URL Support**: gitlab.com, self-hosted GitLab
- **Configuration**: `providers.gitlab.enabled`, `providers.gitlab.api_token`, `providers.gitlab.base_url`

### Fallback Behavior

When no provider is available or API calls fail, the system falls back to git-based metrics:

- **Contributors**: Counted from git commit history
- **Commit Frequency**: Calculated from recent commit patterns
- **Stars/Forks/Issues**: Set to 0 (requires API access)

## Detection Components

### Language Detection

Analyzes file extensions and content to identify:

- **Primary Language**: Most dominant programming language
- **Secondary Languages**: Other languages present
- **Frameworks**: React, Vue, Angular, Terraform, Kubernetes, etc.
- **Package Managers**: npm, pip, cargo, go.mod, etc.
- **Build Tools**: Make, Gradle, Maven, etc.

### Project Type Detection

Classifies projects based on file patterns:

- **Application**: Web apps, mobile apps, desktop apps
- **Library**: Reusable code libraries
- **CLI**: Command-line tools
- **Microservice**: Containerized services
- **Data Science**: ML/AI projects with notebooks
- **Infrastructure as Code**: Terraform, CloudFormation, etc.

### Branch Analysis

Detects branching strategies:

- **Git Flow**: Feature, develop, release, hotfix branches
- **GitHub Flow**: Simple main branch with feature branches
- **GitLab Flow**: Environment-based branching
- **Trunk-Based Development**: Single main branch
- **Custom**: Other branching patterns

### CI/CD Detection

Identifies CI/CD configurations:

- **GitHub Actions**: `.github/workflows/`
- **GitLab CI**: `.gitlab-ci.yml`
- **CircleCI**: `.circleci/config.yml`
- **Jenkins**: `Jenkinsfile`
- **Travis CI**: `.travis.yml`

### Metrics Collection

Gathers repository statistics:

- **Stars**: Repository stars/watches
- **Forks**: Repository forks
- **Open Issues**: Number of open issues
- **Pull Requests**: Open and recently merged PRs
- **Contributors**: Number of contributors
- **Commit Frequency**: Daily, weekly, or monthly activity

## Output Formats

### Summary Output

Human-readable summary of all detected information:

```
Repository Analysis Summary
Path: /path/to/repo
URL: https://github.com/username/repo
Git Repository: True
Primary Language: Python
Secondary Languages: JavaScript, Shell
Frameworks: React, Terraform
Package Managers: pip, npm
Project Type: application
Domain: web
Confidence: 0.85
Branch Strategy: GitHub Flow
Number of Branches: 3
CI/CD Tool: GitHub Actions
Contributors: 5
Commit Frequency: weekly
Stars: 42
Forks: 12
Open Issues: 3
Open PRs: 1
PRs Merged (30d): 8
Metrics Source: GitHub API
Has Docker: True
Has Tests: True
Has Documentation: True
Has Infrastructure as Code: True
```

### YAML Output

Structured YAML configuration:

```yaml
name: "My Project"
description: "A sample project"
url: "https://github.com/username/repo"
kind: "application"
license:
  kind: "mit"
  file: "LICENSE"
maintainers:
  - name: "John Doe"
    email: "john@example.com"
    role: "Maintainer"
branch_strategy: "github_flow"
taskers:
  - kind: "taskfile"
branches:
  - name: "main"
  - name: "develop"
  - name: "feature/new-feature"
cicd:
  platform: "github"
  pipelines:
    - name: "CI"
      ref: ".github/workflows/ci.yml"
metrics:
  stars: 42
  forks: 12
  open_issues: 3
  pull_requests:
    open: 1
    merged_last_30d: 8
  contributors: 5
  commit_frequency: "weekly"
metadata:
  default_branch: "main"
  has_ci: true
  has_tests: true
  has_docs: true
  has_docker: true
  has_iac: true
  created_at: "2024-01-01T00:00:00"
  last_commit_at: "2024-01-15T12:00:00"
workspace:
  projects:
    - name: "default"
      repos:
        - name: "My Project"
          path: "/path/to/repo"
          url: "https://github.com/username/repo"
```

## Examples

### Basic Analysis

```python
from metagit.core.detect import DetectionManager

# Analyze current directory
analysis = DetectionManager.from_path(".")

# Print summary
print(analysis.summary())

# Get configuration
config = analysis.to_metagit_config()
```

### With AppConfig Integration

```python
from metagit.core.detect import DetectionManager
from metagit.core.appconfig import AppConfig
from metagit.core.providers import registry

# Load AppConfig and configure providers
app_config = AppConfig.load()
registry.configure_from_app_config(app_config)

# Analyze repository (will use configured providers for metrics)
analysis = DetectionManager.from_path(".")
print(analysis.summary())
```

### With Manual Provider Configuration

```python
from metagit.core.detect import DetectionManager
from metagit.core.providers.github import GitHubProvider
from metagit.core.providers import registry

# Setup GitHub provider manually
provider = GitHubProvider(api_token="ghp_...")
registry.register(provider)

# Analyze repository
analysis = DetectionManager.from_path(".")
print(analysis.summary())
```

### CLI with AppConfig

```bash
# Create AppConfig file
mkdir -p ~/.config/metagit
cat > ~/.config/metagit/config.yml << EOF
config:
  providers:
    github:
      enabled: true
      api_token: "ghp_..."
    gitlab:
      enabled: false
      api_token: ""
EOF

# Analyze with AppConfig providers
metagit detect repository --path /path/to/repo --output summary

# Save configuration with real metrics
metagit detect repository --path /path/to/repo --save
```

### CLI with Environment Variables

```bash
# Set environment variables
export GITHUB_TOKEN="ghp_..."
export GITLAB_TOKEN="glpat-..."

# Analyze with environment providers
metagit detect repository --path /path/to/repo --output summary

# Disable AppConfig and use environment only
metagit detect repository --use-app-config=false --path /path/to/repo
```

## Error Handling

The detection system gracefully handles errors:

- **Missing Files**: Skips analysis of missing files/directories
- **API Failures**: Falls back to git-based metrics
- **Invalid Repositories**: Returns appropriate error messages
- **Network Issues**: Continues with local analysis
- **Configuration Errors**: Falls back to environment variables or defaults

## Performance Considerations

- **Local Analysis**: Fast, no network required
- **Provider API Calls**: May add 1-3 seconds for metrics
- **Large Repositories**: Analysis time scales with repository size
- **Caching**: No built-in caching (consider implementing for repeated analysis)
- **Configuration Loading**: AppConfig is loaded once per command execution 