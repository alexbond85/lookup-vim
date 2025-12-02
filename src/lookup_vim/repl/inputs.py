"""Input sources for the REPL - Open/Closed design

Protocol-based abstraction allows adding new input sources
without modifying existing code.

Usage:
    sources = [StdinSource(), FifoSource()]
    mux = InputMultiplexer(sources)

    while True:
        event = mux.wait_for_input()
        if event:
            process(event)
"""

import contextlib
import json
import logging
import os
import select
import sys
from dataclasses import dataclass, field
from typing import IO, Protocol

logger = logging.getLogger(__name__)


@dataclass
class InputEvent:
    """An input event from any source"""

    text: str
    source: str
    metadata: dict = field(default_factory=dict)


class InputSource(Protocol):
    """Protocol for input sources - implement to add new sources"""

    @property
    def fileno(self) -> int:
        """File descriptor for select()"""
        ...

    def read(self) -> InputEvent | None:
        """Read and return input, or None if nothing available"""
        ...

    @property
    def name(self) -> str:
        """Source identifier for logging/display"""
        ...

    def close(self) -> None:
        """Cleanup resources"""
        ...


class StdinSource:
    """Standard input from terminal"""

    @property
    def fileno(self) -> int:
        return sys.stdin.fileno()

    def read(self) -> InputEvent | None:
        try:
            line = sys.stdin.readline()
            if not line:
                return None
            return InputEvent(text=line.strip(), source=self.name)
        except EOFError:
            return None

    @property
    def name(self) -> str:
        return "stdin"

    def close(self) -> None:
        pass  # Don't close stdin


class FifoSource:
    """FIFO named pipe input (receives JSON from Vim)"""

    def __init__(self, path: str = "/tmp/robert-dict.fifo"):
        self.path = path
        self._fd: int | None = None
        self._file: IO[str] | None = None

    def _ensure_fifo(self):
        """Create FIFO if it doesn't exist"""
        if not os.path.exists(self.path):
            os.mkfifo(self.path)
            logger.info(f"Created FIFO at {self.path}")

    @property
    def fileno(self) -> int:
        if self._file is None:
            self._ensure_fifo()
            # O_RDONLY | O_NONBLOCK: non-blocking read
            self._fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
            self._file = os.fdopen(self._fd, "r")
        return self._file.fileno()

    def read(self) -> InputEvent | None:
        """Read JSON line from FIFO"""
        if self._file is None:
            return None

        try:
            line = self._file.readline().strip()
            if not line:
                return None

            data = json.loads(line)
            return InputEvent(
                text=data.get("selection", ""),
                source=self.name,
                metadata=data,  # Contains: selection, phrase, paragraph, file
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from FIFO: {e}")
            return None
        except Exception as e:
            logger.debug(f"FIFO read error: {e}")
            return None

    @property
    def name(self) -> str:
        return "fifo"

    def close(self) -> None:
        if self._file:
            with contextlib.suppress(Exception):
                self._file.close()
            self._file = None
            self._fd = None


class InputMultiplexer:
    """Multiplexes multiple input sources using select()"""

    def __init__(self, sources: list[InputSource] | None = None):
        self._sources: list[InputSource] = sources or []
        self._fd_to_source: dict[int, InputSource] = {}
        self._rebuild_map()

    def _rebuild_map(self):
        """Rebuild fd -> source mapping"""
        self._fd_to_source = {s.fileno: s for s in self._sources}

    def add_source(self, source: InputSource) -> None:
        """Add a new input source (Open for extension)"""
        self._sources.append(source)
        self._fd_to_source[source.fileno] = source

    def remove_source(self, source: InputSource) -> None:
        """Remove an input source"""
        if source in self._sources:
            self._sources.remove(source)
            self._rebuild_map()

    @property
    def sources(self) -> list[InputSource]:
        """List of active sources"""
        return self._sources.copy()

    def wait_for_input(self, timeout: float = 0.5) -> InputEvent | None:
        """Wait for input from any source

        Args:
            timeout: How long to wait (seconds). Use 0 for non-blocking.

        Returns:
            InputEvent if input available, None otherwise
        """
        if not self._sources:
            return None

        try:
            fds = [s.fileno for s in self._sources]
            readable, _, _ = select.select(fds, [], [], timeout)
        except (OSError, ValueError) as e:
            logger.debug(f"Select error: {e}")
            return None

        for fd in readable:
            source = self._fd_to_source.get(fd)
            if source:
                event = source.read()
                if event:
                    return event

        return None

    def close(self) -> None:
        """Close all sources"""
        for source in self._sources:
            source.close()
        self._sources.clear()
        self._fd_to_source.clear()
