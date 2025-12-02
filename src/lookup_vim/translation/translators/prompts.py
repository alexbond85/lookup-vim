from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TranslationPrompts:
    """Translation prompts handler"""

    source_lang: str
    target_lang: str
    system_prompt: str

    @classmethod
    def create(cls, source_lang: str, target_lang: str) -> TranslationPrompts:
        """
        Create a TranslationPrompts with a default system prompt

        Args:
            source_lang: Source language for translation
            target_lang: Target language for translation

        Returns:
            TranslationPrompts instance
        """
        system_prompt = (
            f"Aide à la lecture en {source_lang} pour locuteur "
            f"{target_lang}. Parle {source_lang}/{target_lang} "
            f"uniquement. Apprenant avancé. Traduction en {target_lang}, "
            f"explications brèves et ciblées."
        )
        return cls(
            source_lang=source_lang,
            target_lang=target_lang,
            system_prompt=system_prompt,
        )

    def user_prompt(self, query: str, context: str | None) -> str:
        """
        Build user prompt for translation

        Args:
            query: The word or expression to translate
            context: Optional context (phrase/paragraph) for the query

        Returns:
            Formatted user prompt string
        """
        if context:
            return (
                f'"{query}" dans : "{context}"\n\n'
                f'Traduis uniquement "{query}" en {self.target_lang}. '
                f"Explique brièvement le sens dans ce contexte. "
                f"Ajoute seulement si utile : nuances, usage, remarques."
            )
        else:
            return (
                f'Traduis "{query}" en {self.target_lang}. '
                f"Explique brièvement. Ajoute seulement si utile : "
                f"nuances, usage, remarques."
            )
