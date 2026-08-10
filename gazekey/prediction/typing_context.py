"""TypingContext — delivery-only prefix tracking (implemented in Phase 3)."""

from __future__ import annotations


class TypingContext:
    """Tracks in-progress word prefix from successful deliveries. Stub until T021."""

    def __init__(self) -> None:
        self.prefix: str = ""
        self.prefix_epoch: int = 0
        self.shift_armed: bool = False
