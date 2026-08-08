"""
GazeKey - Main entry point
"""

import sys

from PySide6.QtWidgets import QApplication

from gazekey.app_config import apply_config, parse_product_args
from gazekey.ui.virtual_keyboard import VirtualKeyboard


def main(argv: list[str] | None = None) -> None:
    """Initialize and run the application."""
    apply_config(parse_product_args(argv))

    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("GazeKey")
    app.setOrganizationName("GazeKey")

    # Create and show virtual keyboard
    keyboard = VirtualKeyboard()
    keyboard.show()
    keyboard.on_app_started()

    print("GazeKey started!")
    print("- Gaze-dwell or click keys to type into the focused external app")
    print("- Drag the window to reposition")
    print("- Press minimize to hide")
    print("- Close the window to exit")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
