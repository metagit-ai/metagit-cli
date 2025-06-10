"""Tool for asking human input."""

from typing import Callable, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


def _print_func(text: str) -> None:
    print("\n")
    print(text)


def input_func() -> str:
    print("Insert your text. Press Ctrl-D (or Ctrl-Z on Windows) to end.")
    contents = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        contents.append(line)
    return "\n".join(contents)


class MyToolInput(BaseModel):
    """Input schema for MyCustomTool."""

    query: str = Field(..., description="Query to the human.")


class HumanTool(BaseTool):
    name: str = "HumanTool"
    description: str = (
        "You can ask a human for guidance when you think you"
        " got stuck or you are not sure what to do next."
        " The input should be a question for the human."
        " This tool version is suitable when you need answers that span over"
        " several lines."
    )
    args_schema: Type[BaseModel] = MyToolInput
    prompt_func: Callable[[str], None] = _print_func
    input_func: Callable[[], str] = input_func

    def _run(self, query: str) -> str:
        """Use the Multi Line Human input tool."""
        self.prompt_func(query)
        return self.input_func()
