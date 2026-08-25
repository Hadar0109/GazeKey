"""Keyboard window chrome, key grid, and responsive geometry (003 simplified)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QPoint, Qt, QTimer, QRect
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gazekey.layout import inspect_keyboard_layout
from gazekey.typing.gaze_ui_mapper import typing_region_rect
from gazekey.typing.key_semantics import PAGE_LEFT_KEY_ID, PAGE_RIGHT_KEY_ID

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard

# Stable layout key_ids for suggestion slots (contracts/keyboard-layout-003.md).
SUGGESTION_SLOT_COUNT = 3
SUGGESTION_KEY_ID_PREFIX = "suggestion:"

# Letter-area pane stretch (research R2). Named weights only — do not encode
# pixel sizes. Applied to the first two letter rows beside the arrow.
LETTER_PANE_STRETCH = 5
ARROW_PANE_STRETCH = 1
# Top-of-screen overlay height as a fraction of available screen (research R9).
KEYBOARD_HEIGHT_RATIO = 0.70


class KeyboardLayoutBuilder:
    """Builds VirtualKeyboard UI widgets and manages window geometry."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._h = host

    def init_ui(self) -> None:
        h = self._h
        h.setWindowTitle("GazeKey")
        # OS/window focus hardening (T052): stay on top as a tool overlay that
        # does not accept/activate focus — preserves external typing target.
        # Geometry (fullscreen calib elsewhere; top-half keyboard here) unchanged.
        h.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        h.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        h.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.apply_full_keyboard_geometry()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        h.main_content_widget = QWidget()
        h.main_content_widget.setObjectName("container")
        h.main_content_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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

        h._suggestion_bar_layout = self.create_suggestion_bar()
        h._suggestion_bar_widget = QWidget()
        h._suggestion_bar_widget.setLayout(h._suggestion_bar_layout)

        h._container_layout.addWidget(h._control_bar_widget, 0)
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
        self.apply_no_focus_policies()

    def apply_no_focus_policies(self) -> None:
        """T053: mouse clicks must not permanently capture the external typing target."""
        h = self._h
        h.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for attr in (
            "main_content_widget",
            "keyboard_widget",
            "minimized_content_widget",
            "_control_bar_widget",
            "_suggestion_bar_widget",
            "calibrate_btn",
            "minimize_btn",
            "close_btn",
            "restore_btn",
            "shift_btn",
            "page_switch_btn",
        ):
            widget = getattr(h, attr, None)
            if widget is not None:
                widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for btn in getattr(h, "suggestion_buttons", []) or []:
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for btn in getattr(h, "letter_keys", {}).values():
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for btn in h.findChildren(QPushButton):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def apply_mvp_future_ui_placeholders(self) -> None:
        """Keep suggestion slots fixed but blank/disabled until prediction wires labels."""
        h = self._h
        suggestion_disabled_style = """
            QPushButton:disabled {
                background-color: #0a0a0a;
                color: rgba(204, 204, 204, 0.35);
                border: 1px solid #222222;
            }
        """
        for btn in getattr(h, "suggestion_buttons", []):
            btn.setEnabled(False)
            btn.setText("")
            btn.setToolTip("Autocomplete suggestions")
            btn.setStyleSheet(btn.styleSheet() + suggestion_disabled_style)

    def create_control_bar(self) -> QHBoxLayout:
        """Slim window chrome only (FR-008d: Calibrate moved to bottom row)."""
        h = self._h
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()

        h.minimize_btn = QPushButton("−")
        h.minimize_btn.setMinimumSize(50, 36)
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
        h.close_btn.setMinimumSize(50, 36)
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

        layout.addWidget(h.minimize_btn)
        layout.addWidget(h.close_btn)

        return layout

    def _create_calibrate_button(self) -> QPushButton:
        """Large orange Calibrate/Recalibrate gaze recovery target (FR-008d)."""
        h = self._h
        btn = QPushButton("👁 CALIBRATE")
        btn.setObjectName("gazeTarget")
        btn.setProperty("gazeKeyId", "system:calibrate")
        btn.setProperty("gazeKeyAction", "system:calibrate")
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        btn.setMinimumSize(160, 40)
        btn.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        btn.setStyleSheet("""
            QPushButton#gazeTarget {
                background-color: #FF6B35;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px;
            }
            QPushButton#gazeTarget:hover {
                background-color: #FF8555;
            }
            QPushButton#gazeTarget:pressed {
                background-color: #E55A25;
            }
            QPushButton#gazeTarget[gazeFocused="true"] {
                border: 2px solid #FBBF24;
            }
            QPushButton#gazeTarget[gazeDwelling="true"] {
                border: 2px solid #10B981;
            }
        """)
        btn.clicked.connect(h.on_calibrate_clicked)
        h.calibrate_btn = btn
        h._calibrate_btn_style_default = btn.styleSheet()
        return btn

    def create_suggestion_bar(self) -> QHBoxLayout:
        h = self._h
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        h.suggestion_buttons = []
        base_style = """
            QPushButton#gazeTarget {
                background-color: #000000;
                color: #CCCCCC;
                border: 1px solid #333333;
                border-radius: 0;
                text-align: center;
                padding: 0px 10px;
            }
            QPushButton#gazeTarget:hover {
                background-color: #1A1A1A;
                border: 1px solid #555555;
            }
            QPushButton#gazeTarget:pressed {
                background-color: #2A2A2A;
                color: white;
            }
            QPushButton#gazeTarget[gazeFocused="true"] {
                border: 2px solid #FBBF24;
            }
            QPushButton#gazeTarget[gazeDwelling="true"] {
                border: 2px solid #10B981;
            }
            QPushButton#gazeTarget:disabled {
                background-color: #0a0a0a;
                color: rgba(204, 204, 204, 0.35);
                border: 1px solid #222222;
            }
        """
        for slot in range(SUGGESTION_SLOT_COUNT):
            key_id = f"{SUGGESTION_KEY_ID_PREFIX}{slot}"
            btn = QPushButton("")
            btn.setObjectName("gazeTarget")
            btn.setProperty("gazeKeyId", key_id)
            btn.setProperty("gazeKeyAction", key_id)
            btn.setMinimumHeight(40)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
            btn.setStyleSheet(base_style)
            btn.setEnabled(False)
            btn.clicked.connect(lambda checked=False, s=slot: h.on_suggestion_clicked(s))
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

    def _make_letter_key(self, char: str) -> QPushButton:
        btn = self.create_key(char)
        self._h.letter_keys[char] = btn
        return btn

    def _page_switch_arrow_stylesheet(self) -> str:
        return """
            QPushButton#gazeTarget {
                background-color: #163A4A;
                color: #E8F4F8;
                border: 2px solid #3D8CA3;
                border-radius: 6px;
                padding: 4px;
                font-weight: bold;
            }
            QPushButton#gazeTarget:hover {
                background-color: #1E4E62;
                border: 2px solid #5EB1C7;
            }
            QPushButton#gazeTarget:pressed {
                background-color: #0F2C38;
            }
            QPushButton#gazeTarget[gazeFocused="true"] {
                border: 2px solid #FBBF24;
            }
            QPushButton#gazeTarget[gazeDwelling="true"] {
                border: 2px solid #10B981;
            }
        """

    def _create_page_switch_arrow(self, page: str) -> QPushButton:
        """One tall gazeTarget spanning the first two letter rows (not a keyboardKey)."""
        if page == "right":
            key_id = PAGE_LEFT_KEY_ID
            label = "←"
        else:
            key_id = PAGE_RIGHT_KEY_ID
            label = "→"
        btn = QPushButton(label)
        btn.setObjectName("gazeTarget")
        btn.setProperty("gazeKeyId", key_id)
        btn.setProperty("gazeKeyAction", key_id)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        btn.setMinimumWidth(24)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        btn.setStyleSheet(self._page_switch_arrow_stylesheet())
        btn.setToolTip("Switch letter page")
        btn.clicked.connect(self._h.on_page_switch_activated)
        return btn

    def _create_upper_letters_column(self, page: str) -> QWidget:
        """First two letter rows only (arrow sits beside this pane)."""
        h = self._h
        column = QWidget()
        column.setObjectName("lettersColumn")
        column.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        col_layout = QVBoxLayout(column)
        col_layout.setSpacing(int(getattr(h, "_key_gap_px", 3)))
        col_layout.setContentsMargins(0, 0, 0, 0)

        if page == "right":
            row1, row2 = "yuiop", "hjkl"
        else:
            row1, row2 = "qwert", "asdfg"
        self._add_key_row(col_layout, [(self._make_letter_key(ch), 1) for ch in row1])
        self._add_key_row(col_layout, [(self._make_letter_key(ch), 1) for ch in row2])
        return column

    def _create_third_letter_row(self, page: str) -> QWidget:
        """Shift + page letters + Backspace at full letter-area width (no arrow)."""
        h = self._h
        row3 = "bnm" if page == "right" else "zxcv"
        widget = QWidget()
        widget.setObjectName("letterRow3")
        widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        row = self._keyboard_row_layout()
        widget.setLayout(row)
        h.shift_btn = self.create_key("Shift")
        h.shift_btn.setCheckable(True)
        h.shift_btn.clicked.connect(h.on_shift_clicked)
        row.addWidget(h.shift_btn, 2)
        for ch in row3:
            row.addWidget(self._make_letter_key(ch), 1)
        backspace_btn = self.create_key("⌫")
        backspace_btn.clicked.connect(lambda: h.on_key_pressed("BACKSPACE"))
        h.backspace_btn = backspace_btn
        row.addWidget(backspace_btn, 2)
        return widget

    def _populate_letter_area(self, page: str) -> None:
        h = self._h
        h.letter_keys.clear()
        gap = int(getattr(h, "_key_gap_px", 3))
        upper = self._create_upper_letters_column(page)
        arrow = self._create_page_switch_arrow(page)
        top = QWidget()
        top.setObjectName("letterTopPane")
        top.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(gap)
        if page == "right":
            top_layout.addWidget(arrow, ARROW_PANE_STRETCH)
            top_layout.addWidget(upper, LETTER_PANE_STRETCH)
        else:
            top_layout.addWidget(upper, LETTER_PANE_STRETCH)
            top_layout.addWidget(arrow, ARROW_PANE_STRETCH)
        row3 = self._create_third_letter_row(page)
        h._letters_column_widget = upper
        h._letter_top_pane_widget = top
        h._letter_row3_widget = row3
        h.page_switch_btn = arrow
        layout = h._letter_area_layout
        layout.addWidget(top, 2)
        layout.addWidget(row3, 1)
        # Created without a parent (hidden) then reparented; show now that the
        # letter area is already on-screen (rebuild path). Initial show() of
        # the keyboard window still reveals the first page.
        top.show()
        row3.show()
        upper.show()
        arrow.show()

    def _unparent_letter_area_contents(self) -> None:
        """Synchronously remove letter-area widgets from the inspected tree."""
        h = self._h
        layout = getattr(h, "_letter_area_layout", None)
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def rebuild_letter_area(self, page: str) -> None:
        """Destroy/recreate the visible letter page; export before return (R3)."""
        h = self._h
        self._unparent_letter_area_contents()
        h.letter_keys.clear()
        h.page_switch_btn = None
        h._letters_column_widget = None
        h._letter_top_pane_widget = None
        h._letter_row3_widget = None
        h._layout_keys = []
        h._keys_by_id = {}

        self._populate_letter_area(page)
        restore = getattr(h, "_restore_shift_visual_from_session", None)
        if callable(restore):
            restore()
        self.apply_no_focus_policies()
        self.update_responsive_sizes()
        area_layout = getattr(h, "_letter_area_layout", None)
        if area_layout is not None:
            area_layout.activate()
        kb_layout = getattr(h, "_keyboard_layout", None)
        if kb_layout is not None:
            kb_layout.activate()
        area = getattr(h, "_letter_area_widget", None)
        if area is not None:
            area.updateGeometry()
        self.export_keyboard_layout()

    def create_letters_layout(self) -> QVBoxLayout:
        """Paged letter area (research R1) + full-width Calibrate | Space | Enter."""
        h = self._h
        gap = int(getattr(h, "_key_gap_px", 3))
        layout = QVBoxLayout()
        layout.setSpacing(gap)
        layout.setContentsMargins(0, 0, 0, 0)

        h._letter_area_widget = QWidget()
        h._letter_area_widget.setObjectName("letterArea")
        h._letter_area_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        h._letter_area_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        h._letter_area_layout = QVBoxLayout(h._letter_area_widget)
        h._letter_area_layout.setContentsMargins(0, 0, 0, 0)
        h._letter_area_layout.setSpacing(gap)

        page = getattr(h, "letter_page", "left")
        self._populate_letter_area(page)
        layout.addWidget(h._letter_area_widget, 3)

        # Bottom row: large Calibrate | reduced Space | slightly smaller Enter.
        calibrate_btn = self._create_calibrate_button()
        h.space_btn = self.create_key("Space")
        h.space_btn.clicked.connect(lambda: h.on_key_pressed(" "))
        h.enter_btn = self.create_key("↵")
        h.enter_btn.clicked.connect(lambda: h.on_key_pressed("ENTER"))
        # Stretch weights: Calibrate largest, Space medium/centered, Enter smaller.
        self._add_key_row(layout, [
            (calibrate_btn, 4),
            (h.space_btn, 3),
            (h.enter_btn, 2),
        ])
        return layout

    def switch_layout(self, layout_type: str) -> None:
        """Letters-only product surface (003). Symbols path removed; keep API for tools."""
        h = self._h
        if layout_type != "letters":
            h._log_verbose(f"switch_layout({layout_type!r}) ignored — letters-only product keyboard")
            return
        page = getattr(h, "letter_page", "left")
        self.rebuild_letter_area(page)
        h.current_layout = "letters"

    def create_key(self, text: str) -> QPushButton:
        h = self._h
        btn = QPushButton(text)
        btn.setObjectName("keyboardKey")
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        btn.setMinimumHeight(24)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        """Top-of-screen product keyboard height = 70% of available screen (R9)."""
        screen = self.primary_screen_available_geometry()
        width = screen.width()
        height = int(screen.height() * KEYBOARD_HEIGHT_RATIO)
        return width, height

    def position_at_bottom(self) -> None:
        h = self._h
        screen = self.primary_screen_available_geometry()
        x = screen.x()
        y = screen.y() + screen.height() - h.height()
        h.move(x, y)

    def position_at_top(self) -> None:
        """Pin keyboard to top of available geometry (T051 — preserved)."""
        h = self._h
        screen = self.primary_screen_available_geometry()
        h.move(screen.x(), screen.y())

    def apply_full_keyboard_geometry(self) -> None:
        """Apply current top-half geometry without redesign/reposition (T051)."""
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
        if hasattr(h, "_suggestion_bar_layout"):
            h._suggestion_bar_layout.setSpacing(gap)
        letter_area_layout = getattr(h, "_letter_area_layout", None)
        if letter_area_layout is not None:
            letter_area_layout.setSpacing(gap)
        top_pane = getattr(h, "_letter_top_pane_widget", None)
        if top_pane is not None and top_pane.layout() is not None:
            top_pane.layout().setSpacing(gap)
        letters_column = getattr(h, "_letters_column_widget", None)
        if letters_column is not None and letters_column.layout() is not None:
            col_layout = letters_column.layout()
            col_layout.setSpacing(gap)
            for i in range(col_layout.count()):
                nested = col_layout.itemAt(i).layout()
                if nested is not None:
                    nested.setSpacing(gap)
        row3 = getattr(h, "_letter_row3_widget", None)
        if row3 is not None and row3.layout() is not None:
            row3.layout().setSpacing(gap)

        # FR-008d: slim top chrome (no Calibrate) → reclaim height into letter rows.
        chrome_h = int(max(28.0, min(42.0, window_h * 0.07)))
        sugg_h = int(max(40.0, min(64.0, window_h * 0.11)))

        chrome_pt = int(max(10.0, min(16.0, chrome_h * 0.32)))

        for attr in ("minimize_btn", "close_btn"):
            if hasattr(h, attr):
                btn = getattr(h, attr)
                btn.setMinimumHeight(max(28, chrome_h - 4))
                btn.setMaximumHeight(max(28, chrome_h - 4))
                f = btn.font()
                if f.pointSize() != max(9, chrome_pt):
                    f.setPointSize(max(9, chrome_pt))
                    btn.setFont(f)

        if hasattr(h, "suggestion_buttons"):
            for btn in h.suggestion_buttons:
                btn.setMinimumHeight(sugg_h)
                btn.setMaximumHeight(sugg_h)
                f = btn.font()
                target = int(max(12.0, min(20.0, sugg_h * 0.42)))
                if f.pointSize() != target:
                    f.setPointSize(target)
                    btn.setFont(f)

        margins_total = float(margin * 2)
        gaps_total = float(gap * 2)  # control + suggestion + keyboard (2 gaps)
        desired_kb_h = window_h - (margins_total + gaps_total + chrome_h + sugg_h)

        if desired_kb_h < 4 * 28:
            extra = (4 * 28) - desired_kb_h
            shrink_chrome = min(extra * 0.35, chrome_h * 0.15)
            shrink_sugg = min(extra * 0.65, sugg_h * 0.25)
            chrome_h = int(max(26.0, chrome_h - shrink_chrome))
            sugg_h = int(max(36.0, sugg_h - shrink_sugg))
            desired_kb_h = window_h - (margins_total + gaps_total + chrome_h + sugg_h)

        h.keyboard_widget.setMinimumHeight(int(max(0.0, desired_kb_h)))
        h.keyboard_widget.setMaximumHeight(int(max(0.0, desired_kb_h)))

        for widget_attr, widget_h in (
            ("_control_bar_widget", chrome_h),
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
        # Give bottom row a bit more height for the large Calibrate target.
        letter_share = 0.72
        bottom_share = 0.28
        letter_usable = usable * letter_share
        bottom_usable = usable * bottom_share
        key_h = int(max(28.0, min(160.0, letter_usable / 3.0)))
        bottom_h = int(max(key_h + 8, min(140.0, bottom_usable)))
        font_pt = int(max(12.0, min(36.0, key_h * 0.42)))
        calib_pt = int(max(13.0, min(24.0, bottom_h * 0.28)))

        for btn in h.keyboard_widget.findChildren(QPushButton, "keyboardKey"):
            # Space/Enter sit on the taller bottom row with Calibrate.
            if btn is getattr(h, "space_btn", None) or btn is getattr(h, "enter_btn", None):
                btn.setMinimumHeight(bottom_h)
                btn.setMaximumHeight(bottom_h)
            else:
                btn.setMinimumHeight(key_h)
                btn.setMaximumHeight(key_h)
            f = btn.font()
            if f.pointSize() != font_pt:
                f.setPointSize(font_pt)
                btn.setFont(f)

        if hasattr(h, "calibrate_btn") and h.calibrate_btn is not None:
            h.calibrate_btn.setMinimumHeight(bottom_h)
            h.calibrate_btn.setMaximumHeight(bottom_h)
            f = h.calibrate_btn.font()
            if f.pointSize() != calib_pt:
                f.setPointSize(calib_pt)
                h.calibrate_btn.setFont(f)

        stacked_two_row_h = int(2 * key_h + gap)
        stacked_letter_h = int(3 * key_h + 2 * gap)
        letter_area = getattr(h, "_letter_area_widget", None)
        if letter_area is not None:
            letter_area.setMinimumHeight(stacked_letter_h)
            letter_area.setMaximumHeight(stacked_letter_h)
        top_pane = getattr(h, "_letter_top_pane_widget", None)
        if top_pane is not None:
            top_pane.setMinimumHeight(stacked_two_row_h)
            top_pane.setMaximumHeight(stacked_two_row_h)
        row3 = getattr(h, "_letter_row3_widget", None)
        if row3 is not None:
            row3.setMinimumHeight(key_h)
            row3.setMaximumHeight(key_h)
        arrow = getattr(h, "page_switch_btn", None)
        if arrow is not None:
            arrow.setMinimumHeight(stacked_two_row_h)
            arrow.setMaximumHeight(stacked_two_row_h)
            arrow_pt = int(max(18.0, min(48.0, stacked_two_row_h * 0.32)))
            f = arrow.font()
            if f.pointSize() != arrow_pt:
                f.setPointSize(arrow_pt)
                arrow.setFont(f)

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
            keys = inspect_keyboard_layout(h.main_content_widget)
            # Full interactive surface: suggestions + keys + bottom Recalibrate
            # (union of exported gaze targets — includes disabled suggestion slots).
            region_rect = typing_region_rect(
                h.keyboard_widget,
                h.calibrate_btn,
                suggestion_bar_widget=getattr(h, "_suggestion_bar_widget", None),
                layout_keys=keys,
            )
            exporter = h._devtools.layout_exporter() if hasattr(h, "_devtools") else getattr(h, "_layout_exporter", None)
            if exporter is not None:
                h._layout_version = exporter.export(
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
