"""Production startup sequence: official GazeFollower then the existing keyboard."""

from __future__ import annotations

from typing import Any

from gazekey.backend.debug_gaze_dot import DebugGazeOverlay
from gazekey.backend.geometry_audit import build_live_audit, write_geometry_audit
from gazekey.backend.lifecycle import GazeFollowerLifecycle
from gazekey.backend.provenance import product_interpreter_path, provenance_record


def run_official_startup(lifecycle: GazeFollowerLifecycle) -> None:
    """Preview → 13-point Calibration → pygame.quit → start_sampling.

    Must run before QApplication / VirtualKeyboard construction.
    """
    lifecycle.construct()
    lifecycle.preview()
    lifecycle.calibrate()
    lifecycle.quit_pygame()
    lifecycle.start_sampling()


def record_live_geometry(lifecycle: GazeFollowerLifecycle, keyboard: Any) -> Any:
    """T028: fill the T011 audit from the live keyboard session."""
    builder = getattr(keyboard, "_keyboard_layout_builder", None)
    if builder is not None:
        builder.export_keyboard_layout()
    audit, geometry = build_live_audit(
        keyboard=keyboard,
        pygame_mode=lifecycle.pygame_mode,
        gf_screen_size=lifecycle.gf_screen_size,
    )
    lifecycle.geometry = geometry
    return write_geometry_audit(
        audit,
        extra={
            "interpreter": product_interpreter_path(),
            "provenance": provenance_record(),
        },
    )


def wire_debug_gaze_dot(lifecycle: GazeFollowerLifecycle, keyboard: Any) -> Any:
    """Stage C debug overlay: official-sized GREEN ring via gf.get_gaze_info()."""
    geom = getattr(lifecycle, "geometry", None)
    dpr = float(geom.dpr) if geom is not None else 1.0
    overlay = DebugGazeOverlay(keyboard, dpr=dpr)
    keyboard._gf_debug_overlay = overlay
    bridge = lifecycle.attach_debug_get_gaze_info_bridge(overlay, parent=keyboard)
    bridge.start()
    keyboard._gf_sample_bridge = bridge
    return bridge
