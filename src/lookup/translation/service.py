"""Translation service"""

from typing import cast

from pydantic import BaseModel

from lookup.domain import TranslationResult
from lookup.translation.llm.base import StructuredOutputLLM
from lookup.translation.prompts import Prompts


class TranslationOutput(BaseModel):
    """Structured output format for translation"""

    translation: str
    explanations: str


class TranslationService:
    """Translation service using LLM with structured output"""

    def __init__(self, llm: StructuredOutputLLM, prompts: Prompts):
        self.llm = llm
        self.prompts = prompts

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
        output = cast(
            TranslationOutput,
            self.llm.structured_response(
                user_prompt=self.prompts.user(query, context),
                system_prompt=self.prompts.system(),
                output_model=TranslationOutput,
            ),
        )

        return TranslationResult(
            query=query,
            translation=output.translation,
            explanations=output.explanations,
            context=context,
        )
