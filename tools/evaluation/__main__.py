"""Developer key-hit benchmark entry (not a product mode).

Usage:
    python -m tools.evaluation

Optional:
    set GAZEKEY_DEV_BENCHMARK=1  — auto-start benchmark after calibration+preview
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from gazekey.ui.virtual_keyboard import VirtualKeyboard
from tools.devtools_install import install_devtools


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("GazeKey Benchmark (tools)")
    keyboard = VirtualKeyboard()
    install_devtools(
        keyboard,
        enable_preview=True,
        enable_benchmark=True,
        auto_preview_after_calib=True,
    )
    keyboard.show()
    keyboard.on_app_started()
    print("GazeKey tools evaluation/benchmark started.")
    print("Set GAZEKEY_DEV_BENCHMARK=1 to auto-run the 15-key benchmark after calib.")
    print("Product launch remains: python main.py")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
