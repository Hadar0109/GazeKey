"""Map keyboard button labels to typing actions and OS-bound roles."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from PySide6.QtWidgets import QPushButton

from gazekey.typing.key_action import KeyAction, KeyActionKind, KeyActionSource


class KeyRole(str, Enum):
    """Semantic role for dwell/runtime handling (data-model ActiveTypingKey)."""

    LETTER = "letter"
    SPACE = "space"
    BACKSPACE = "backspace"
    ENTER = "enter"
    SHIFT_ONESHOT = "shift_oneshot"
    SYSTEM_PAUSE_RESUME = "pause_resume"
    SUGGESTION = "suggestion"
    NON_OS = "non_os"


PAUSE_RESUME_ACTION = "PAUSE_RESUME"
SUGGESTION_KEY_ID_PREFIX = "suggestion:"
_PAUSE_RESUME_LABELS = frozenset(
    {
        "Pause",
        "Resume",
        "⏸ Pause",
        "▶ Resume",
    }
)


def action_from_button(button: QPushButton) -> str:
    """Return the action string for a key button (matches mouse click handlers)."""
    override = button.property("gazeKeyAction")
    if override:
        return str(override)
    return action_from_label(button.text())


def action_from_label(label: str) -> str:
    if label in _PAUSE_RESUME_LABELS:
        return PAUSE_RESUME_ACTION
    if label == "⌫":
        return "BACKSPACE"
    if label == "Space":
        return " "
    if label == "↵":
        return "ENTER"
    if label == "Shift":
        return "SHIFT"
    if label == "Ctrl":
        return "CTRL"
    if label == "Alt":
        return "ALT"
    if label == "&&":
        return "&"
    return label


def is_suggestion_action(action: str) -> bool:
    return str(action).startswith(SUGGESTION_KEY_ID_PREFIX)


def suggestion_slot_index(action_or_key_id: str) -> Optional[int]:
    text = str(action_or_key_id)
    if not text.startswith(SUGGESTION_KEY_ID_PREFIX):
        return None
    try:
        return int(text[len(SUGGESTION_KEY_ID_PREFIX) :])
    except ValueError:
        return None


def role_for_action(action: str) -> KeyRole:
    """Classify a key action for OS-bound vs non-OS handling."""
    if action == PAUSE_RESUME_ACTION:
        return KeyRole.SYSTEM_PAUSE_RESUME
    if is_suggestion_action(action):
        return KeyRole.SUGGESTION
    if action == "SHIFT":
        return KeyRole.SHIFT_ONESHOT
    if action in ("CTRL", "ALT"):
        return KeyRole.NON_OS
    if action == "BACKSPACE":
        return KeyRole.BACKSPACE
    if action == "ENTER":
        return KeyRole.ENTER
    if action == " ":
        return KeyRole.SPACE
    if len(action) == 1 and action.isalpha() and action.upper() >= "A" and action.upper() <= "Z":
        return KeyRole.LETTER
    return KeyRole.NON_OS


def is_os_bound_action(action: str) -> bool:
    """True for A–Z, Space, Backspace, Enter (emit OS KeyAction when session active)."""
    return role_for_action(action) in {
        KeyRole.LETTER,
        KeyRole.SPACE,
        KeyRole.BACKSPACE,
        KeyRole.ENTER,
    }


def is_shift_action(action: str) -> bool:
    return role_for_action(action) is KeyRole.SHIFT_ONESHOT


def is_pause_resume_action(action: str) -> bool:
    return role_for_action(action) is KeyRole.SYSTEM_PAUSE_RESUME


def builds_os_key_action(
    action: str,
    *,
    key_id: str,
    source: KeyActionSource,
    timestamp: float,
    shift_armed: bool,
) -> Optional[KeyAction]:
    """
    Build an OS-bound KeyAction, or None for Shift / Ctrl / Alt / other non-OS.

    Letter casing uses ``shift_armed``; caller must consume Shift after a letter.
    """
    role = role_for_action(action)
    if role is KeyRole.LETTER:
        ch = action.upper() if shift_armed else action.lower()
        return KeyAction(
            kind=KeyActionKind.CHAR,
            text=ch,
            source=source,
            key_id=key_id,
            timestamp=timestamp,
        )
    if role is KeyRole.SPACE:
        return KeyAction(
            kind=KeyActionKind.CHAR,
            text=" ",
            source=source,
            key_id=key_id,
            timestamp=timestamp,
        )
    if role is KeyRole.BACKSPACE:
        return KeyAction(
            kind=KeyActionKind.BACKSPACE,
            source=source,
            key_id=key_id,
            timestamp=timestamp,
        )
    if role is KeyRole.ENTER:
        return KeyAction(
            kind=KeyActionKind.ENTER,
            source=source,
            key_id=key_id,
            timestamp=timestamp,
        )
    return None
