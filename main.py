"""
GazeKey - Main entry point

Feature 005 production path: official GazeFollower Preview + Calibration,
then sampling, then the existing Qt keyboard. GazeKey camera capture is unused.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _reexec_project_venv() -> None:
    """Use the project .venv so `python main.py` does not need the venv path."""
    root = Path(__file__).resolve().parent
    venv_python = root / ".venv" / ("Scripts" if os.name == "nt" else "bin") / (
        "python.exe" if os.name == "nt" else "python"
    )
    if not venv_python.is_file():
        return
    try:
        if Path(sys.executable).resolve() == venv_python.resolve():
            return
    except OSError:
        pass
    raise SystemExit(subprocess.call([str(venv_python), *sys.argv]))


_reexec_project_venv()

from gazekey.app_config import apply_config, parse_product_args
from gazekey.backend.lifecycle import (
    GazeFollowerLifecycle,
    GazeFollowerLifecycleError,
)
from gazekey.backend.startup import (
    record_dpi_probe,
    record_live_geometry,
    run_official_startup,
    wire_debug_gaze_dot,
    wire_official_gaze_typing,
)


def main(argv: list[str] | None = None) -> int:
    """Official GazeFollower pygame UI, then the existing GazeKey keyboard."""
    apply_config(parse_product_args(argv))

    lifecycle = GazeFollowerLifecycle()
    try:
        run_official_startup(lifecycle)
    except GazeFollowerLifecycleError:
        try:
            lifecycle.release()
        except Exception:
            pass
        return 1

    from PySide6.QtWidgets import QApplication

    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    app = QApplication(sys.argv)
    app.setApplicationName("GazeKey")
    app.setOrganizationName("GazeKey")

    keyboard = VirtualKeyboard()
    keyboard.show()
    keyboard.on_app_started()
    record_live_geometry(lifecycle, keyboard)
    probe_path = record_dpi_probe(lifecycle)
    wire_debug_gaze_dot(lifecycle, keyboard)
    wire_official_gaze_typing(lifecycle, keyboard)
    app.aboutToQuit.connect(lifecycle.release)

    print("GazeKey started (GazeFollower backend)!")
    print("- GREEN ring = official filtered gaze (origin+dpr)")
    print("- Dwell/OS typing consume GazeSample. Invalid gaze cancels dwell.")
    if probe_path is not None:
        print(f"- DPI probe: {probe_path}")
    print("- Close the window to exit")

    return int(app.exec())


if __name__ == "__main__":
    sys.exit(main())
