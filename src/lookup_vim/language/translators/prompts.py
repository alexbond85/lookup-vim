"""Prompt factory for translation and conversation"""


class Prompts:
    """Prompt factory initialized with source and target languages"""

    def __init__(self, source_lang: str, target_lang: str):
        self.source_lang = source_lang
        self.target_lang = target_lang

    def system(self) -> str:
        """System prompt for translation"""
        return (
            f"Aide à la lecture en {self.source_lang} pour locuteur "
            f"{self.target_lang}. Parle {self.source_lang}/{self.target_lang} "
            f"uniquement. Apprenant avancé. Traduction en {self.target_lang}, "
            f"explications brèves et ciblées."
        )

    def user(self, query: str, context: str | None) -> str:
        """User prompt for translation"""
        lang_instruction = (
            f"Parle {self.source_lang}/{self.target_lang} uniquement."
        )
        if context:
            return (
                f'"{query}" dans : "{context}"\n\n'
                f'Traduis uniquement "{query}" en {self.target_lang}. '
                f"Explique brièvement le sens dans ce contexte. "
                f"Ajoute seulement si utile : nuances, usage, remarques. "
                f"{lang_instruction}"
            )
        return (
            f'Traduis "{query}" en {self.target_lang}. '
            f"Explique brièvement. Ajoute seulement si utile : "
            f"nuances, usage, remarques. "
            f"{lang_instruction}"
        )

    def conversation(self) -> str:
        """System prompt for follow-up conversations"""
        return (
            f"Aide à la lecture en {self.source_lang} pour locuteur "
            f"{self.target_lang}. Parle {self.source_lang}/{self.target_lang} "
            f"uniquement. Apprenant avancé. Réponses brèves et ciblées."
        )
