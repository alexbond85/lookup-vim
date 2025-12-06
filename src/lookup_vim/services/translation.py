"""Translation service with dependency injection"""

from typing import cast

from pydantic import BaseModel

from lookup_vim.language.translators.translator import Translator
from lookup_vim.models import TranslationResult


class TranslationOutput(BaseModel):
    """Structured output format for translation"""

    translation: str
    explanations: str


class TranslationService:
    """High-level translation service that delegates to a translator"""

    def __init__(self, provider: Translator):
        """
        Initialize the translation service

        Args:
            provider: Translator instance
        """
        self.provider = provider

    def translate(
        self, query: str, context: str | None = None
    ) -> TranslationResult:
        """
        Translate a word/expression with detailed explanations

        Args:
            query: The word or expression to translate
            context: Optional context (phrase/paragraph) for the query

        Returns:
            TranslationResult containing translation and explanations
        """
        # Call the provider with the structured output model
        output = cast(
            TranslationOutput,
            self.provider.translate(query, context, TranslationOutput),
        )

        # Convert to TranslationResult for backward compatibility
        return TranslationResult(
            query=query,
            translation=output.translation,
            explanations=output.explanations,
            context=context,
        )
