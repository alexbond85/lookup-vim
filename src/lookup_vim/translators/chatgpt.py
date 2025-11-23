"""ChatGPT-based translation provider"""

from pydantic import BaseModel

from lookup_vim.translators.base import TranslationProvider
from lookup_vim.translators.llm import StructuredLLM


class ChatGPTTranslator(TranslationProvider):
    """Translation provider using ChatGPT/OpenAI"""

    def __init__(
        self,
        llm: StructuredLLM,
        source_lang: str = "French",
        target_lang: str = "Russian",
    ):
        """
        Initialize the ChatGPT translator

        Args:
            llm: StructuredLLM instance configured with API key and model
            source_lang: Source language for translation (default: French)
            target_lang: Target language for translation (default: Russian)
        """
        self.llm = llm
        self.source_lang = source_lang
        self.target_lang = target_lang

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
        # Build the user prompt based on whether context is provided
        if context:
            user_prompt = f""""{query}" dans : "{context}"

Traduis uniquement "{query}" en {self.target_lang}. Explique brièvement le sens dans ce contexte. Ajoute seulement si utile : nuances, usage, remarques."""
        else:
            user_prompt = f"""Traduis "{query}" en {self.target_lang}. Explique brièvement. Ajoute seulement si utile : nuances, usage, remarques."""

        # Call the LLM with the prompt and output model
        return self.llm.generate(user_prompt, output_model)
