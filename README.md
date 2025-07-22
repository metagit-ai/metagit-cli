# Metagit

Metagit is situational awareness for developers and agents. It can make a sprawling multi-repo project feel more like a monorepo and provide concise information on the software stacks, generated artifacts, dependencies, and more.

## About

This tool is well suited for a number of scenarios including;

1. At-a-glance view of a project's technical stacks, languages, external dependencies, and generated artifacts.
2. Rapid pivoting between numerous git projects throughout the day while still maintaining a steady clip of productivity.
3. Isolating outside dependencies that weaken the security and dependability of your software delivery pipelines.
4. Automated documentation of a code's provenance.
5. As a new contributor to a project or team, go from zero to first code commit in as little time as possible.

Metagit aims to provide situational awareness for developers, SREs, AI agents, and engineers on the git projects they work in every day. It is meant to shed light on the numerous interconnected dependencies that comprise the whole of the entire solution being worked on in a single easily read, updated, and version controlled file.

## Audience

This tool targets;

- DevOps Engineers
- Polyglot developers
- New team members
- Project Managers
- SREs
- Solution Engineers
- AI Agents (more to come!)

## Metagit is NOT...

### ...an SBOM Tool

SBOM output can be thousands of lines long and encompass all the software dependencies, their transitive dependencies, and more. This kind of data is too much for the simple need of situational awareness and AI integration. As such, a comprehensive SBOM report is overkill for the goals outlined above. The development roadmap may include the ability to read in SBOM manifests as a data source though!

Metagit makes extensive use of CI library definitions (like go.mod, packages.json, requirements.txt, et cetera) for detection and boundary validations. Such files will be used to help determine technology stacks in use but not extensive versioning or other deep information.

### ...a git Client

Despite the name this tool still requires git and all the trappings of a git hosting solution.

## How It Works

This app accesses and saves project configuration metadata within the repository as a `.metagit.yml` file. This file follows a schema that can be read via the cli.

If using this tool to manage several dozen git repos (aka. an umbrella repo) then everything within the configuration file can be manually updated. You can also attempt to automatically update the file using a mix of standard heuristics and AI driven workflows.

## Modes

This application will have multiple modes of operation as described below.

### Workspace Mode

This mode is the first planned release feature as an open source cli tool.

In this mode users stitch together various repositories that comprise the components of a project into one workspace that can be loaded via vscode or accessed individually via fast context switching at the console.

> **AKA** Multi-repo as Monorepo

In this mode you are using metagit as a means to externally track and work with multiple git projects as a whole. One top level 'umbrella' project has the only metagit definition file which contains definitions for all related git repos and local target folders in the current project. Optionally you then sync the project to your local workstation.

The metagit configuration file is then be checked into version control as a stand-alone project.

This mode is ideal for;

- Creating umbrella projects for new team members of a multi-repo project
- Individual power users that need to quickly pivot between several project repositories that comprise a larger team effort
- Keeping loosely coupled git projects grouped together to work on without having to deal with git submodules (yuk)

## Metadata Mode

This mode uses the same config file that workspace mode employs but with additional information about the project's primary language, frameworks, and other situational awareness information you always wish you had at hand when diving into a new project. This mode can be used in tandem with workspace mode.

To configure this metadata for a single project by hand would be easy. To do so for several dozen or even thousands of repos is a no small task. Towards that end, metagit will include detection heuristics to automate a good deal of this task. What cannot be done easily through code initially will be done with AI.

> **NOTE** This too will need to be actively monitored by other AI agents to convert into static code over time.

In this mode, metagit would be used to answer questions such as;

- What other projects are related to this project?
- What application and development stacks does this project use?
- What external dependencies exist for this project?
- What artifacts does this project create?
- What branch strategy is employed?
- What version strategy is employed?

> **External Dependencies** are the devil! If you ever experienced a pipeline that suddenly fails due to a missing outside/external dependency you know exactly why they stink.

## Metadata+ Mode

All the prior metadata is incredibly useful already. But if we add context around this then we are cooking with gas! If we setup basic organization boundaries like owned registries or github/gitlab groups we can then start looking for dangers such as outside dependencies.

## Enterprise (TBD)

Enterprise mode is using metagit at scale.

In this mode metagit connects to our enterprise SaaS offering to help mine the whole of your organization's code assets continuously.

- Imagine if you could mine your entire organization's copious amounts of code repos for the exact thing you need for your own project? 
- How many times do wheels get recreated simply because you cannot find the artifact needed for your own project even though you know it must exist? 
- How much time is wasted looking for a project using your language and framework to use as a starting point for your own efforts?
- How frustrated do you get when, after putting in days or weeks of effort to create something you find another internal project that does it twice as elegantly that was done 6 months ago by another team? Enterprise mode of metagit aims to target this issue head on.


## Installation

**uv:**

`uv tool install metagit-ai`

**From source:**
To install metagit, clone the repository and build the project:

```bash
git clone https://github.com/metagit-ai/metagit-cli.git
cd metagit-cli

./configure.sh
task build
uv tool install dist/metagit-*-py3-none-any.whl
```

**docker:**

```bash
# Pull the latest version
docker pull ghcr.io/metagit-ai/metagit-cli:latest

# Pull a specific version
docker pull ghcr.io/metagit-ai/metagit-cli:0.1.0

# Run the CLI
docker run --rm ghcr.io/metagit-ai/metagit-cli:latest --help
```
# Usage

## Quick Start

To get started with metagit, initialize a new configuration in your Git repository:

```bash
metagit init
```

This creates a `metagit.yaml` configuration file and updates your `.gitignore` file.

## Subcommands

### `init` - Initialize Repository
Initialize a new metagit configuration in your current Git repository:

```bash
metagit init
```

This command will:
- Check if the current directory is a Git repository
- Create a `metagit.yaml` configuration file if it doesn't exist
- Add `.metagit` to your `.gitignore` file

### `appconfig` - Application Configuration

Manage metagit's application-level configuration:

```bash
# Show current application configuration
metagit appconfig show

# Create default application config
metagit appconfig create

# Get a specific configuration value
metagit appconfig get <key>

# Validate configuration file
metagit appconfig validate

# Generate JSON schema for configuration
metagit appconfig schema

# Show configuration information
metagit appconfig info
```

### `config` - Project Configuration

Manage project-specific (local git project) metagit configuration:

```bash
# Show current project configuration
metagit config show

# Create new metagit config files
metagit config create

# Validate metagit configuration
metagit config validate

# Generate JSON schema for MetagitConfig
metagit config schema

# Display project configuration information
metagit config info

# Manage git provider plugins
metagit config providers
```

### `detect` - Repository Detection

Analyze and detect project characteristics:

```bash
# Basic repository detection
metagit detect repo

# Comprehensive repository analysis with MetagitConfig generation
metagit detect repository
```

The detection system analyzes your repository to automatically identify:
- Programming languages and frameworks
- Build tools and package managers
- CI/CD configurations
- Project structure and dependencies

### `project` - Project Management
Manage projects within workspaces:

```bash
# List current project configuration
metagit project list

# Select a project repository to work on
metagit project select

# Sync project within workspace
metagit project sync

# Repository-specific operations
metagit project repo <subcommand>
```

Options:
- `-c, --config`: Path to metagit definition file
- `-p, --project`: Specific project within workspace

### `record` - Record Management
Manage metagit records with various storage backends:

```bash
# Create a record from metagit configuration
metagit record create

# Show record(s)
metagit record show

# Search records
metagit record search <query>

# Update an existing record
metagit record update

# Delete a record
metagit record delete

# Export record to file
metagit record export

# Import record from file
metagit record import

# Show storage statistics
metagit record stats
```

Storage options:
- `--storage-type`: Choose between `local` or `opensearch`
- `--storage-path`: Path for local storage
- `--opensearch-*`: OpenSearch connection parameters

### `workspace` - Workspace Management
Manage multi-repository workspaces:

```bash
# Select project repository to work on
metagit workspace select
```

### `info` - Configuration Information
Display current configuration:

```bash
metagit info
```

### `version` - Version Information
Get application version:

```bash
metagit version
```

## Global Options

Available for all commands:

- `--version`: Show version and exit
- `-c, --config`: Path to configuration file
- `--debug / --no-debug`: Enable/disable debug mode
- `--verbose / --no-verbose`: Enable/disable verbose output
- `-h, --help`: Show help message

# Configuration

The default configuration file is `metagit.config.yaml`, which can be customized to suit your project's needs.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

# Development

# Links

## MCP Servers

[Sequential Thinking](https://github.com/modelcontextprotocol/servers/tree/HEAD/src/sequentialthinking)

