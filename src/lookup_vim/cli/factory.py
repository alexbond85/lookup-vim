"""Service factory - centralized dependency injection

Creates and wires all services with proper configuration.
Single source of truth for service instantiation.

Usage:
    factory = ServiceFactory()

    # Get individual services
    dictionary = factory.dictionary_service
    translation = factory.translation_service
    conversation = factory.conversation_service
    lookup = factory.lookup_service

    # Or create the full app
    app = factory.create_app()
"""

import logging
from dataclasses import dataclass

from lookup_vim.cache import create_cache
from lookup_vim.cache.base import CacheBase
from lookup_vim.cli.inputs import FifoSource, InputSource, StdinSource
from lookup_vim.config import Config, load_config
from lookup_vim.services.conversation import ConversationService
from lookup_vim.services.dictionary import DictionaryService
from lookup_vim.services.lookup import LookupService
from lookup_vim.services.translation import TranslationService
from lookup_vim.language.scrapers.lerobert import LeRobertScraper
from lookup_vim.language.translators.openai_llm import OpenAILLM
from lookup_vim.language.translators.prompts import Prompts
from lookup_vim.language.translators.translator import Translator


@dataclass
class ServiceFactory:
    """Factory for creating configured services

    Lazily creates services on first access and caches them.
    All services share the same config and can be overridden.
    """

    config: Config | None = None
    cache_type: str = "memory"
    model: str = "gpt-5.1"

    def __post_init__(self):
        if self.config is None:
            self.config = load_config()

        # Lazy-initialized services
        self._prompts: Prompts | None = None
        self._cache: CacheBase | None = None
        self._dictionary_service: DictionaryService | None = None
        self._translation_service: TranslationService | None = None
        self._conversation_service: ConversationService | None = None
        self._lookup_service: LookupService | None = None

    @property
    def source_lang(self) -> str:
        return self.config.source_lang

    @property
    def target_lang(self) -> str:
        return self.config.target_lang

    @property
    def fifo_path(self) -> str:
        return self.config.fifo_path

    @property
    def debug(self) -> bool:
        return self.config.debug

    def setup_logging(self) -> None:
        """Configure logging based on debug setting"""
        level = logging.DEBUG if self.debug else logging.WARNING
        logging.basicConfig(
            level=level,
            format="%(name)s - %(levelname)s - %(message)s"
            if self.debug
            else "%(message)s",
        )

    # --- Cached service instances ---

    @property
    def prompts(self) -> Prompts:
        if self._prompts is None:
            self._prompts = Prompts(self.source_lang, self.target_lang)
        return self._prompts

    @property
    def cache(self) -> CacheBase:
        if self._cache is None:
            self._cache = create_cache(self.cache_type)
        return self._cache

    @property
    def dictionary_service(self) -> DictionaryService:
        if self._dictionary_service is None:
            scraper = LeRobertScraper()
            self._dictionary_service = DictionaryService(scraper)
        return self._dictionary_service

    @property
    def translation_service(self) -> TranslationService:
        if self._translation_service is None:
            llm = OpenAILLM(model=self.model)
            translator = Translator(llm=llm, prompts=self.prompts)
            self._translation_service = TranslationService(provider=translator)
        return self._translation_service

    @property
    def conversation_service(self) -> ConversationService:
        if self._conversation_service is None:
            self._conversation_service = self.create_conversation_service(
                self.prompts.conversation()
            )
        return self._conversation_service

    def create_conversation_service(self, system_prompt: str) -> ConversationService:
        """Create a conversation service with a custom system prompt"""
        llm = OpenAILLM(model=self.model)
        return ConversationService(llm=llm, system_prompt=system_prompt)

    @property
    def lookup_service(self) -> LookupService:
        if self._lookup_service is None:
            self._lookup_service = LookupService(
                self.cache,
                self.translation_service,
            ).with_dictionary(self.dictionary_service)
        return self._lookup_service

    # --- Input sources ---

    def create_input_sources(
        self,
        enable_stdin: bool = True,
        enable_fifo: bool = True,
    ) -> list[InputSource]:
        """Create input sources for the app"""
        sources: list[InputSource] = []
        if enable_stdin:
            sources.append(StdinSource())
        if enable_fifo:
            sources.append(FifoSource(self.fifo_path))
        return sources

    # --- App factory ---

    def create_app(
        self,
        enable_stdin: bool = True,
        enable_fifo: bool = True,
    ):
        """Create a fully configured LookupApp

        Import here to avoid circular dependency.
        """
        from lookup_vim.cli.app import LookupApp

        return LookupApp(
            lookup_service=self.lookup_service,
            conversation_service=self.conversation_service,
            sources=self.create_input_sources(enable_stdin, enable_fifo),
        )


# Convenience function for simple usage
def create_factory(
    cache_type: str = "memory",
    model: str = "gpt-5.1",
) -> ServiceFactory:
    """Create a factory with custom settings"""
    return ServiceFactory(cache_type=cache_type, model=model)
