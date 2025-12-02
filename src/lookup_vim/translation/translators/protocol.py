"""Protocol for structured LLM implementations"""

from typing import Protocol

from pydantic import BaseModel


class StructuredLLM(Protocol):
    """Protocol for structured LLM implementations"""

    def generate(
        self,
        user_prompt: str,
        system_prompt: str,
        output_model: type[BaseModel],
    ) -> BaseModel:
        """
        Generate structured output from the LLM

        Args:
            user_prompt: The user's prompt/query
            system_prompt: The system prompt for the LLM
            output_model: Pydantic model for structured output

        Returns:
            Parsed structured output matching the output_model
        """
        ...
