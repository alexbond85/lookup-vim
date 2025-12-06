"""Protocol for structured output LLM implementations"""

from typing import Protocol

from pydantic import BaseModel


class StructuredOutputLLM(Protocol):
    """Protocol for LLM with structured output support"""

    def structured_response(
        self,
        user_prompt: str,
        system_prompt: str,
        output_model: type[BaseModel],
    ) -> BaseModel:
        """Generate structured response parsed into the given model"""
        ...

    def response(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str | None:
        """Generate text response for a message history"""
        ...
