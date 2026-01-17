from lookup.cli.factory import ServiceFactory
from lookup.conversation.service import ConversationService
from lookup.domain import (
    ConjugationResult,
    TranslationResult,
    WordResult,
)

LookupResult = WordResult | ConjugationResult | TranslationResult | None


class Session:
    """Manages state for a user session"""

    def __init__(self, session_id: str, factory: ServiceFactory):
        self.session_id = session_id
        self.conversation_service = factory.create_conversation_service(
            factory.prompts.conversation()
        )
        self.messages = []  # Chat history for UI
        self.current_file: str | None = None
        self.current_phrase: str | None = None
        self.current_paragraph: str | None = None
        # Track which contexts have been translated for current selection
        self.phrase_translated: bool = False
        self.paragraph_translated: bool = False

    def reset_context_flags(self):
        """Reset translation tracking for new selection"""
        self.phrase_translated = False
        self.paragraph_translated = False

    def reset_conversation(self):
        """Reset conversation for new translation (match CLI behavior)"""
        self.conversation_service.reset()
        # Clear Q&A messages but keep structure for new translation
        self.messages = []

    def add_translation(self, query: str, result: LookupResult):
        """Add translation to chat history"""
        # Format like CLI app does
        result_text = self._format_result(query, result)
        self.conversation_service.add_assistant_message(result_text)

        # Add to UI messages based on result type
        if isinstance(result, TranslationResult):
            self.messages.append({
                "role": "assistant",
                "type": "translation",
                "data": {
                    "query": query,
                    "translation": result.translation,
                    "explanations": result.explanations
                }
            })
        elif isinstance(result, WordResult):
            # Format definitions for display
            definitions_html = self._format_word_result(result)
            self.messages.append({
                "role": "assistant",
                "type": "translation",
                "data": {
                    "query": query,
                    "translation": result.word,
                    "explanations": definitions_html
                }
            })
        elif isinstance(result, ConjugationResult):
            self.messages.append({
                "role": "assistant",
                "type": "translation",
                "data": {
                    "query": query,
                    "translation": result.redirected_to,
                    "explanations": result.message
                }
            })

    def add_conversation(self, question: str, answer: str):
        """Add Q&A to chat history"""
        self.messages.extend([
            {"role": "user", "type": "question", "content": question},
            {"role": "assistant", "type": "answer", "content": answer}
        ])

    def _format_result(self, query: str, result: LookupResult) -> str:
        """Format result as text for conversation context (like CLI app)"""
        if isinstance(result, TranslationResult):
            content = (
                f"Translation: {result.translation}\n"
                f"Explanations: {result.explanations}"
            )
        elif isinstance(result, WordResult):
            lines = []
            for i, d in enumerate(result.definitions, 1):
                lines.append(f"{i}. {d.definition}")
                for ex in d.examples[:2]:
                    lines.append(f"   → {ex}")
            definitions = "\n".join(lines)
            content = f"Word: {result.word}\nDefinitions:\n{definitions}"
        elif isinstance(result, ConjugationResult):
            content = (
                f"Conjugation of: {result.redirected_to}\n{result.message}"
            )
        else:
            content = str(result) if result else ""

        return f"Query: {query}\nResult: {content}"

    def _format_word_result(self, result: WordResult) -> str:
        """Format WordResult definitions as HTML"""
        lines = []
        for i, d in enumerate(result.definitions, 1):
            lines.append(f"<b>{i}. {d.definition}</b>")
            for ex in d.examples[:2]:
                lines.append(f"<i>→ {ex}</i>")
        return "<br>".join(lines)


class SessionManager:
    """Simple in-memory session storage"""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._factory = ServiceFactory(cache_type="jsonl", model="gpt-5.1")

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id, self._factory)
        return self._sessions[session_id]

    def reload_factory(self):
        """Reload the factory with fresh config (after config changes)"""
        self._factory = ServiceFactory(cache_type="jsonl", model="gpt-5.1")
        # Clear existing sessions so they get recreated with new factory
        self._sessions.clear()

    @property
    def factory(self) -> ServiceFactory:
        return self._factory
