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
            user_prompt = f"""Le mot/expression "{query}" a été sélectionné dans ce contexte :

"{context}"

Donne une réponse courte et utile :
1. Traduction en {self.target_lang}
2. Sens littéral et explication (seulement si cela aide à comprendre le mot/expression)
3. Remarques supplémentaires (étymologie, connotation, nuances) - seulement si c'est important pour la compréhension"""
        else:
            user_prompt = f"""Traduis le mot/expression {self.source_lang} "{query}" en {self.target_lang} et donne une réponse courte et utile :
1. Traduction
2. Sens littéral et explication (seulement si cela aide à comprendre le mot/expression)
3. Remarques supplémentaires (étymologie, connotation, nuances) - seulement si c'est important pour la compréhension"""

        # Call the LLM with the prompt and output model
        return self.llm.generate(user_prompt, output_model)
