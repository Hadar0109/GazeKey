"""Fullscreen calibration overlay.

Supports two paths:
- Legacy v1 calibration session (gaze_h/gaze_v ratios)
- Calibration v2 session (FrameFeatures + gating), used by `VirtualKeyboard`
"""

from __future__ import annotations

import os
from typing import Callable, List, Optional, Tuple, Union

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QApplication,
)

from gazekey.calibration.calibration_session import (
    CalibrationSession,
    CalibrationResult,
    Phase,
    PREPARE_MS,
)
from gazekey.calibration2.session import CalibrationV2Result, CalibrationV2Session
from gazekey.features.feature_types import FrameFeatures


class CalibrationDotWidget(QWidget):
    """Draws the target dot at a screen-global position."""

    DOT_RADIUS = 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._target: Optional[Tuple[float, float]] = None
        self._pulse_phase = 0

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._on_pulse)
        self._pulse_timer.start(50)

    def set_target(self, x: float, y: float) -> None:
        self._target = (x, y)
        self.update()

    def _on_pulse(self) -> None:
        self._pulse_phase = (self._pulse_phase + 1) % 20
        if self._target is not None:
            self.update()

    def paintEvent(self, event):
        if self._target is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Targets are in overlay-local coordinates
        local_x, local_y = self._target[0], self._target[1]

        scale = 1.0 + 0.15 * (self._pulse_phase / 20.0)
        radius = int(self.DOT_RADIUS * scale)

        painter.setPen(QPen(QColor(255, 255, 255, 200), 3))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(
            int(local_x - radius),
            int(local_y - radius),
            radius * 2,
            radius * 2,
        )
        painter.end()


class CalibrationOverlay(QWidget):
    """
    Fullscreen calibration UI on the primary screen.

    Signals completion via on_finished callback.
    """

    def __init__(
        self,
        dot_targets: List[Tuple[float, float]],
        screen_targets: List[Tuple[float, float]],
        on_finished: Callable[[Union[CalibrationResult, CalibrationV2Result]], None],
        frame_w: float = 640.0,
        frame_h: float = 480.0,
        session_v2: CalibrationV2Session | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._dot_targets = dot_targets
        self._screen_targets = screen_targets
        self._on_finished = on_finished
        self._session_v2 = session_v2
        self._session = None if self._session_v2 is not None else CalibrationSession(screen_targets, frame_w=frame_w, frame_h=frame_h)
        self._result: Optional[Union[CalibrationResult, CalibrationV2Result]] = None
        self._v2_last_target_index: int = -1
        self._v2_collect_enabled: bool = False

        self._prepare_timer = QTimer(self)
        self._prepare_timer.setSingleShot(True)
        self._prepare_timer.timeout.connect(self._start_collect)

        self._success_close_timer = QTimer(self)
        self._success_close_timer.setSingleShot(True)
        self._success_close_timer.timeout.connect(self._emit_finished_and_close)

        self._setup_window()
        self._setup_ui()
        self._begin_current_point()

    @property
    def session(self) -> CalibrationSession:
        if self._session is None:
            raise RuntimeError("Legacy v1 session is not available when session_v2 is provided.")
        return self._session

    @property
    def session_v2(self) -> CalibrationV2Session:
        if self._session_v2 is None:
            raise RuntimeError("session_v2 is not set.")
        return self._session_v2

    def _setup_window(self) -> None:
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

    def _setup_ui(self) -> None:
        self.setStyleSheet("background-color: rgba(10, 10, 20, 230);")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Eye Calibration")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(title)

        self.status_label = QLabel("Look at the dot")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 16))
        self.status_label.setStyleSheet("color: #CCCCCC; background: transparent;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch()

        self.dot_widget = CalibrationDotWidget(self)
        self.dot_widget.setGeometry(self.rect())
        self.dot_widget.raise_()

        button_row = QHBoxLayout()
        button_row.addStretch()

        self.try_again_btn = QPushButton("Try again")
        self.try_again_btn.setMinimumSize(140, 48)
        self.try_again_btn.setFont(QFont("Segoe UI", 14))
        self.try_again_btn.setStyleSheet(self._button_style("#FF6B35"))
        self.try_again_btn.clicked.connect(self._restart)
        self.try_again_btn.hide()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumSize(140, 48)
        self.cancel_btn.setFont(QFont("Segoe UI", 14))
        self.cancel_btn.setStyleSheet(self._button_style("#555555"))
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.hide()

        button_row.addWidget(self.try_again_btn)
        button_row.addSpacing(16)
        button_row.addWidget(self.cancel_btn)
        button_row.addStretch()
        layout.addLayout(button_row)

    @staticmethod
    def _button_style(bg: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "dot_widget"):
            self.dot_widget.setGeometry(self.rect())
            if self._session_v2 is not None:
                idx = int(self._session_v2.target_index)
                if idx < len(self._dot_targets) and not self._session_v2.is_finished:
                    self.dot_widget.set_target(*self._dot_targets[idx])
            else:
                idx = self._session.point_index
                if idx < len(self._dot_targets) and not self._session.is_finished:
                    self.dot_widget.set_target(*self._dot_targets[idx])

    def add_sample(self, iris_x: float, iris_y: float) -> None:
        self.add_sample_dt(iris_x, iris_y, dt_ms=16.7)

    def add_sample_dt(self, gaze_h: float, gaze_v: float, dt_ms: float) -> None:
        """
        Feed one gaze sample into calibration.

        The session itself decides when a dot is "locked" and when collection
        is complete (fixation-style lock-on + completion).
        """
        if self._session_v2 is not None:
            # v2 path is driven by FrameFeatures; ignore v1 ratio samples.
            return

        if self._result is not None or self._session.is_finished:
            return

        if self._session.phase != Phase.COLLECT:
            return

        result = self._session.process_sample(gaze_h, gaze_v, dt_ms=dt_ms)
        if result is not None:
            self._show_result(result)
            return

        # Point completed and we advanced to the next dot.
        if self._session.phase == Phase.IDLE and not self._session.is_finished:
            self._begin_current_point()

    def add_features_dt(self, features: FrameFeatures, *, dt_ms: float) -> None:
        """Feed one FrameFeatures sample into calibration v2 session."""
        if self._session_v2 is None:
            return
        if self._result is not None or self._session_v2.is_finished:
            return
        # If we advanced targets, update the dot and reset the gate ONCE.
        idx = int(self._session_v2.target_index)
        if idx != self._v2_last_target_index:
            self._begin_current_point()
            # During prepare delay we don't collect.
            return

        if not self._v2_collect_enabled:
            return

        if os.environ.get("GAZEKEY_CALIB_DEBUG", "0").strip() == "1":
            idx = int(self._session_v2.target_index)
            label = (
                self._session_v2.targets[idx].label
                if idx < len(self._session_v2.targets)
                else f"T{idx+1:02d}"
            )
            gate = self._session_v2.gate.debug_metrics()
            self.status_label.setText(
                f"Point {idx + 1} ({label}) — {gate.get('state', '?')}\n"
                f"uL={features.pca_uL} vL={features.pca_vL} "
                f"uR={features.pca_uR} vR={features.pca_vR} "
                f"avg_v={features.avg_v}"
            )
        else:
            self._update_v2_status_hint()

        res = self._session_v2.process(features, dt_ms=float(dt_ms))
        if res is not None:
            self._show_result(res)
            return

        if os.environ.get("GAZEKEY_CALIB_DEBUG", "0").strip() != "1":
            self._update_v2_status_hint()

        # If we advanced targets, update the dot/label.
        if int(self._session_v2.target_index) != idx:
            self._begin_current_point()

    def _begin_current_point(self) -> None:
        if self._session_v2 is not None:
            idx = int(self._session_v2.target_index)
            if idx >= len(self._dot_targets) or self._session_v2.is_finished:
                return
            if idx == self._v2_last_target_index:
                return
            self._v2_last_target_index = idx
            self._v2_collect_enabled = False
            tx, ty = self._dot_targets[idx]
            point_count = len(self._dot_targets)
            name = self._session_v2.targets[idx].label if idx < len(self._session_v2.targets) else f"T{idx+1:02d}"
        else:
            idx = self._session.point_index
            if idx >= self._session.point_count:
                return
            tx, ty = self._dot_targets[idx]
            point_count = self._session.point_count
            name = self._session.current_point_name()

        self.dot_widget.set_target(tx, ty)
        self.dot_widget.show()
        self.dot_widget.raise_()

        self.status_label.setStyleSheet("color: #CCCCCC; background: transparent;")
        self.status_label.setText(
            f"Point {idx + 1} of {point_count} ({name})\n"
            "Look at the dot — move your eyes only; keep your head still."
        )

        if self._session_v2 is None:
            self._session.begin_prepare()
            self._prepare_timer.start(PREPARE_MS)
        else:
            # v2 session controls readiness via its own gating; we still keep a short "prepare" pause
            # so the user can saccade to the new dot, THEN we enable collecting.
            try:
                self._session_v2.begin_target()
            except Exception:
                pass
            self._prepare_timer.start(PREPARE_MS)

    def _update_v2_status_hint(self) -> None:
        if self._session_v2 is None:
            return
        idx = int(self._session_v2.target_index)
        if idx >= len(self._dot_targets):
            return
        point_count = len(self._dot_targets)
        name = self._session_v2.targets[idx].label if idx < len(self._session_v2.targets) else f"T{idx+1:02d}"
        gate = self._session_v2.gate.debug_metrics()
        state = str(gate.get("state", ""))
        reason = str(self._session_v2.last_reject_reason or "")
        if reason == "head_drift":
            detail = "Head moved — keep still and look at the dot"
        elif reason in {"unstable", "jump_ratio", "jump_pca", "jump"}:
            detail = "Hold steady on the dot"
        elif state == "WAIT_LOCK" or reason.startswith("locking"):
            detail = "Hold your gaze on the dot…"
        elif state == "LOCKED_COLLECTING":
            detail = "Collecting — keep head still, eyes on dot"
        else:
            detail = "Look at the dot — move your eyes only; keep your head still."
        self.status_label.setStyleSheet("color: #CCCCCC; background: transparent;")
        self.status_label.setText(f"Point {idx + 1} of {point_count} ({name})\n{detail}")

    def _start_collect(self) -> None:
        if self._session_v2 is None:
            self._session.begin_collect()
            # Collection completes when the session detects a stable fixation.
        else:
            self._v2_collect_enabled = True
            idx = int(self._session_v2.target_index)
            label = (
                self._session_v2.targets[idx].label
                if idx < len(self._session_v2.targets)
                else f"T{idx+1:02d}"
            )
            print(
                f"[calib2] target {label}: collection enabled after {PREPARE_MS}ms prepare "
                f"(fixation lock-on ~{self._session_v2.gate.cfg.lock_on_ms:.0f}ms before samples count)"
            )
            return

    def _show_result(self, result: Union[CalibrationResult, CalibrationV2Result]) -> None:
        self._result = result
        self.dot_widget.hide()
        self._prepare_timer.stop()

        if result.success:
            self.status_label.setStyleSheet("color: #10B981; background: transparent;")
            self.status_label.setText(result.message)
            self._success_close_timer.start(1500)
        else:
            self.status_label.setStyleSheet("color: #E63946; background: transparent;")
            self.status_label.setText(result.message)
            self.try_again_btn.show()
            self.cancel_btn.show()

    def _restart(self) -> None:
        self._result = None
        if self._session_v2 is None and self._session is not None:
            self._session.reset()
        self.try_again_btn.hide()
        self.cancel_btn.hide()
        self._begin_current_point()

    def _cancel(self) -> None:
        if self._session_v2 is not None:
            self._result = CalibrationV2Result(success=False, message="Calibration cancelled.", targets=list(self._session_v2.targets))
        else:
            self._result = CalibrationResult(success=False, message="Calibration cancelled.")
        self._emit_finished_and_close()

    def _emit_finished_and_close(self) -> None:
        if self._result is not None:
            self._on_finished(self._result)
        self.close()

    def restart_from_scratch(self) -> None:
        """Public entry to restart the full 5-point flow."""
        self._result = None
        self._success_close_timer.stop()
        if self._session_v2 is None and self._session is not None:
            self._session.reset()
        self.try_again_btn.hide()
        self.cancel_btn.hide()
        self._begin_current_point()
