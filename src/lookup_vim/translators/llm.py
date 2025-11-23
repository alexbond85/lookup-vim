"""Generic structured LLM wrapper for OpenAI API"""

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()


class StructuredLLM:
    """Generic LLM wrapper for structured output using OpenAI API"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-5.1",
        system_prompt: str = "",
    ):
        """
        Initialize the LLM wrapper

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use (default: gpt-5.1)
            system_prompt: System prompt for the LLM
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt

    def generate(
        self, user_prompt: str, output_model: type[BaseModel]
    ) -> BaseModel:
        """
        Generate structured output from the LLM

        Args:
            user_prompt: The user's prompt/query
            output_model: Pydantic model for structured output

        Returns:
            Parsed structured output matching the output_model

        Raises:
            ValueError: If the API returns no output
        """
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text_format=output_model,
            text={"verbosity": "low"},
        )

        output = response.output_parsed

        if output is None:
            raise ValueError("LLM generation failed: no output from API")

        return output
