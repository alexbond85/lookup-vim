"""CLI module for interactive lookup

Architecture:
    - factory.py: ServiceFactory (creates all services with config)
    - inputs.py: Input sources (Protocol + StdinSource, FifoSource, Multiplexer)
    - app.py: LookupApp (orchestrates LookupService + ConversationService)
    - display.py: Rich output formatting
    - standalone/: Individual service interfaces for testing

Usage:
    from lookup_vim.cli import main
    main()

Or create custom configuration:
    from lookup_vim.cli import ServiceFactory

    factory = ServiceFactory(cache_type="jsonl")
    app = factory.create_app()
    app.start()
"""

from lookup_vim.cli.app import LookupApp, main
from lookup_vim.cli.factory import ServiceFactory, create_factory

__all__ = [
    "main",
    "LookupApp",
    "ServiceFactory",
    "create_factory",
]
