"""Internal text buffer for gaze/mouse typing."""

from PySide6.QtWidgets import QLineEdit


class TextBufferController:
    """Apply keyboard actions to a QLineEdit text buffer."""

    def __init__(self, line_edit: QLineEdit) -> None:
        self._line_edit = line_edit

    def apply_key(self, action: str, shift_active: bool = False) -> None:
        if action in ("CTRL", "ALT", "SHIFT"):
            return

        if action == "BACKSPACE":
            text = self._line_edit.text()
            if text:
                self._line_edit.setText(text[:-1])
            return

        if action == "ENTER":
            self._line_edit.setText(self._line_edit.text() + "\n")
            return

        if action == " ":
            self._insert_char(" ")
            return

        if len(action) == 1:
            ch = action.upper() if shift_active and action.isalpha() else action
            self._insert_char(ch)
            return

    def _insert_char(self, ch: str) -> None:
        self._line_edit.setText(self._line_edit.text() + ch)

    def text(self) -> str:
        return self._line_edit.text()

    def clear(self) -> None:
        self._line_edit.clear()
