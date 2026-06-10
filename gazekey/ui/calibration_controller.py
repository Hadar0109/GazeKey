"""Minimal calibration boundary: start session, overlay, and summary hooks (FR-017)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from PySide6.QtWidgets import QApplication, QWidget

from gazekey.calibration2.calibration_csv import CalibrationCsvLogger
from gazekey.calibration2.fixation_gate import FixationGateConfig
from gazekey.calibration2.session import CalibrationV2Result, CalibrationV2Session
from gazekey.calibration2.targets import keyboard_geometry_targets
from gazekey.layout.layout_inspector import inspect_keyboard_layout
from gazekey.mapping.typing_candidate import CALIBRATION_MODE
from gazekey.typing.gaze_ui_mapper import letter_keys_region_rect
from gazekey.ui.calibration_overlay import CalibrationOverlay
from gazekey.ui.env_flags import calib_mode_override


@dataclass(frozen=True)
class CalibrationStartContext:
    overlay: CalibrationOverlay
    session: CalibrationV2Session
    csv_logger: CalibrationCsvLogger
    calib_mode: str
    calib_clip_rect: Tuple[float, float, float, float]
    dot_targets: List[Tuple[float, float]]
    screen_targets: List[Tuple[float, float]]


class CalibrationController:
    """
    Owns calibration v2 session lifecycle boundaries.

    App orchestration (mapper fit, quality gates, gaze loop) stays in VirtualKeyboard.
    """

    def __init__(self) -> None:
        self.session: Optional[CalibrationV2Session] = None
        self.csv_logger: Optional[CalibrationCsvLogger] = None
        self.overlay: Optional[CalibrationOverlay] = None
        self.calib_mode: str = ""
        self.calib_clip_rect: Optional[Tuple[float, float, float, float]] = None

    @property
    def session_id(self) -> str:
        if self.csv_logger is None:
            return ""
        return str(self.csv_logger.session_id)

    def reset(self) -> None:
        if self.overlay is not None:
            try:
                self.overlay.close()
            except Exception:
                pass
        self.session = None
        self.csv_logger = None
        self.overlay = None
        self.calib_mode = ""
        self.calib_clip_rect = None

    def start(
        self,
        *,
        keyboard_widget: QWidget,
        on_finished: Callable[[CalibrationV2Result], None],
        gate_cfg: FixationGateConfig,
        calibration_mode: str = CALIBRATION_MODE,
        max_timeouts_per_target: int = 1,
        on_timeout: str = "retry",
    ) -> CalibrationStartContext:
        self.reset()

        # Dev override so T032 candidate layouts can be selected without editing config
        # (mirrors GAZEKEY_DEV_BENCHMARK). Falls back to the configured mode.
        resolved_mode = calib_mode_override() or calibration_mode

        screen = QApplication.primaryScreen().geometry()
        # letter_keys_region_rect() is the full keyboard-widget rect (all rows, no
        # calibrate bar); it already spans the interactive keyboard vertically.
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

        dot_targets = [(t.screen_x - screen.x(), t.screen_y - screen.y()) for t in targets]
        screen_targets = [(t.screen_x, t.screen_y) for t in targets]

        self.csv_logger = CalibrationCsvLogger(enabled=True)
        self.csv_logger.begin_calibration_run()
        self.session = CalibrationV2Session(
            targets=targets,
            csv_logger=self.csv_logger,
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
            csv_logger=self.csv_logger,
            calib_mode=self.calib_mode,
            calib_clip_rect=self.calib_clip_rect,
            dot_targets=dot_targets,
            screen_targets=screen_targets,
        )
