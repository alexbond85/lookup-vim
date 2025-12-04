"""REPL module for interactive lookup console

Architecture:
    - inputs.py: Input sources (Protocol + StdinSource, FifoSource, Multiplexer)
    - runner.py: ReplRunner (orchestrates LookupService + FollowUpService)
    - display.py: Rich output formatting

Usage:
    from lookup_vim.repl import main
    main()

Or create custom configuration:
    from lookup_vim.repl import create_default_runner, ReplRunner

    runner = create_default_runner(cache_type="jsonl")
    runner.start()
"""

from lookup_vim.repl.runner import ReplRunner, create_default_runner, main

__all__ = [
    "main",
    "ReplRunner",
    "create_default_runner",
]
