"""Pynput-backed OS input adapter — sole product import site for pynput."""

from __future__ import annotations

from pynput.keyboard import Controller, Key

from gazekey.input.os_input_adapter import OsInjectResult
from gazekey.typing.key_action import KeyAction, KeyActionKind


class PynputOsInputAdapter:
    """Inject CHAR / BACKSPACE / ENTER via ``pynput.keyboard.Controller``."""

    def __init__(self) -> None:
        self._controller = Controller()

    def inject(self, action: KeyAction) -> OsInjectResult:
        try:
            if action.kind is KeyActionKind.CHAR:
                if not action.text:
                    return OsInjectResult(ok=False, error="missing_char_text")
                self._controller.type(action.text)
            elif action.kind is KeyActionKind.BACKSPACE:
                self._controller.press(Key.backspace)
                self._controller.release(Key.backspace)
            elif action.kind is KeyActionKind.ENTER:
                self._controller.press(Key.enter)
                self._controller.release(Key.enter)
            else:
                return OsInjectResult(ok=False, error=f"unsupported_kind:{action.kind}")
            return OsInjectResult(ok=True)
        except Exception as exc:  # noqa: BLE001 — boundary must not crash callers
            return OsInjectResult(ok=False, error=str(exc)[:200])
