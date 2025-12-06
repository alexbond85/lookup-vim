"""OpenAI implementation of StructuredOutputLLM protocol"""

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()


class OpenAILLM:
    """OpenAI implementation of StructuredOutputLLM protocol"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-5.1",
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def structured_response(
        self,
        user_prompt: str,
        system_prompt: str,
        output_model: type[BaseModel],
    ) -> BaseModel:
        """Generate structured response parsed into the given model"""
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

    def response(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str | None:
        """Generate text response for a message history"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
        )
        return response.choices[0].message.content


if __name__ == "__main__":
    from pydantic import BaseModel

    class Sentiment(BaseModel):
        sentiment: str
        confidence: float

    llm = OpenAILLM()

    # Test structured response
    result = llm.structured_response(
        user_prompt="The food was amazing and the service was great!",
        system_prompt="Analyze the sentiment of the given text. Return "
        "'positive', 'negative', or 'neutral' as a string.",
        output_model=Sentiment,
    )
    print(f"Structured: {result}")

    # Test regular response
    reply = llm.response(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. Be brief.",
            },
            {"role": "user", "content": "What is 2+2?"},
        ]
    )
    print(f"Response: {reply}")
