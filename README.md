# Metagit

Metagit is situational awareness for developers made easy. Metagit can make multi-repo projects feel more like a monorepo and provide information on the software stacks within.

<details>
<summary>Table of Contents</summary>
<!---toc start-->

* [Metagit](#metagit)
* [About](#about)
  * [Audience](#audience)
  * [Metagit is NOT...](#metagit-is-not)
    * [...an SBOM Tool](#an-sbom-tool)
    * [...a git Client](#a-git-client)
  * [How It Works](#how-it-works)
* [Modes](#modes)
  * [Workspace Mode](#workspace-mode)
  * [Metadata Mode](#metadata-mode)
  * [Metadata+ Mode](#metadata-mode-1)
  * [Enterprise (TBD)](#enterprise-tbd)
  * [Installation](#installation)
* [Usage](#usage)
    * [Initialize a Repository](#initialize-a-repository)
    * [Project Commands](#project-commands)
      * [Detect Project Settings](#detect-project-settings)
    * [Workspace Commands](#workspace-commands)
      * [Synchronize Workspace](#synchronize-workspace)
* [Configuration](#configuration)
  * [Contributing](#contributing)
  * [License](#license)
* [Configuration](#configuration-1)
* [Use](#use)
* [Development](#development)
  * [MCP Servers](#mcp-servers)

<!---toc end-->
</details>

# About

This tool is well suited for a number of scenarios including;

1. At-a-glance view of a project's technical stacks, languages, external dependencies, and generated artifacts.
2. Rapid pivoting between numerous git projects throughout the day while still maintaining a steady clip of productivity.
3. Isolating outside dependencies that weaken the security and dependability of your cicd pipelines.
4. Automated documentation of a code's provenance.
5. As a new contributor to a project or team, get from zero to first code commit in as little time as possible.

Metagit aims to provide situational awareness for developers, SREs, AI agents, and engineers on the git projects they work in every day. It is meant to shed light on the numerous interconnected dependencies that comprise the whole of the entire solution being worked on in a single easily read and updated file.

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

SBOM output can be thousands of lines long and encompass all the software dependencies, their transitive dependencies, and  more. This is too much for the simple need of situational awareness and AI integration. As such, a comprehensive software bill of materials is overkill for the goals outlined above. The development roadmap may include the ability to read in sbom manifests as a data source though!

Metagit makes extensive use of CI library definitions (like go.mod, packages.json, requirements.txt, et cetera) for detection and boundary validations. Such files will be used to help determine technology stacks in use but not extensive versioning or other deep information.

### ...a git Client

Despite the name this tool still requires git and all the trappings of a git hosting solution.

## How It Works

This app accesses and saves project configuration metadata within the repository as a .metagit.yml file (or in a hosted tenant). The data within a project follows a schema that can be read via the cli.

If using this tool to simply manage several dozen git repos (aka. an umbrella repo) then everything within the configuration file can be manually updated. You can also attempt to automatically update the file using a mix of standard heuristics and AI driven workflows.

# Modes

This application will have multiple modes of operation as described below.

## Workspace Mode

This mode is the first planned release feature as an open source cli tool.

In this mode users stitch together various repositories that comprise the components of a project into one workspace that can be loaded via vscode or accessed individually via fast context switching at the console.

> **AKA** Multi-repo as Monorepo

In this mode you are using metagit as a means to externally track and work with multiple git projects as a whole. One top level 'umbrella' project has the only metagit definition file which contains definitions for all related git repos and local target folders in the current project. Optionally you then sync the project to your local workstation.

The metagit configuration file is then be checked into version control as a stand-alone project.

This mode is ideal for;

- Simply trying out metagit
- Creating umbrella projects for new team members of a multi-repo project
- Individual power users that need to quickly pivot between several git project repositories that comprise a larger team effort
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

All the prior metadata is incredibly useful already. But if we add context around this then we are cooking with gas! If we setup basic organization boundaries like owned registries or github/gitlab groups we can then start looking for fragile pipelines or  This can be done easily through a central configuration file or SaaS offering. This 

## Enterprise (TBD)

Enterprise mode is using metagit at scale.

In this mode metagit connects to our enterprise SaaS offering to help mine the whole of your organization's code assets continuously.

- Imagine if you could mine your entire organization's copious amounts of code repos for the exact thing you need for your own project? 
- How many times do wheels get recreated simply because you cannot find the artifact needed for your own project even though you know it must exist? 
- How much time is wasted looking for a project using your language and framework to use as a starting point for your own efforts?
- How frustrated do you get when, after putting in days or weeks of effort to create something you find another internal project that does it twice as elegantly that was done 6 months ago by another team? Enterprise mode of metagit aims to target this issue head on.


## Installation

To install metagit, clone the repository and build the project:

```bash
git clone https://github.com/zloeber/metagit.git
cd metagit

./configure.sh
task build
```

# Usage

### Initialize a Repository

To initialize a new metagit configuration in your current Git repository, run:

```bash
./metagit init
```

This command will check if the current directory is a Git repository and create a `metagit.yaml` configuration file if it does not exist. It will also ensure that `.metagit` is added to your `.gitignore`.

### Project Commands

To work with project settings, use the project command:

```bash
./metagit project
```

#### Detect Project Settings

To detect project configurations, run:

```bash
./metagit project detect
```

### Workspace Commands

To manage workspace settings, use the workspace command:

```bash
./metagit workspace
```

#### Synchronize Workspace

To sync workspace settings, run:

```bash
./metagit workspace sync
```

# Configuration

The default configuration file is `metagit.config.yaml`, which can be customized to suit your project's needs.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

# Configuration

`./.configure.sh`

# Use

```bash
uv run -m metagit.cli.main

# Show current config
uv run -m metagit.cli.main appconfig show

# Dump new/default config
uv run -m metagit.cli.main appconfig create

# Run generic detection for current path
uv run -m metagit.cli.main detect repo
```

# Development

## MCP Servers

[Sequential Thinking](https://github.com/modelcontextprotocol/servers/tree/HEAD/src/sequentialthinking)
