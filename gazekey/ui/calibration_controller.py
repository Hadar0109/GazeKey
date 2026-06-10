"""Minimal calibration boundary: start session, overlay, and summary hooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from PySide6.QtWidgets import QApplication, QWidget

from gazekey.calibration.fixation_gate import FixationGateConfig
from gazekey.calibration.session import CalibrationResult, CalibrationSession
from gazekey.calibration.targets import keyboard_geometry_targets
from gazekey.evaluation.session import new_session_id
from gazekey.layout.layout_inspector import inspect_keyboard_layout
from gazekey.mapping.config import CALIBRATION_MODE
from gazekey.typing.gaze_ui_mapper import letter_keys_region_rect
from gazekey.ui.calibration_overlay import CalibrationOverlay
from gazekey.ui.env_flags import calib_mode_override


@dataclass(frozen=True)
class CalibrationStartContext:
    overlay: CalibrationOverlay
    session: CalibrationSession
    session_id: str
    calib_mode: str
    calib_clip_rect: Tuple[float, float, float, float]
    dot_targets: List[Tuple[float, float]]
    screen_targets: List[Tuple[float, float]]


class CalibrationController:
    """Owns calibration session lifecycle boundaries."""

    def __init__(self) -> None:
        self.session: Optional[CalibrationSession] = None
        self.session_id: str = ""
        self.overlay: Optional[CalibrationOverlay] = None
        self.calib_mode: str = ""
        self.calib_clip_rect: Optional[Tuple[float, float, float, float]] = None

    def reset(self) -> None:
        if self.overlay is not None:
            try:
                self.overlay.close()
            except Exception:
                pass
        self.session = None
        self.session_id = ""
        self.overlay = None
        self.calib_mode = ""
        self.calib_clip_rect = None

    def start(
        self,
        *,
        keyboard_widget: QWidget,
        on_finished: Callable[[CalibrationResult], None],
        gate_cfg: FixationGateConfig,
        calibration_mode: str = CALIBRATION_MODE,
        max_timeouts_per_target: int = 1,
        on_timeout: str = "retry",
    ) -> CalibrationStartContext:
        self.reset()
        resolved_mode = calib_mode_override() or calibration_mode
        screen = QApplication.primaryScreen().geometry()
        region_rect = letter_keys_region_rect(keyboard_widget)
        self.calib_clip_rect = (
            float(region_rect.x()),
            float(region_rect.y()),
            float(region_rect.width()),
            float(region_rect.height()),
        )
        layout_keys = inspect_keyboard_layout(keyboard_widget)
        targets = keyboard_geometry_targets(
            keys=layout_keys,
            typing_region_rect=region_rect,
            mode=resolved_mode,
            screen_rect=screen,
        )
        self.calib_mode = resolved_mode
        self.session_id = new_session_id()

        dot_targets = [(t.screen_x - screen.x(), t.screen_y - screen.y()) for t in targets]
        screen_targets = [(t.screen_x, t.screen_y) for t in targets]

        self.session = CalibrationSession(
            targets=targets,
            session_id=self.session_id,
            calibration_version=6,
            calibration_mode=self.calib_mode,
            gate_cfg=gate_cfg,
            max_timeouts_per_target=max_timeouts_per_target,
            on_timeout=on_timeout,
        )

        self.overlay = CalibrationOverlay(
            dot_targets=dot_targets,
            screen_targets=screen_targets,
            on_finished=on_finished,
            session=self.session,
            minimal_fixation_ui=True,
        )
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()

        return CalibrationStartContext(
            overlay=self.overlay,
            session=self.session,
            session_id=self.session_id,
            calib_mode=self.calib_mode,
            calib_clip_rect=self.calib_clip_rect,
            dot_targets=dot_targets,
            screen_targets=screen_targets,
        )
