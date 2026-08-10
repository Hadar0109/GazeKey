"""TypingContext — delivery-only prefix tracking for prediction."""

from __future__ import annotations

from gazekey.typing.key_action import KeyAction, KeyActionKind


class TypingContext:
    """
    Tracks in-progress word prefix from successful OS deliveries only.

    Updates exclusively via ``on_action_delivered`` with ``ok=True``.
    Suggestion accept must not call a separate ``clear_prefix()`` — Space
    delivery clears the prefix through the normal rules.
    """

    def __init__(self) -> None:
        self.prefix: str = ""
        self.prefix_epoch: int = 0
        self.shift_armed: bool = False

    def get_prefix(self) -> str:
        return self.prefix

    def get_epoch(self) -> int:
        return self.prefix_epoch

    def set_shift_armed(self, armed: bool) -> None:
        self.shift_armed = bool(armed)

    def on_action_delivered(self, action: KeyAction, *, ok: bool) -> bool:
        """
        Apply a delivered action. Returns True if ``prefix`` / epoch changed.
        """
        if not ok:
            return False

        kind = action.kind
        if kind is KeyActionKind.CHAR:
            text = action.text or ""
            if not text:
                return False
            if text == " ":
                return self._clear_prefix()
            if len(text) == 1 and text.isalpha():
                return self._append_letter(text.lower())
            return False

        if kind is KeyActionKind.BACKSPACE:
            if not self.prefix:
                return False
            self.prefix = self.prefix[:-1]
            self.prefix_epoch += 1
            return True

        if kind is KeyActionKind.ENTER:
            return self._clear_prefix()

        return False

    def _append_letter(self, ch: str) -> bool:
        self.prefix = self.prefix + ch
        self.prefix_epoch += 1
        return True

    def _clear_prefix(self) -> bool:
        if self.prefix == "":
            # Still bump epoch when Space/Enter lands on empty so UI can refresh.
            self.prefix_epoch += 1
            return True
        self.prefix = ""
        self.prefix_epoch += 1
        return True
