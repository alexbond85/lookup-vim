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

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str | None:
        """
        Chat completion with message history

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature

        Returns:
            Assistant's response content or None
        """
        ...
