"""Fullscreen 5-point calibration overlay."""

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

from gazekey.calibration.calibration_session import (
    CalibrationSession,
    CalibrationResult,
    PREPARE_MS,
    COLLECT_MS,
    POINT_NAMES,
)


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
        on_finished: Callable[[CalibrationResult], None],
        frame_w: float = 640.0,
        frame_h: float = 480.0,
        parent=None,
    ):
        super().__init__(parent)
        self._dot_targets = dot_targets
        self._screen_targets = screen_targets
        self._on_finished = on_finished
        self._session = CalibrationSession(
            screen_targets, frame_w=frame_w, frame_h=frame_h
        )
        self._result: Optional[CalibrationResult] = None

        self._prepare_timer = QTimer(self)
        self._prepare_timer.setSingleShot(True)
        self._prepare_timer.timeout.connect(self._start_collect)

        self._collect_timer = QTimer(self)
        self._collect_timer.setSingleShot(True)
        self._collect_timer.timeout.connect(self._end_collect)

        self._success_close_timer = QTimer(self)
        self._success_close_timer.setSingleShot(True)
        self._success_close_timer.timeout.connect(self._emit_finished_and_close)

        self._setup_window()
        self._setup_ui()
        self._begin_current_point()

    @property
    def session(self) -> CalibrationSession:
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
            idx = self._session.point_index
            if idx < len(self._dot_targets) and not self._session.is_finished:
                self.dot_widget.set_target(*self._dot_targets[idx])

    def add_sample(self, iris_x: float, iris_y: float) -> None:
        self._session.add_sample(iris_x, iris_y)

    def _begin_current_point(self) -> None:
        idx = self._session.point_index
        if idx >= 5:
            return

        tx, ty = self._dot_targets[idx]
        self.dot_widget.set_target(tx, ty)
        self.dot_widget.show()
        self.dot_widget.raise_()

        name = POINT_NAMES[idx]
        self.status_label.setStyleSheet("color: #CCCCCC; background: transparent;")
        self.status_label.setText(
            f"Point {idx + 1} of 5 ({name})\nLook at the dot — keep your head still."
        )

        self._session.begin_prepare()
        self._prepare_timer.start(PREPARE_MS)

    def _start_collect(self) -> None:
        self._session.begin_collect()
        self._collect_timer.start(COLLECT_MS)

    def _end_collect(self) -> None:
        result = self._session.finish_collect()
        if result is not None:
            self._show_result(result)
            return

        self._begin_current_point()

    def _show_result(self, result: CalibrationResult) -> None:
        self._result = result
        self.dot_widget.hide()
        self._prepare_timer.stop()
        self._collect_timer.stop()

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
        self._session.reset()
        self.try_again_btn.hide()
        self.cancel_btn.hide()
        self._begin_current_point()

    def _cancel(self) -> None:
        self._result = CalibrationResult(
            success=False,
            message="Calibration cancelled.",
        )
        self._emit_finished_and_close()

    def _emit_finished_and_close(self) -> None:
        if self._result is not None:
            self._on_finished(self._result)
        self.close()

    def restart_from_scratch(self) -> None:
        """Public entry to restart the full 5-point flow."""
        self._result = None
        self._success_close_timer.stop()
        self._session.reset()
        self.try_again_btn.hide()
        self.cancel_btn.hide()
        self._begin_current_point()
