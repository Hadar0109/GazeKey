"""Fullscreen calibration v2 fixation overlay (FrameFeatures + gating)."""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

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

from gazekey.calibration.session import CalibrationResult, CalibrationSession
from gazekey.features.feature_types import FrameFeatures
from gazekey.mvp_log import mvp_log

# Short pause after dot moves before samples count (matches legacy v1 prepare delay).
PREPARE_MS = 2000


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
    Fullscreen calibration v2 UI on the primary screen.

    Signals completion via on_finished callback.
    """

    def __init__(
        self,
        dot_targets: List[Tuple[float, float]],
        screen_targets: List[Tuple[float, float]],
        on_finished: Callable[[CalibrationResult], None],
        session: CalibrationSession,
        minimal_fixation_ui: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self._dot_targets = dot_targets
        self._screen_targets = screen_targets
        self._on_finished = on_finished
        self._session = session
        self._minimal_fixation_ui = bool(minimal_fixation_ui)
        self._result: Optional[CalibrationResult] = None
        self._last_target_index: int = -1
        self._collect_enabled: bool = False

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
        return self._session

    @property
    def session_v2(self) -> CalibrationSession:
        """Alias retained for tests and transitional callers."""
        return self._session

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

        self._title_label = QLabel("Eye Calibration")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self._title_label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(self._title_label)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 16))
        self.status_label.setStyleSheet("color: #CCCCCC; background: transparent;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        if self._minimal_fixation_ui:
            self._title_label.hide()
            self.status_label.setFont(QFont("Segoe UI", 14))

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
            idx = int(self._session.target_index)
            if idx < len(self._dot_targets) and not self._session.is_finished:
                self.dot_widget.set_target(*self._dot_targets[idx])

    def add_features_dt(self, features: FrameFeatures, *, dt_ms: float) -> None:
        """Feed one FrameFeatures sample into the calibration v2 session."""
        if self._result is not None or self._session.is_finished:
            return

        idx = int(self._session.target_index)
        if idx != self._last_target_index:
            self._begin_current_point()
            return

        if not self._collect_enabled:
            return

        if self._verbose_fixation_ui():
            label = (
                self._session.targets[idx].label
                if idx < len(self._session.targets)
                else f"T{idx+1:02d}"
            )
            gate = self._session.gate.debug_metrics()
            self.status_label.setText(
                f"Point {idx + 1} ({label}) — {gate.get('state', '?')}\n"
                f"uL={features.pca_uL} vL={features.pca_vL} "
                f"uR={features.pca_uR} vR={features.pca_vR} "
                f"avg_v={features.avg_v}"
            )
        elif self._minimal_fixation_ui:
            self._update_progress_only()
        else:
            self._update_status_hint()

        res = self._session.process(features, dt_ms=float(dt_ms))
        if res is not None:
            self._show_result(res)
            return

        if not self._verbose_fixation_ui():
            if self._minimal_fixation_ui:
                self._update_progress_only()
            else:
                self._update_status_hint()

        if int(self._session.target_index) != idx:
            self._begin_current_point()

    def _begin_current_point(self) -> None:
        idx = int(self._session.target_index)
        if idx >= len(self._dot_targets) or self._session.is_finished:
            return
        if idx == self._last_target_index:
            return
        self._last_target_index = idx
        self._collect_enabled = False
        tx, ty = self._dot_targets[idx]
        name = self._session.targets[idx].label if idx < len(self._session.targets) else f"T{idx+1:02d}"

        self.dot_widget.set_target(tx, ty)
        self.dot_widget.show()
        self.dot_widget.raise_()

        if self._minimal_fixation_ui:
            self._update_progress_only()
        else:
            self._update_status_hint()

        try:
            self._session.begin_target()
        except Exception:
            pass
        self._prepare_timer.start(PREPARE_MS)

    @staticmethod
    def _verbose_fixation_ui() -> bool:
        from gazekey.ui.env_flags import verbose_fixation_ui

        return verbose_fixation_ui()

    def _update_progress_only(self) -> None:
        """MVP fixation UI: optional progress only (FR-003, SC-006)."""
        idx = int(self._session.target_index)
        if idx >= len(self._dot_targets):
            return
        point_count = len(self._dot_targets)
        self.status_label.setStyleSheet("color: #AAAAAA; background: transparent;")
        self.status_label.setText(f"{idx + 1} / {point_count}")
        self.status_label.show()

    def _update_status_hint(self) -> None:
        idx = int(self._session.target_index)
        if idx >= len(self._dot_targets):
            return
        point_count = len(self._dot_targets)
        name = self._session.targets[idx].label if idx < len(self._session.targets) else f"T{idx+1:02d}"
        gate = self._session.gate.debug_metrics()
        state = str(gate.get("state", ""))
        reason = str(self._session.last_reject_reason or "")
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
        self._collect_enabled = True
        idx = int(self._session.target_index)
        label = (
            self._session.targets[idx].label
            if idx < len(self._session.targets)
            else f"T{idx+1:02d}"
        )
        mvp_log(
            f"[calib2] target {label}: collection enabled after {PREPARE_MS}ms prepare "
            f"(fixation lock-on ~{self._session.gate.cfg.lock_on_ms:.0f}ms before samples count)"
        )

    def _show_result(self, result: CalibrationResult) -> None:
        self._result = result
        self.dot_widget.hide()
        self._prepare_timer.stop()

        if result.success and self._minimal_fixation_ui:
            self.status_label.hide()
            self._emit_finished_and_close()
            return

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
        self.try_again_btn.hide()
        self.cancel_btn.hide()
        self._begin_current_point()

    def _cancel(self) -> None:
        self._result = CalibrationResult(
            success=False,
            message="Calibration cancelled.",
            targets=list(self._session.targets),
        )
        self._emit_finished_and_close()

    def _emit_finished_and_close(self) -> None:
        """Hide overlay before the finish callback (mapper fit can take seconds)."""
        result = self._result
        self.hide()
        if result is not None:
            self._on_finished(result)
        self.close()

    def restart_from_scratch(self) -> None:
        """Public entry to restart the full calibration flow."""
        self._result = None
        self._success_close_timer.stop()
        self._last_target_index = -1
        self._collect_enabled = False
        self.try_again_btn.hide()
        self.cancel_btn.hide()
        self._begin_current_point()
