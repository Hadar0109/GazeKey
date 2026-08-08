"""KeyAction — requested OS-bound typing action (contracts/key-action.md)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class KeyActionKind(str, Enum):
    """Semantic kind delivered through the OS input boundary."""

    CHAR = "CHAR"
    BACKSPACE = "BACKSPACE"
    ENTER = "ENTER"


class KeyActionSource(str, Enum):
    """How the selection that produced this action was made."""

    DWELL = "dwell"
    MOUSE = "mouse"


@dataclass(frozen=True)
class KeyAction:
    """Requested semantic action for ActionDispatcher → OsInputAdapter."""

    kind: KeyActionKind
    source: KeyActionSource
    key_id: str
    timestamp: float
    text: Optional[str] = None  # CHAR only; already cased if Shift oneshot armed
