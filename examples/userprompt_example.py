#!/usr/bin/env python
"""
Example demonstrating the improved UserPrompt utility with prompt_toolkit styling.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel, Field

from metagit.core.utils.userprompt import UserPrompt


class UserProfile(BaseModel):
    """Example Pydantic model for user profile creation."""

    name: str = Field(description="Full name of the user")
    email: str = Field(description="Email address")
    age: int = Field(description="Age in years", ge=0, le=150)
    is_active: bool = Field(default=True, description="Whether the user is active")
    tags: list[str] = Field(
        default_factory=list, description="User tags (comma-separated or JSON array)"
    )
    preferences: dict = Field(
        default_factory=dict, description="User preferences (JSON format)"
    )


class ProjectConfig(BaseModel):
    """Example Pydantic model for project configuration."""

    project_name: str = Field(description="Name of the project")
    version: str = Field(default="1.0.0", description="Project version")
    description: str = Field(description="Project description")
    author: str = Field(description="Project author")
    license: str = Field(default="MIT", description="Project license")


def main():
    """Demonstrate the UserPrompt utility with different scenarios."""

    print("🚀 UserPrompt Utility Demo with prompt_toolkit Styling")
    print("=" * 60)

    # Example 1: Create a user profile
    print("\n📝 Example 1: Creating a User Profile")
    print("-" * 40)

    if UserPrompt.confirm_action("Would you like to create a user profile?"):
        user_profile = UserPrompt.prompt_for_model(UserProfile)
        print(f"\n✅ Created user profile: {user_profile.model_dump()}")

    # Example 2: Create a project configuration
    print("\n📝 Example 2: Creating a Project Configuration")
    print("-" * 40)

    if UserPrompt.confirm_action("Would you like to create a project configuration?"):
        project_config = UserPrompt.prompt_for_model(ProjectConfig)
        print(f"\n✅ Created project config: {project_config.model_dump()}")

    # Example 3: Single field prompt
    print("\n📝 Example 3: Single Field Prompt")
    print("-" * 40)

    if UserPrompt.confirm_action("Would you like to test a single field prompt?"):
        api_key = UserPrompt.prompt_for_single_field(
            field_name="API Key",
            field_type=str,
            description="Your API key for external service",
            default="sk-...",
        )
        print(
            f"\n✅ API Key entered: {api_key[:10]}..."
            if api_key
            else "No API key provided"
        )

    print("\n🎉 Demo completed!")


if __name__ == "__main__":
    main()
