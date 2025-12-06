"""LLM implementations for translation"""

from lookup.translation.llm.base import StructuredOutputLLM
from lookup.translation.llm.openai import OpenAILLM

__all__ = ["OpenAILLM", "StructuredOutputLLM"]
