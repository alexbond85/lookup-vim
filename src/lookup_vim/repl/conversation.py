"""Conversation buffer for follow-up questions with LLM"""


class ConversationBuffer:
    """Manages follow-up conversation state with LLM"""

    def __init__(self, source_lang: str, target_lang: str):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.messages: list[dict[str, str]] = []
        self.last_query: str | None = None
        self.last_result: str | None = None

    def start_conversation(self, query: str, result: str):
        """Start a new conversation with initial query and result"""
        self.messages = []
        self.last_query = query
        self.last_result = result

        self.messages.append(
            {
                "role": "system",
                "content": (
                    f"Aide à la lecture en {self.source_lang} pour locuteur "
                    f"{self.target_lang}. Parle {self.source_lang}/"
                    f"{self.target_lang} uniquement. Apprenant avancé. "
                    "Réponses brèves et ciblées."
                ),
            }
        )
        self.messages.append(
            {
                "role": "assistant",
                "content": f"Query: {query}\nResult: {result}",
            }
        )

    def add_follow_up(self, question: str) -> list[dict[str, str]]:
        """Add a follow-up question and return full conversation history"""
        self.messages.append({"role": "user", "content": question})
        return self.messages

    def add_response(self, response: str):
        """Add LLM response to conversation"""
        self.messages.append({"role": "assistant", "content": response})

    def has_conversation(self) -> bool:
        """Check if there's an active conversation"""
        return len(self.messages) > 0

    def reset(self):
        """Clear conversation state"""
        self.messages = []
        self.last_query = None
        self.last_result = None
