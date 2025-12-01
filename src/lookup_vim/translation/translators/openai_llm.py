"""OpenAI implementation of StructuredLLM protocol"""

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()


class OpenAILLM:
    """OpenAI implementation of StructuredLLM protocol"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-5.1",
    ):
        """
        Initialize the LLM wrapper

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use (default: gpt-5.1)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model

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

        Raises:
            ValueError: If the API returns no output
        """
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=output_model,
            text={"verbosity": "low"},
        )

        output = response.output_parsed

        if output is None:
            raise ValueError("LLM generation failed: no output from API")

        return output

