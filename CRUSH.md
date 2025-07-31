# CRUSH.md - Developer Guide for Metagit

## Build/Lint/Test Commands

- Install dependencies: `uv sync`
- Run app: `uv run -m metagit.cli.main`
- Run tests: `task test` or `pytest tests/`
- Run single test: `pytest tests/test_module.py::test_function`
- Type checking: `task typecheck` or `uv run mypy metagit/core`
- Linting: `task lint` or `uv run ruff check .`
- Formatting: `task format` or `uv run ruff format .`
- Build: `task build` or `uv run build`

## Code Style Guidelines

- PEP 8 compliance with 2-space indentation
- Type hints required for all functions and variables
- Use pydantic for data structures and Protocol for interfaces
- Component-driven structure in src/metagit/core/<component>/
- File paths with os.path.join(), imports at file top
- Remove unused imports and variables (use '_' for unused)
- Combine if statements, use ternary operators for simple logic
- Prefer Python native libraries over subprocess
- Private members prefixed with underscore (_)
- isinstance() for type comparisons

## Naming Conventions

- snake_case for variables, functions, filenames
- PascalCase for class names
- Environment variables prefixed with provider name (e.g., OLLAMA_, OPENAI_)
- Descriptive configuration file names (e.g., agents.yaml)

## Error Handling

- Validate environment variables at startup
- Use try-except with meaningful messages
- No bare exception statements
- Log errors with UnifiedLogger
- Secure configuration file loading
- Functions returning Union[ExpectedType, Exception]

## Security

- No hardcoded sensitive data
- Use environment variables for secrets
- Sanitize inputs to external services

## Documentation

- Maintain README.md with setup instructions
- Clear inline comments in code
- Keep CHANGELOG.md updated

## Project Structure

- examples/: Example scripts
- src/metagit/core/<component>/: Core logic and models
- src/metagit/cli/commands/: CLI subcommands
- docs/: Documentation
- tests/: Unit tests

## Tools

- uv: Python environment/package manager
- task: Task runner
- ruff/black: Formatting and linting
- pytest: Testing framework
- mypy: Type checking

## Cursor Rules

Follow all guidelines in .cursor/rules/project-level.mdc