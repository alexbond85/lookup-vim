"""Generic translation provider"""

from pydantic import BaseModel

from lookup_vim.translation.translators.protocol import StructuredLLM
from lookup_vim.translation.translators.prompts import TranslationPrompts


class Translator:
    """Generic translation provider that works with any StructuredLLM"""

    def __init__(
        self,
        structured_llm: StructuredLLM,
        prompts: TranslationPrompts,
    ):
        """
        Initialize the translator

        Args:
            structured_llm: StructuredLLM implementation
            prompts: Translation prompts handler
        """
        self.structured_llm = structured_llm
        self.prompts = prompts

    def translate(
        self, query: str, context: str | None, output_model: type[BaseModel]
    ) -> BaseModel:
        """
        Translate a word/expression between the configured languages

        Args:
            query: The word or expression to translate
            context: Optional context (phrase/paragraph) for the query
            output_model: Pydantic model for structured output

        Returns:
            Parsed structured output matching the output_model
        """
        user_prompt = self.prompts.user_prompt(query, context)

        return self.structured_llm.generate(
            user_prompt=user_prompt,
            system_prompt=self.prompts.system_prompt,
            output_model=output_model,
        )

