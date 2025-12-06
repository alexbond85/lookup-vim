from pydantic import BaseModel

from lookup_vim.language.translators.llm import StructuredOutputLLM
from lookup_vim.language.translators.prompts import Prompts


class Translator:
    """Generic translation provider that works with any StructuredOutputLLM"""

    def __init__(self, llm: StructuredOutputLLM, prompts: Prompts):
        self.llm = llm
        self.prompts = prompts

    def translate(
        self, query: str, context: str | None, output_model: type[BaseModel]
    ) -> BaseModel:
        """Translate a word/expression between the configured languages"""
        return self.llm.structured_response(
            user_prompt=self.prompts.user(query, context),
            system_prompt=self.prompts.system(),
            output_model=output_model,
        )


if __name__ == "__main__":
    from pydantic import BaseModel

    from lookup_vim.language.translators.openai_llm import OpenAILLM

    class TranslationOutput(BaseModel):
        translation: str
        explanation: str

    llm = OpenAILLM()
    prompts = Prompts(source_lang="français", target_lang="anglais")
    translator = Translator(llm, prompts)

    # Test without context
    result = translator.translate(
        query="bouleversé",
        context=None,
        output_model=TranslationOutput,
    )
    print(f"Without context: {result}")

    # Test with context
    result = translator.translate(
        query="bouleversé",
        context="Il était complètement bouleversé par la nouvelle.",
        output_model=TranslationOutput,
    )
    print(f"With context: {result}")
