"""WordProvider protocol — UI/typing depend on this abstraction only."""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable


@runtime_checkable
class WordProvider(Protocol):
    """Prefix → ranked completion words (≤3 by default)."""

    def suggest(self, prefix: str, *, limit: int = 3) -> List[str]:
        """Return up to ``limit`` completion words for ``prefix``."""
        ...
