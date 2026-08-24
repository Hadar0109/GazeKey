"""Production startup sequence: official GazeFollower then the existing keyboard."""

from __future__ import annotations

from typing import Any

from gazekey.backend.debug_gaze_dot import DebugGazeOverlay
from gazekey.backend.display_probe import (
    PHASE_AFTER_CALIBRATE,
    PHASE_AFTER_PYGAME_QUIT,
    PHASE_AFTER_QT_KEYBOARD,
    PHASE_AFTER_START_SAMPLING,
    DisplayProbe,
)
from gazekey.backend.geometry_audit import build_live_audit, write_geometry_audit
from gazekey.backend.lifecycle import GazeFollowerLifecycle, GazeFollowerLifecycleError
from gazekey.backend.provenance import product_interpreter_path, provenance_record


def _probe_for(lifecycle: GazeFollowerLifecycle) -> DisplayProbe:
    probe = getattr(lifecycle, "_display_probe", None)
    if not isinstance(probe, DisplayProbe):
        probe = DisplayProbe()
        lifecycle._display_probe = probe
    return probe


def _capture(
    lifecycle: GazeFollowerLifecycle, phase: str, *, include_qt: bool = False
) -> None:
    try:
        _probe_for(lifecycle).capture(phase, lifecycle, include_qt=include_qt)
    except Exception:
        pass


def run_official_startup(lifecycle: GazeFollowerLifecycle) -> None:
    """Preview → 13-point Calibration → pygame.quit → start_sampling.

    Must run before QApplication / VirtualKeyboard construction.
    """
    _probe_for(lifecycle)
    lifecycle.construct()
    lifecycle.preview()
    lifecycle.calibrate()
    _capture(lifecycle, PHASE_AFTER_CALIBRATE)
    if not lifecycle.calibration_accepted():
        lifecycle._cleanup_after_failure()
        lifecycle._fail_closed(
            "calibrate() (not accepted)",
            RuntimeError("official calibration was not accepted"),
        )
    lifecycle.quit_pygame()
    _capture(lifecycle, PHASE_AFTER_PYGAME_QUIT)
    lifecycle.start_sampling()
    _capture(lifecycle, PHASE_AFTER_START_SAMPLING)


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


def record_dpi_probe(lifecycle: GazeFollowerLifecycle, path: Any = None) -> Any:
    """Write the four-phase pygame.quit → Qt display/DPI probe. Best-effort."""
    _capture(lifecycle, PHASE_AFTER_QT_KEYBOARD, include_qt=True)
    try:
        return _probe_for(lifecycle).write(path)
    except Exception:
        return None


def wire_debug_gaze_dot(lifecycle: GazeFollowerLifecycle, keyboard: Any) -> Any:
    """Stage C debug overlay: GREEN official-style origin+dpr ring."""
    existing = getattr(keyboard, "_gf_debug_overlay", None)
    if existing is not None:
        try:
            existing.hide()
        except Exception:
            pass
    geom = getattr(lifecycle, "geometry", None)
    dpr = float(geom.dpr) if geom is not None else 1.0
    overlay = DebugGazeOverlay(keyboard, dpr=dpr)
    keyboard._gf_debug_overlay = overlay
    bridge = lifecycle.attach_debug_get_gaze_info_bridge(overlay, parent=keyboard)
    bridge.start()
    keyboard._gf_sample_bridge = bridge
    return bridge


def wire_official_gaze_typing(lifecycle: GazeFollowerLifecycle, keyboard: Any) -> Any:
    """Stage D: GazeSample queue → MappedGazePoint → existing dwell / OS typing."""
    keyboard._gf_lifecycle = lifecycle
    keyboard._official_gaze_ready = True
    ensure = getattr(keyboard, "_ensure_typing_auto_started", None)
    if callable(ensure):
        ensure()
    bridge = lifecycle.attach_qt_bridge(parent=keyboard)
    loop = getattr(keyboard, "_gaze_loop", None)
    if loop is not None and hasattr(bridge, "sample_ready"):
        bridge.sample_ready.connect(loop.on_gaze_sample)
    bridge.start()
    keyboard._gf_typing_bridge = bridge
    return bridge


def _show_keyboard(keyboard: Any) -> None:
    show = getattr(keyboard, "show", None)
    if callable(show):
        show()
    raise_ = getattr(keyboard, "raise_", None)
    if callable(raise_):
        raise_()
    activate = getattr(keyboard, "activateWindow", None)
    if callable(activate):
        activate()


def _schedule_qt_consumer_resume(lifecycle: GazeFollowerLifecycle, keyboard: Any) -> None:
    """Rewire debug ring + typing consumers on the next Qt tick after pygame.quit()."""

    def _resume(
        life: GazeFollowerLifecycle = lifecycle, kb: Any = keyboard
    ) -> None:
        wire_debug_gaze_dot(life, kb)
        wire_official_gaze_typing(life, kb)

    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
    except Exception:
        _resume()
        return
    app = QApplication.instance()
    if app is None:
        _resume()
        return
    QTimer.singleShot(0, _resume)


def run_official_recalibrate(lifecycle: GazeFollowerLifecycle, keyboard: Any) -> bool:
    """Hide Qt, official Preview+Calibration from scratch. Resume only if the new model is usable."""
    from PySide6.QtWidgets import QApplication

    runtime = getattr(keyboard, "_typing_runtime", None)
    if runtime is not None:
        runtime.set_os_inject_enabled(False)
        runtime.dwell.cancel_progress()
    lifecycle.stop_qt_bridge()
    hide = getattr(keyboard, "hide", None)
    if callable(hide):
        hide()
    app = QApplication.instance()
    if app is not None:
        app.processEvents()

    usable = False
    try:
        lifecycle.stop_sampling()
        lifecycle.preview(cleanup_on_failure=False)
        lifecycle.calibrate(cleanup_on_failure=False)
        lifecycle.quit_pygame()
        usable = lifecycle.calibration_model_usable()
        if usable:
            lifecycle.resume_sampling_after_pygame()
    except GazeFollowerLifecycleError:
        try:
            lifecycle.quit_pygame()
        except Exception:
            pass
        lifecycle._return_camera_to_closing()
        usable = False
    finally:
        _show_keyboard(keyboard)

    if not usable:
        lifecycle.invalidate_live_calibration()
        if hasattr(keyboard, "_official_gaze_ready"):
            keyboard._official_gaze_ready = False
        if runtime is not None:
            runtime.set_os_inject_enabled(False)
        lifecycle._fail_closed(
            "recalibrate (new calibration not usable)",
            RuntimeError("official calibration was not accepted"),
        )
    _schedule_qt_consumer_resume(lifecycle, keyboard)
    return True
