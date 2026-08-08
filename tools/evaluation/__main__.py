"""Developer key-hit benchmark entry (not a product mode).

Usage:
    python -m tools.evaluation
    python -m tools.evaluation --verbose --calib-geom-debug

The evaluation entry itself enables auto-benchmark after calib+preview.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from gazekey.app_config import apply_config, parse_evaluation_args
from gazekey.ui.virtual_keyboard import VirtualKeyboard
from tools.devtools_install import install_devtools


def main(argv: list[str] | None = None) -> int:
    apply_config(parse_evaluation_args(argv))

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
    print("Auto-benchmark runs after successful calibration + preview.")
    print("Product launch remains: python main.py")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
