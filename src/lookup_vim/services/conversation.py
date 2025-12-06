"""Conversation service for follow-up questions

Simple conversation management with LLM.
"""

import logging

from lookup_vim.language.translators.llm import StructuredOutputLLM

logger = logging.getLogger(__name__)


class ConversationService:
    """Manages conversations with LLM

    Simple API:
    - Add assistant/user messages
    - Generate response (adds user question, calls LLM, adds response)
    - Reset conversation
    """

    def __init__(self, llm: StructuredOutputLLM, system_prompt: str):
        self._llm = llm
        self._system_prompt = system_prompt
        self._messages: list[dict[str, str]] = []

    def add_assistant_message(self, content: str):
        """Add assistant message to conversation

        If first message, automatically adds system prompt.
        """
        if not self._messages:
            self._messages.append(
                {"role": "system", "content": self._system_prompt}
            )
        self._messages.append({"role": "assistant", "content": content})

    def add_user_message(self, content: str):
        """Add user message to conversation"""
        self._messages.append({"role": "user", "content": content})

    def generate_response(self, question: str) -> str | None:
        """Generate response to a question

        Adds user question, calls LLM, adds response to messages.

        Returns:
            LLM response or None on error
        """
        if not self._messages:
            return None

        try:
            self.add_user_message(question)
            response = self._llm.response(self._messages)
            if response:
                self._messages.append(
                    {"role": "assistant", "content": response}
                )
            return response
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None

    def has_conversation(self) -> bool:
        """Check if there's an active conversation"""
        return len(self._messages) > 0

    def reset(self):
        """Clear conversation state"""
        self._messages = []
