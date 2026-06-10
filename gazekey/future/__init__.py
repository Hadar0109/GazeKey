"""Future gaze interaction (intent, selection, dwell typing) — dormant in MVP (T052).

Re-exports preserved modules for when gaze-typing is re-enabled. The active MVP
preview path does not use these symbols; dormant wiring imports from here only.
"""

from gazekey.future.intent import KeyIntentScore, score_keys
from gazekey.future.selection import SelectionPolicy, SelectionState
from gazekey.future.typing import DwellSelector, DwellState, GazeTypingController

__all__ = [
    "DwellSelector",
    "DwellState",
    "GazeTypingController",
    "KeyIntentScore",
    "SelectionPolicy",
    "SelectionState",
    "score_keys",
]
