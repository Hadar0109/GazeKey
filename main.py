"""
GazeKey - Main entry point
"""

import sys
from PySide6.QtWidgets import QApplication
from gazekey.ui.virtual_keyboard import VirtualKeyboard


def main():
    """Initialize and run the application"""
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("GazeKey")
    app.setOrganizationName("GazeKey")
    
    # Create and show virtual keyboard
    keyboard = VirtualKeyboard()
    keyboard.show()
    
    print("GazeKey started!")
    print("- Click keys to test")
    print("- Drag the window to reposition")
    print("- Press minimize to hide")
    print("- Close the window to exit")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
