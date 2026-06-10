"""Keyboard window chrome, key grid, and responsive geometry (T046)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPoint, Qt, QTimer, QRect
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gazekey.layout import inspect_keyboard_layout
from gazekey.typing.gaze_ui_mapper import typing_region_rect

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class KeyboardLayoutBuilder:
    """Builds VirtualKeyboard UI widgets and manages window geometry."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._h = host

    def init_ui(self) -> None:
        h = self._h
        h.setWindowTitle("GazeKey")
        h.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.apply_full_keyboard_geometry()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        h.main_content_widget = QWidget()
        h.main_content_widget.setObjectName("container")
        h.main_content_widget.setStyleSheet("""
            QWidget#container {
                background-color: #000000;
            }
        """)

        h._container_layout = QVBoxLayout(h.main_content_widget)
        h._container_layout.setContentsMargins(0, 0, 0, 0)
        h._container_layout.setSpacing(0)

        h._control_bar_layout = self.create_control_bar()
        h._control_bar_widget = QWidget()
        h._control_bar_widget.setLayout(h._control_bar_layout)

        h._text_display_layout = self.create_text_display()
        h._text_display_widget = QWidget()
        h._text_display_widget.setLayout(h._text_display_layout)

        h._suggestion_bar_layout = self.create_suggestion_bar()
        h._suggestion_bar_widget = QWidget()
        h._suggestion_bar_widget.setLayout(h._suggestion_bar_layout)

        h._container_layout.addWidget(h._control_bar_widget, 0)
        h._container_layout.addWidget(h._text_display_widget, 0)
        h._container_layout.addWidget(h._suggestion_bar_widget, 0)

        h.keyboard_widget = QWidget()
        h.keyboard_widget.setStyleSheet("background-color: #000000;")
        h._keyboard_layout = QVBoxLayout(h.keyboard_widget)
        h._keyboard_layout.setContentsMargins(0, 0, 0, 0)
        h._keyboard_layout.setSpacing(0)
        h._keyboard_layout.addLayout(self.create_letters_layout())
        h._container_layout.addWidget(h.keyboard_widget, 1)

        h.minimized_content_widget = self.create_minimized_view()
        h.minimized_content_widget.hide()

        main_layout.addWidget(h.main_content_widget)
        main_layout.addWidget(h.minimized_content_widget)

        h.setLayout(main_layout)
        h.setStyleSheet("background-color: #000000;")
        self.update_responsive_sizes()
        self.apply_mvp_future_ui_placeholders()

    def apply_mvp_future_ui_placeholders(self) -> None:
        """T037 / FR-018: disable future UI without shrinking layout."""
        h = self._h
        disabled_chrome_style = """
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.35);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
        """
        for attr in ("lang_btn", "symbols_btn"):
            if hasattr(h, attr):
                btn = getattr(h, attr)
                btn.setEnabled(False)
                btn.setToolTip("Reserved for a future release — not active in the calibration/mapping MVP")
                btn.setStyleSheet(btn.styleSheet() + disabled_chrome_style)

        suggestion_disabled_style = """
            QPushButton:disabled {
                background-color: #0a0a0a;
                color: rgba(204, 204, 204, 0.35);
                border: 1px solid #222222;
            }
        """
        for btn in getattr(h, "suggestion_buttons", []):
            btn.setEnabled(False)
            btn.setToolTip("Autocomplete suggestions — reserved for a future release")
            btn.setStyleSheet(btn.styleSheet() + suggestion_disabled_style)

    def create_control_bar(self) -> QHBoxLayout:
        h = self._h
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        h.calibrate_btn = QPushButton("👁 CALIBRATE")
        h.calibrate_btn.setObjectName("gazeTarget")
        h.calibrate_btn.setMinimumSize(220, 56)
        h.calibrate_btn.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        h.calibrate_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #FF8555;
            }
            QPushButton:pressed {
                background-color: #E55A25;
            }
            QPushButton#gazeTarget[gazeFocused="true"] {
                border: 2px solid #FBBF24;
            }
            QPushButton#gazeTarget[gazeDwelling="true"] {
                border: 2px solid #10B981;
            }
        """)
        h.calibrate_btn.clicked.connect(h.on_calibrate_clicked)
        h._calibrate_btn_style_default = h.calibrate_btn.styleSheet()

        h.camera_status_label = QLabel("📷 Camera: Off")
        h.camera_status_label.setFont(QFont("Segoe UI", 9))
        h.camera_status_label.setStyleSheet("""
            QLabel {
                color: #999999;
                padding: 5px;
            }
        """)

        layout.addWidget(h.calibrate_btn)
        layout.addWidget(h.camera_status_label)

        h.preview_btn = QPushButton("PREVIEW")
        h.preview_btn.setMinimumSize(90, 45)
        h.preview_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        h.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.12);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.18);
            }
            QPushButton[active="true"] {
                background-color: rgba(16, 185, 129, 0.25);
                border: 1px solid rgba(16, 185, 129, 0.6);
            }
        """)
        h.preview_btn.clicked.connect(h.on_preview_clicked)
        h.preview_btn.setEnabled(False)
        layout.addWidget(h.preview_btn)
        layout.addStretch()

        h.lang_btn = QPushButton("EN")
        h.lang_btn.setMinimumSize(60, 45)
        h.lang_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        h.lang_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        h.lang_btn.clicked.connect(h.on_language_clicked)

        h.minimize_btn = QPushButton("−")
        h.minimize_btn.setMinimumSize(50, 45)
        h.minimize_btn.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        h.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        h.minimize_btn.clicked.connect(h.on_minimize_clicked)

        h.close_btn = QPushButton("✕")
        h.close_btn.setMinimumSize(50, 45)
        h.close_btn.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        h.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.3);
                color: #FF6B6B;
            }
        """)
        h.close_btn.clicked.connect(h.on_close_clicked)

        h.symbols_btn = QPushButton("?123")
        h.symbols_btn.setMinimumSize(60, 45)
        h.symbols_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        h.symbols_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        h.symbols_btn.clicked.connect(h.on_symbols_clicked)

        layout.addWidget(h.lang_btn)
        layout.addWidget(h.symbols_btn)
        layout.addWidget(h.minimize_btn)
        layout.addWidget(h.close_btn)

        return layout

    def create_text_display(self) -> QHBoxLayout:
        h = self._h
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        h.text_display = QLineEdit()
        h.text_display.setPlaceholderText("Typed text appears here…")
        h.text_display.setReadOnly(True)
        h.text_display.setMinimumHeight(34)
        h.text_display.setFont(QFont("Segoe UI", 14))
        h.text_display.setStyleSheet("""
            QLineEdit {
                background-color: #111111;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 6px 10px;
            }
        """)
        layout.addWidget(h.text_display)
        return layout

    def create_suggestion_bar(self) -> QHBoxLayout:
        h = self._h
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        h.suggestion_buttons = []
        placeholder_suggestions = ["word1", "word2", "word3"]
        for suggestion in placeholder_suggestions:
            btn = QPushButton(suggestion)
            btn.setMinimumHeight(30)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #000000;
                    color: #CCCCCC;
                    border: 1px solid #333333;
                    border-radius: 0;
                    text-align: center;
                    padding: 0px 10px;
                }
                QPushButton:hover {
                    background-color: #1A1A1A;
                    border: 1px solid #555555;
                }
                QPushButton:pressed {
                    background-color: #2A2A2A;
                    color: white;
                }
            """)
            btn.clicked.connect(lambda checked, s=suggestion: h.on_suggestion_clicked(s))
            h.suggestion_buttons.append(btn)
            layout.addWidget(btn, 1)
        return layout

    def create_minimized_view(self) -> QWidget:
        h = self._h
        widget = QWidget()
        widget.setObjectName("minimized_container")
        widget.setStyleSheet("""
            QWidget#minimized_container {
                background-color: rgba(30, 30, 40, 230);
                border-radius: 12px;
                border: 2px solid rgba(255, 255, 255, 0.1);
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        h.restore_btn = QPushButton("⌨")
        h.restore_btn.setMinimumSize(80, 60)
        h.restore_btn.setFont(QFont("Segoe UI", 36))
        h.restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        h.restore_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid #FBBF24;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        h.restore_btn.clicked.connect(h.on_restore_clicked)
        layout.addWidget(h.restore_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        return widget

    @staticmethod
    def _keyboard_key_stylesheet() -> str:
        return """
            QPushButton#keyboardKey {
                background-color: #000000;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 0;
                padding: 2px 4px;
                margin: 0;
                font-weight: 500;
                text-align: center;
            }
            QPushButton#keyboardKey:hover {
                background-color: #1A1A1A;
                border: 1px solid #555555;
            }
            QPushButton#keyboardKey:pressed {
                background-color: #2A2A2A;
                border: 1px solid #777777;
            }
            QPushButton#keyboardKey:checked {
                background-color: #333333;
                border: 1px solid #888888;
            }
            QPushButton#keyboardKey[gazeFocused="true"] {
                background-color: #1A1A1A;
                border: 2px solid #FBBF24;
            }
            QPushButton#keyboardKey[gazeDwelling="true"] {
                background-color: #2A3A1A;
                border: 2px solid #10B981;
            }
        """

    def _keyboard_row_layout(self) -> QHBoxLayout:
        h = self._h
        row = QHBoxLayout()
        row.setSpacing(int(getattr(h, "_key_gap_px", 3)))
        row.setContentsMargins(0, 0, 0, 0)
        return row

    def _add_key_row(self, parent_layout: QVBoxLayout, widgets_with_stretch: list) -> None:
        row = self._keyboard_row_layout()
        for widget, stretch in widgets_with_stretch:
            row.addWidget(widget, stretch)
        parent_layout.addLayout(row, 1)

    def create_letters_layout(self) -> QVBoxLayout:
        h = self._h
        h.letter_keys.clear()
        layout = QVBoxLayout()
        layout.setSpacing(int(getattr(h, "_key_gap_px", 3)))
        layout.setContentsMargins(0, 0, 0, 0)

        row1_keys = []
        for char in "qwertyuiop":
            btn = self.create_key(char)
            h.letter_keys[char] = btn
            row1_keys.append((btn, 1))
        self._add_key_row(layout, row1_keys)

        row2 = self._keyboard_row_layout()
        row2.addStretch(1)
        for char in "asdfghjkl":
            btn = self.create_key(char)
            h.letter_keys[char] = btn
            row2.addWidget(btn, 1)
        row2.addStretch(1)
        layout.addLayout(row2, 1)

        row3_keys = []
        h.shift_btn = self.create_key("Shift")
        h.shift_btn.setCheckable(True)
        h.shift_btn.clicked.connect(h.on_shift_clicked)
        row3_keys.append((h.shift_btn, 2))
        for char in "zxcvbnm":
            btn = self.create_key(char)
            h.letter_keys[char] = btn
            row3_keys.append((btn, 1))
        backspace_btn = self.create_key("⌫")
        backspace_btn.clicked.connect(lambda: h.on_key_pressed("BACKSPACE"))
        row3_keys.append((backspace_btn, 2))
        self._add_key_row(layout, row3_keys)

        ctrl_btn = self.create_key("Ctrl")
        ctrl_btn.clicked.connect(lambda: h.on_key_pressed("CTRL"))
        alt_btn = self.create_key("Alt")
        alt_btn.clicked.connect(lambda: h.on_key_pressed("ALT"))
        space_btn = self.create_key("Space")
        space_btn.clicked.connect(lambda: h.on_key_pressed(" "))
        enter_btn = self.create_key("↵")
        enter_btn.clicked.connect(lambda: h.on_key_pressed("ENTER"))
        self._add_key_row(layout, [
            (ctrl_btn, 1),
            (alt_btn, 1),
            (space_btn, 5),
            (enter_btn, 2),
        ])
        return layout

    def create_symbols_layout(self) -> QVBoxLayout:
        h = self._h
        layout = QVBoxLayout()
        layout.setSpacing(int(getattr(h, "_key_gap_px", 3)))
        layout.setContentsMargins(0, 0, 0, 0)

        self._add_key_row(layout, [(self.create_key(n), 1) for n in "1234567890"])
        self._add_key_row(layout, [
            (self.create_key(sym), 1)
            for sym in ["!", "@", "#", "$", "%", "^", "&&", "*", "(", ")"]
        ])

        row3_keys = [(self.create_key(sym), 1) for sym in ["-", "/", ":", ";", "'", '"', ",", "."]]
        backspace_btn = self.create_key("⌫")
        backspace_btn.clicked.connect(lambda: h.on_key_pressed("BACKSPACE"))
        row3_keys.append((backspace_btn, 2))
        self._add_key_row(layout, row3_keys)

        ctrl_btn = self.create_key("Ctrl")
        ctrl_btn.clicked.connect(lambda: h.on_key_pressed("CTRL"))
        alt_btn = self.create_key("Alt")
        alt_btn.clicked.connect(lambda: h.on_key_pressed("ALT"))
        space_btn = self.create_key("Space")
        space_btn.clicked.connect(lambda: h.on_key_pressed(" "))
        enter_btn = self.create_key("↵")
        enter_btn.clicked.connect(lambda: h.on_key_pressed("ENTER"))
        self._add_key_row(layout, [
            (ctrl_btn, 1),
            (alt_btn, 1),
            (space_btn, 5),
            (enter_btn, 2),
        ])
        return layout

    def create_key(self, text: str) -> QPushButton:
        h = self._h
        btn = QPushButton(text)
        btn.setObjectName("keyboardKey")
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        btn.setMinimumHeight(24)
        btn.setFont(QFont("Segoe UI", 16, QFont.Weight.Medium))
        btn.setStyleSheet(self._keyboard_key_stylesheet())

        special_chars = [
            ",", ".", "!", "@", "#", "$", "%", "^", "*", "(", ")",
            "-", "/", ":", ";", "?", "'", '"', "_", "+", "=",
        ]
        if len(text) == 1 and (text.isalnum() or text in special_chars):
            btn.clicked.connect(lambda checked=False, t=text: h.on_key_pressed(t))
        elif text == "&&":
            btn.clicked.connect(lambda: h.on_key_pressed("&"))
        return btn

    def switch_layout(self, layout_type: str) -> None:
        h = self._h
        keyboard_layout = h.keyboard_widget.layout()
        while keyboard_layout.count():
            item = keyboard_layout.takeAt(0)
            if item.layout():
                self.clear_layout(item.layout())
            elif item.widget():
                item.widget().deleteLater()

        if layout_type == "letters":
            new_layout = self.create_letters_layout()
            h.symbols_btn.setText("?123")
            h._log_verbose("Switched to letters layout")
        else:
            new_layout = self.create_symbols_layout()
            h.symbols_btn.setText("ABC")
            h._log_verbose("Switched to symbols layout")

        keyboard_layout.addLayout(new_layout)
        h.current_layout = layout_type
        h._schedule_layout_export()

    @staticmethod
    def clear_layout(layout: Any) -> None:
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                elif item.layout():
                    KeyboardLayoutBuilder.clear_layout(item.layout())

    def primary_screen_geometry(self):
        return QApplication.primaryScreen().geometry()

    def primary_screen_available_geometry(self):
        return QApplication.primaryScreen().availableGeometry()

    def full_keyboard_size(self) -> tuple[int, int]:
        screen = self.primary_screen_available_geometry()
        width = screen.width()
        height_ratio = 0.62
        height = int(screen.height() * height_ratio)
        return width, height

    def position_at_bottom(self) -> None:
        h = self._h
        screen = self.primary_screen_available_geometry()
        x = screen.x()
        y = screen.y() + screen.height() - h.height()
        h.move(x, y)

    def position_at_top(self) -> None:
        h = self._h
        screen = self.primary_screen_available_geometry()
        h.move(screen.x(), screen.y())

    def apply_full_keyboard_geometry(self) -> None:
        h = self._h
        width, height = self.full_keyboard_size()
        screen = self.primary_screen_available_geometry()
        h.setFixedHeight(min(height, screen.height()))
        h.setFixedWidth(width)
        self.position_at_top()

    def apply_minimized_geometry(self) -> None:
        h = self._h
        h.setFixedSize(120, 100)
        screen = self.primary_screen_geometry()
        margin = 20
        x = screen.x() + screen.width() - h.width() - margin
        y = screen.y() + screen.height() - h.height() - margin
        h.move(x, y)

    def update_responsive_sizes(self) -> None:
        h = self._h
        if not hasattr(h, "keyboard_widget"):
            return

        window_h = float(h.height() or 0)
        if window_h <= 0:
            return
        window_w = float(h.width() or 0)
        if window_w <= 0:
            return

        margin = int(max(4.0, min(14.0, window_h * 0.02)))
        gap = int(max(2.0, min(8.0, window_h * 0.01)))
        h._key_gap_px = gap

        if hasattr(h, "_container_layout"):
            h._container_layout.setContentsMargins(margin, margin, margin, margin)
            h._container_layout.setSpacing(gap)
        if hasattr(h, "_keyboard_layout"):
            h._keyboard_layout.setContentsMargins(0, 0, 0, 0)
            h._keyboard_layout.setSpacing(gap)
        if hasattr(h, "_control_bar_layout"):
            h._control_bar_layout.setSpacing(gap)
        if hasattr(h, "_text_display_layout"):
            h._text_display_layout.setSpacing(gap)
        if hasattr(h, "_suggestion_bar_layout"):
            h._suggestion_bar_layout.setSpacing(gap)

        chrome_h = int(max(34.0, min(58.0, window_h * 0.12)))
        text_h = int(max(24.0, min(38.0, window_h * 0.08)))
        sugg_h = int(max(26.0, min(40.0, window_h * 0.08)))

        chrome_pt = int(max(11.0, min(18.0, chrome_h * 0.30)))
        if hasattr(h, "calibrate_btn"):
            f = h.calibrate_btn.font()
            if f.pointSize() != chrome_pt + 4:
                f.setPointSize(chrome_pt + 4)
                h.calibrate_btn.setFont(f)
        if hasattr(h, "camera_status_label"):
            f = h.camera_status_label.font()
            if f.pointSize() != max(8, chrome_pt - 2):
                f.setPointSize(max(8, chrome_pt - 2))
                h.camera_status_label.setFont(f)

        if hasattr(h, "calibrate_btn"):
            h.calibrate_btn.setMinimumHeight(chrome_h)
            h.calibrate_btn.setMaximumHeight(chrome_h)
        for attr in ("lang_btn", "symbols_btn", "minimize_btn", "close_btn"):
            if hasattr(h, attr):
                btn = getattr(h, attr)
                btn.setMinimumHeight(max(34, chrome_h - 10))
                btn.setMaximumHeight(max(34, chrome_h - 10))
                f = btn.font()
                if f.pointSize() != max(9, chrome_pt):
                    f.setPointSize(max(9, chrome_pt))
                    btn.setFont(f)

        if hasattr(h, "text_display"):
            h.text_display.setMinimumHeight(text_h)
            h.text_display.setMaximumHeight(text_h)
            f = h.text_display.font()
            if f.pointSize() != int(max(11.0, min(18.0, text_h * 0.45))):
                f.setPointSize(int(max(11.0, min(18.0, text_h * 0.45))))
                h.text_display.setFont(f)

        if hasattr(h, "suggestion_buttons"):
            for btn in h.suggestion_buttons:
                btn.setMinimumHeight(sugg_h)
                btn.setMaximumHeight(sugg_h)
                f = btn.font()
                target = int(max(10.0, min(18.0, sugg_h * 0.45)))
                if f.pointSize() != target:
                    f.setPointSize(target)
                    btn.setFont(f)

        margins_total = float(margin * 2)
        gaps_total = float(gap * 3)
        desired_kb_h = window_h - (margins_total + gaps_total + chrome_h + text_h + sugg_h)

        if desired_kb_h < 4 * 24:
            extra = (4 * 24) - desired_kb_h
            shrink = min(extra, chrome_h * 0.25)
            chrome_h = int(max(28.0, chrome_h - shrink))
            desired_kb_h = window_h - (margins_total + gaps_total + chrome_h + text_h + sugg_h)

        h.keyboard_widget.setMinimumHeight(int(max(0.0, desired_kb_h)))
        h.keyboard_widget.setMaximumHeight(int(max(0.0, desired_kb_h)))

        for widget_attr, widget_h in (
            ("_control_bar_widget", chrome_h),
            ("_text_display_widget", text_h),
            ("_suggestion_bar_widget", sugg_h),
        ):
            if hasattr(h, widget_attr):
                w = getattr(h, widget_attr)
                w.setMinimumHeight(int(widget_h))
                w.setMaximumHeight(int(widget_h))

        kb_h = float(desired_kb_h)
        if kb_h <= 0:
            return

        row_spacing = float(gap)
        rows = 4.0
        usable = max(0.0, kb_h - row_spacing * (rows - 1.0))
        row_h = usable / rows if rows > 0 else usable

        key_h = int(max(24.0, min(72.0, row_h)))
        font_pt = int(max(11.0, min(22.0, key_h * 0.42)))

        for btn in h.keyboard_widget.findChildren(QPushButton, "keyboardKey"):
            btn.setMinimumHeight(key_h)
            btn.setMaximumHeight(key_h)
            f = btn.font()
            if f.pointSize() != font_pt:
                f.setPointSize(font_pt)
                btn.setFont(f)

        if hasattr(h, "suggestion_buttons"):
            sug_h2 = int(max(26.0, min(48.0, key_h * 0.75)))
            sug_pt = int(max(10.0, min(18.0, sug_h2 * 0.45)))
            for btn in h.suggestion_buttons:
                btn.setMinimumHeight(sug_h2)
                btn.setMaximumHeight(sug_h2)
                f = btn.font()
                if f.pointSize() != sug_pt:
                    f.setPointSize(sug_pt)
                    btn.setFont(f)

    def schedule_layout_export(self) -> None:
        h = self._h
        if h._layout_export_pending:
            return
        h._layout_export_pending = True
        QTimer.singleShot(0, self.export_keyboard_layout)

    def export_keyboard_layout(self) -> None:
        h = self._h
        h._layout_export_pending = False
        tl = h.mapToGlobal(QPoint(0, 0))
        window_rect = QRect(tl, h.size())

        try:
            region_rect = typing_region_rect(h.keyboard_widget, h.calibrate_btn)
            keys = inspect_keyboard_layout(h.main_content_widget)
            h._layout_version = h._layout_exporter.export(
                window_rect=window_rect,
                typing_region_rect=region_rect,
                keys=keys,
            )
            h._layout_keys = keys
            h._keys_by_id = {k.key_id: k for k in keys}
            h._key_semantic_row = self.derive_key_semantic_rows(keys)
        except Exception as e:
            h._log_verbose(f"Failed to export keyboard_layout.csv: {e}")

    def derive_key_semantic_rows(self, keys) -> dict:
        """Assign each key_id to one of the semantic row regions."""
        row_names = self._h._row_aware_row_names
        phys = {}
        for k in keys:
            ys = phys.setdefault(k.row_index, [])
            ys.append(float(k.center[1]))
        phys_rows = [(float(sum(v) / len(v)), ridx) for ridx, v in phys.items() if v]
        phys_rows.sort(key=lambda t: t[0])
        ordered = [ridx for _, ridx in phys_rows]

        def sem_for_rank(rank: int) -> str:
            if len(ordered) <= len(row_names):
                return row_names[min(rank, len(row_names) - 1)]
            q = int(round((rank / max(1, len(ordered) - 1)) * (len(row_names) - 1)))
            return row_names[max(0, min(len(row_names) - 1, q))]

        sem_for_phys = {}
        for rank, ridx in enumerate(ordered):
            sem_for_phys[ridx] = sem_for_rank(rank)

        return {k.key_id: sem_for_phys.get(k.row_index, "letters2") for k in keys}
