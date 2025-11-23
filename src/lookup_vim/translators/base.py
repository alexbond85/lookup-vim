"""Abstract base class for translation providers"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class TranslationProvider(ABC):
    """Abstract base class for translation provider implementations"""

    @abstractmethod
    def translate(
        self, query: str, context: str | None, output_model: type[BaseModel]
    ) -> BaseModel:
        """
        Translate a word/expression with optional context

        Args:
            query: The word or expression to translate
            context: Optional context (phrase/paragraph) for the query
            output_model: Pydantic model for structured output

        Returns:
            Parsed structured output matching the output_model
        """
        pass
