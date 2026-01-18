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

from lookup.cache.base import CacheBase
from lookup.cache.jsonl import JSONLCache
from lookup.cache.memory import MemoryCache
from lookup.cli.inputs import FifoSource, InputSource, StdinSource
from lookup.config import Config, load_config, save_config
from lookup.conversation.service import ConversationService
from lookup.dictionary.scraper import LeRobertScraper
from lookup.dictionary.service import DictionaryService
from lookup.orchestration.service import LookupService
from lookup.translation.llm.openai import OpenAILLM
from lookup.translation.prompts import Prompts
from lookup.translation.service import TranslationService


def create_cache(cache_type: str, config: Config) -> CacheBase:
    """Factory function to create cache instances"""
    if cache_type == "jsonl":
        return JSONLCache(cache_file=config.selections_file)
    return MemoryCache()


@dataclass
class ServiceFactory:
    """Factory for creating configured services

    Lazily creates services on first access and caches them.
    All services share the same config and can be overridden.

    Args:
        production: If True, use OS app data directory for storage
                   (~/Library/Application Support/VimLookup on macOS)
    """

    config: Config | None = None
    cache_type: str = "memory"
    model: str = "gpt-5.1"
    production: bool = False

    def __post_init__(self):
        if self.config is None:
            self.config = load_config(production=self.production)

        # Lazy-initialized services
        self._prompts: Prompts | None = None
        self._cache: CacheBase | None = None
        self._dictionary_service: DictionaryService | None = None
        self._translation_service: TranslationService | None = None
        self._conversation_service: ConversationService | None = None
        self._lookup_service: LookupService | None = None

    @property
    def source_lang(self) -> str:
        assert self.config is not None
        return self.config.source_lang

    @property
    def target_lang(self) -> str:
        assert self.config is not None
        return self.config.target_lang

    @property
    def fifo_path(self) -> str:
        assert self.config is not None
        return str(self.config.fifo_path)

    @property
    def debug(self) -> bool:
        assert self.config is not None
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
            assert self.config is not None
            self._cache = create_cache(self.cache_type, self.config)
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
            self._translation_service = TranslationService(
                llm=llm, prompts=self.prompts
            )
        return self._translation_service

    @property
    def conversation_service(self) -> ConversationService:
        if self._conversation_service is None:
            self._conversation_service = self.create_conversation_service(
                self.prompts.conversation()
            )
        return self._conversation_service

    def create_conversation_service(
        self, system_prompt: str
    ) -> ConversationService:
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
        from lookup.cli.app import LookupApp

        return LookupApp(
            lookup_service=self.lookup_service,
            conversation_service=self.conversation_service,
            sources=self.create_input_sources(enable_stdin, enable_fifo),
        )


# Convenience function for simple usage
def create_factory(
    cache_type: str = "memory",
    model: str = "gpt-5.1",
    production: bool = False,
) -> ServiceFactory:
    """Create a factory with custom settings

    Args:
        cache_type: Type of cache to use ("memory" or "jsonl")
        model: LLM model to use
        production: If True, use OS app data directory for storage
    """
    return ServiceFactory(
        cache_type=cache_type, model=model, production=production
    )
