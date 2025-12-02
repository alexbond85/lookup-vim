"""REPL module for interactive lookup console

Architecture:
    - inputs.py: Input sources (Protocol + StdinSource, FifoSource, Multiplexer)
    - core.py: LookupEngine (input-agnostic lookup logic)
    - runner.py: ReplRunner (ties inputs to engine)
    - display.py: Rich output formatting
    - conversation.py: Follow-up conversation state

Usage:
    from lookup_vim.repl import main
    main()

Or create custom configuration:
    from lookup_vim.repl import create_default_runner, LookupEngine, ReplRunner
    from lookup_vim.repl.inputs import StdinSource, FifoSource

    engine = LookupEngine(cache_type="jsonl")
    runner = ReplRunner(engine, sources=[StdinSource()])
    runner.start()
"""

from lookup_vim.repl.core import LookupEngine
from lookup_vim.repl.runner import ReplRunner, create_default_runner, main

__all__ = [
    "main",
    "LookupEngine",
    "ReplRunner",
    "create_default_runner",
]
