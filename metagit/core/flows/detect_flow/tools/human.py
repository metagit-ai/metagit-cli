"""Tool for asking human input."""

from collections.abc import Callable
from typing import Union

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


def _print_func(text: str) -> Union[None, Exception]:
    try:
        print("\n")
        print(text)
        return None
    except Exception as e:
        return e


def input_func() -> Union[str, Exception]:
    try:
        print("Insert your text. Press Ctrl-D (or Ctrl-Z on Windows) to end.")
        contents = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            contents.append(line)
        return "\n".join(contents)
    except Exception as e:
        return e


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
    args_schema: type[BaseModel] = MyToolInput
    prompt_func: Callable[[str], None] = _print_func
    input_func: Callable[[], str] = input_func

    def _run(self, query: str) -> Union[str, Exception]:
        """Use the Multi Line Human input tool."""
        try:
            prompt_result = self.prompt_func(query)
            if isinstance(prompt_result, Exception):
                return prompt_result
            return self.input_func()
        except Exception as e:
            return e
