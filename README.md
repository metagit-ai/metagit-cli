# metagit

Agent code used to gain situational awareness within your project.

- Project Purpose
- Primary language
- CICD platform
- CI
  - Tools for:
    - Lint
    - SAST/DAST
    - Code Quality
    - Build
- CD 
  - Tools for:
    - Infrastructure as code
    - Configuration as code
    - Artifact deployment targets
- Development requirements
- CICD dependencies
- project dependencies
- Upstream related projects
- Branch management strategy
- Version management strategy
- Generated Artifacts

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

# Utilities

## UserPrompt

The `UserPrompt` utility provides an interactive way to collect user input for Pydantic model properties with beautiful, styled prompts using `prompt_toolkit`.

### Features

- **Styled Prompts**: Color-coded input prompts with different styles for fields, descriptions, defaults, and errors
- **Type Validation**: Real-time validation of user input against Pydantic field types
- **Default Values**: Support for pre-filled default values
- **Optional Fields**: Interactive prompts for optional fields
- **Error Handling**: Clear error messages with styling
- **Model Creation**: Complete Pydantic model creation from user input

### Usage

```python
from pydantic import BaseModel, Field
from utils.userprompt import UserPrompt

class UserProfile(BaseModel):
    name: str = Field(description="Full name of the user")
    email: str = Field(description="Email address")
    age: int = Field(description="Age in years", ge=0, le=150)
    is_active: bool = Field(default=True, description="Whether the user is active")

# Create a complete model instance
user_profile = UserPrompt.prompt_for_model(UserProfile)

# Prompt for a single field
api_key = UserPrompt.prompt_for_single_field(
    field_name="API Key",
    field_type=str,
    description="Your API key for external service",
    default="sk-..."
)

# Confirm an action
if UserPrompt.confirm_action("Would you like to proceed?"):
    print("Proceeding...")
```

### Example

Run the example to see the styled prompts in action:

```bash
python examples/userprompt_example.py
```

# MCP Servers

[Sequential Thinking](https://github.com/modelcontextprotocol/servers/tree/HEAD/src/sequentialthinking)
