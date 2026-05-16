"""Map keyboard button labels to typing actions."""

from PySide6.QtWidgets import QPushButton


def action_from_button(button: QPushButton) -> str:
    """Return the action string for a key button (matches mouse click handlers)."""
    return action_from_label(button.text())


def action_from_label(label: str) -> str:
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
