"""Developer read-only gaze preview entry (not a product mode).

Usage:
    python -m tools.preview
    python -m tools.preview --verbose --gaze-debug
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from gazekey.app_config import apply_config, parse_preview_args
from gazekey.ui.virtual_keyboard import VirtualKeyboard
from tools.devtools_install import install_devtools


def main(argv: list[str] | None = None) -> int:
    apply_config(parse_preview_args(argv))

    app = QApplication(sys.argv)
    app.setApplicationName("GazeKey Preview (tools)")
    keyboard = VirtualKeyboard()
    install_devtools(
        keyboard,
        enable_preview=True,
        enable_benchmark=False,
        auto_preview_after_calib=True,
    )
    keyboard.show()
    keyboard.on_app_started()
    print("GazeKey tools preview started (read-only gaze after calibration).")
    print("Product launch remains: python main.py")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
