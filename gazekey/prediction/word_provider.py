"""WordProvider protocol — UI/typing depend on this abstraction only."""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable


@runtime_checkable
class WordProvider(Protocol):
    """Prefix → ranked completion words (≤3). Implemented in Phase 3."""

    def suggest(self, prefix: str) -> List[str]:
        """Return up to 3 completions for ``prefix`` (frequency-ranked)."""
        ...
