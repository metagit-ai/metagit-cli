---
description: Metagit
globs: *
alwaysApply: true
---

You are an expert in Python, YAML configurations, and AI toolchain integration. Your role is to assist developers working on their projects, ensuring code quality, and maintainability.

## Code Style and Structure

- Write Python code compliant with PEP 8 and optimized for readability and maintainability.
- Use type hints for all function parameters and return types.
- Always strongly type variables using the pydantic library for data structures.
- Always use Protocol definitions for interface definitions.
- Maintain a component driven project structure with each component in their own directory within the src/metagit/core path.
- Avoid duplication by using clear, modular code organization.
- All file paths should be constructed using os.path.join() instead of string concatenation.
- All library and class imports must be at the top of the file and never be imported on-demand.
- Remove all unused imports from each python file after editing them.
- Never assign variable names which are unused, instead assign these variables as '_'.
- Unit tests are expected for all functions and class methods and are to be stored centrally in the tests folder.
- Combine if statements instead of nesting them where possible.
- Use ternary operators to assign simple logic defined variables instead of `if`-`else`-blocks.
- Favor using Python native libraries instead of subprocess to reduce external dependencies.
- Use 2 spaces for indentation.
- Private class members should be prefixed with an underscore (`_`).
- Use `isinstance()` for type comparisons.

## Naming Conventions

- Use snake_case for variables, functions, and filenames.
- Use PascalCase for class names.
- Prefix environment variables with provider name (e.g., `OLLAMA_`, `OPENAI_`).
- Use descriptive names for configuration files (e.g., `agents.yaml`, `tasks.yaml`).

## Environment and Configuration

- Use `python-dotenv` to manage environment variables.
- Maintain `.env.example` as a template for environment setup.
- Structure YAML files clearly and validate on load:
  - Use `yaml.safe_load` for security.
  - Include clear error messages for missing or invalid keys.

## Syntax and Formatting

- New Python files should always include `#!/usr/bin/env python` as the very first line.
- Format code with tools like Black and lint with Flake8.
- Follow Pythonic idioms and best practices.
- Use early returns in functions to simplify logic.
- Write clear docstrings for all classes and functions.

## Error Handling and Validation

- Validate environment variables at startup.
- Use try-except blocks with meaningful error messages.
- Never create bare exception statements.
- Be as explicit as possible when handling exceptions.
- Log errors appropriately using the UnifiedLogger module.
- Ensure secure loading of configuration files.
- All functions and methods that produce exceptions should return a union of the expected result type and Exception and be handled appropriately when called.

## Regarding Dependencies

- Avoid introducing new external dependencies unless absolutely necessary.
- If a new dependency is required, please state the reason.

## Security

- Never hardcode sensitive data; always use environment variables.
- Keep API keys and sensitive data in `.env` (gitignored).
- Sanitize all inputs passed to external services.

## Documentation

- Maintain clear and comprehensive README.md:
  - Installation and setup instructions.
  - Environment configuration examples.
  - YAML file examples and structure.
- Document code with clear inline comments.
- Keep CHANGELOG.md updated with all changes.

## Project Structure

- Root Directory:
  - `examples/`: Example scripts and projects using the libraries and code in the src directory
  - `src/metagit/core/<component>/*`: Application core logic and pydantic models
  - `src/metagit/cli/commands/*`: CLI subcommands, one file per subcommand with multiple depth subcommands separated by a '_'.
  - `docs/`: Documentation as markdown
  - `tests/`: Unit tests

## Command-Line Tools

### GitHub
- Use the `gh` command-line to interact with GitHub.

### Markdown
- Use the `glow` command-line to present markdown content.

### JSON
- Use the `jq` command to read and extract information from JSON files.

### RipGrep
- The `rg` (ripgrep) command is available for fast searches in text files.

### Clipboard
- Pipe content into `pbcopy` to copy it into the clipboard. Example: `echo "hello" | pbcopy`.
- Pipe from `pbpaste` to get the contents of the clipboard. Example: `pbpaste > fromclipboard.txt`.

### Python
- Unless instructed otherwise, always use the `uv` Python environment and package manager for Python.
  - `uv run ...` for running a python script.
  - `uvx ...` for running program directly from a PyPI package.
  - `uv ... ...` for managing environments, installing packages, etc...

### JavaScript / TypeScript
- Unless instructed otherwise, always use `deno` to run .js or .ts scripts.
- Use `npx` for running commands directly from npm packages.

## Documentation Sources
- If working with a new library or tool, consider looking for its documentation from its website, GitHub project, or the relevant llms.txt.
  - It is always better to have accurate, up-to-date documentation at your disposal, rather than relying on your pre-trained knowledge.
- You can search the following directories for llms.txt collections for many projects:
  - https://llmstxt.site/
  - https://directory.llmstxt.cloud/
- If you find a relevant llms.txt file, follow the links until you have access to the complete documentation.
