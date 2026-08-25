"""Layout geometry and calibration-target alignment tests (FR-024)."""

from __future__ import annotations

from unittest.mock import MagicMock

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QPushButton, QWidget

from gazekey.layout.layout_inspector import inspect_keyboard_layout
from gazekey.typing.gaze_ui_mapper import letter_keys_region_rect
from tools.debug.layout_geometry_check import format_geometry_report, verify_keyboard_geometry
from tools.evaluation.benchmark_runner import predict_key_at
from tools.evaluation.session_paths import ensure_session_dir, geometry_check_path
from gazekey.typing.key_hit_tester import (
    GAZE_HIT_OBJECT_NAMES,
    KEY_OBJECT_NAME,
    KeyHitTester,
    hit_test_layout_keys,
)


def _make_key_button(parent: QWidget, label: str, x: int, y: int) -> QPushButton:
    btn = QPushButton(label, parent)
    btn.setObjectName(KEY_OBJECT_NAME)
    btn.setGeometry(x, y, 60, 40)
    btn.show()
    return btn


def _build_test_keyboard(qapp) -> QWidget:
    root = QWidget()
    root.setGeometry(0, 0, 800, 400)
    # Row 0
    _make_key_button(root, "Q", 50, 50)
    _make_key_button(root, "W", 120, 50)
    _make_key_button(root, "E", 190, 50)
    _make_key_button(root, "T", 260, 50)
    _make_key_button(root, "Y", 330, 50)
    _make_key_button(root, "U", 400, 50)
    _make_key_button(root, "I", 470, 50)
    _make_key_button(root, "O", 540, 50)
    _make_key_button(root, "P", 610, 50)
    # Row 1
    _make_key_button(root, "A", 80, 110)
    _make_key_button(root, "S", 150, 110)
    _make_key_button(root, "D", 220, 110)
    _make_key_button(root, "G", 290, 110)
    _make_key_button(root, "H", 360, 110)
    _make_key_button(root, "J", 430, 110)
    _make_key_button(root, "K", 500, 110)
    _make_key_button(root, "L", 570, 110)
    # Row 2
    _make_key_button(root, "Z", 110, 170)
    _make_key_button(root, "X", 180, 170)
    _make_key_button(root, "C", 250, 170)
    _make_key_button(root, "V", 320, 170)
    _make_key_button(root, "B", 390, 170)
    _make_key_button(root, "N", 460, 170)
    _make_key_button(root, "M", 530, 170)
    _make_key_button(root, "Space", 200, 240)
    root.show()
    qapp.processEvents()
    return root


def test_layout_inspector_matches_key_hit_tester(qapp, tmp_path):  # noqa: ARG001
    root = _build_test_keyboard(qapp)
    layout_keys, mismatches = verify_keyboard_geometry(root)
    assert layout_keys, "expected keys from test keyboard"
    assert not mismatches, format_geometry_report(layout_keys, mismatches)

    report = format_geometry_report(layout_keys, mismatches)
    session_id = "layout-geometry"
    ensure_session_dir(session_id, runs_dir=tmp_path)
    geometry_check_path(session_id, runs_dir=tmp_path).write_text(report, encoding="utf-8")


def test_benchmark_hit_test_matches_key_hit_tester(qapp):
    root = _build_test_keyboard(qapp)
    layout_keys = inspect_keyboard_layout(root)
    tester = KeyHitTester(root)
    tester.refresh()
    btn_by_id = {id(r.button): r for r in layout_keys}
    for k in layout_keys:
        cx, cy = k.center
        idx = hit_test_layout_keys(layout_keys, cx, cy)
        assert idx is not None
        predicted = predict_key_at(cx, cy, layout_keys)
        assert predicted.key_id == layout_keys[idx].key_id
        btn = tester.hit_test(cx, cy)
        assert btn is not None
        assert id(btn) == id(btn_by_id[id(btn)].button)


def test_product_keyboard_has_three_fixed_suggestion_slots(qapp):
    """003: suggestion:0..2 always exported; disabled slots not dwellable."""
    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    vk._keyboard_layout_builder.export_keyboard_layout()
    qapp.processEvents()

    assert len(vk.suggestion_buttons) == 3
    for i, btn in enumerate(vk.suggestion_buttons):
        assert btn.property("gazeKeyId") == f"suggestion:{i}"
        assert btn.objectName() == "gazeTarget"
        assert not btn.isEnabled()
        assert btn.text() == ""

    keys = inspect_keyboard_layout(vk.main_content_widget)
    suggestion_ids = [k.key_id for k in keys if str(k.key_id).startswith("suggestion:")]
    assert suggestion_ids == ["suggestion:0", "suggestion:1", "suggestion:2"]

    # Disabled slots must not be hit-testable / dwellable.
    for k in keys:
        if str(k.key_id).startswith("suggestion:"):
            cx, cy = k.center
            idx = hit_test_layout_keys(keys, cx, cy)
            if idx is not None:
                hit = keys[idx]
                assert not str(hit.key_id).startswith("suggestion:"), (
                    f"disabled suggestion hit: {hit.key_id}"
                )

    # No removed chrome in product layout.
    actions = {str(k.key_action) for k in keys}
    labels = {str(k.key_label) for k in keys}
    assert "PAUSE_RESUME" not in actions
    assert "Ctrl" not in labels
    assert "Alt" not in labels


def test_calibrate_is_large_bottom_row_recovery_target(qapp):
    """003 FR-008d: Calibrate left of Space, larger than a letter key, dwellable."""
    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    vk._keyboard_layout_builder.update_responsive_sizes()
    vk._keyboard_layout_builder.export_keyboard_layout()
    qapp.processEvents()

    assert vk.calibrate_btn.objectName() == "gazeTarget"
    assert vk.calibrate_btn.property("gazeKeyId") == "system:calibrate"
    assert vk.calibrate_btn.isEnabled()
    assert vk.calibrate_btn.parent() is not None
    # Not in the slim top chrome row.
    assert vk.calibrate_btn.parentWidget() is not vk._control_bar_widget

    keys = inspect_keyboard_layout(vk.main_content_widget)
    by_id = {k.key_id: k for k in keys}
    assert "system:calibrate" in by_id
    calib = by_id["system:calibrate"]

    # Find a typical letter key for size comparison.
    letter = next(
        (k for k in keys if len(str(k.key_action)) == 1 and str(k.key_action).isalpha()),
        None,
    )
    assert letter is not None
    calib_area = calib.rect.width() * calib.rect.height()
    letter_area = letter.rect.width() * letter.rect.height()
    assert calib_area > letter_area, (
        f"calibrate area {calib_area} should exceed letter area {letter_area}"
    )

    space = next((k for k in keys if k.key_action == " "), None)
    assert space is not None
    # Calibrate left of Space on the same bottom band.
    assert calib.center[0] < space.center[0]
    assert abs(calib.center[1] - space.center[1]) < max(24.0, calib.rect.height() * 0.6)

    # Hit-test center selects calibrate (enabled gazeTarget).
    idx = hit_test_layout_keys(keys, calib.center[0], calib.center[1])
    assert idx is not None
    assert keys[idx].key_id == "system:calibrate"


def test_typing_region_rect_includes_suggestion_row_and_gaze_targets(qapp):
    """003 geometry: typing_region_rect covers suggestions + keys + Recalibrate."""
    from gazekey.typing.gaze_ui_mapper import typing_region_from_layout_keys, typing_region_rect
    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    vk._keyboard_layout_builder.update_responsive_sizes()
    vk._keyboard_layout_builder.export_keyboard_layout()
    qapp.processEvents()

    keys = inspect_keyboard_layout(vk.main_content_widget)
    region = typing_region_from_layout_keys(keys)
    assert not region.isEmpty()

    # Suggestion slots (including disabled) are inside the region.
    suggestion_keys = [k for k in keys if str(k.key_id).startswith("suggestion:")]
    assert len(suggestion_keys) == 3
    for k in suggestion_keys:
        assert region.contains(k.rect.center()), f"{k.key_id} center outside typing region"

    # Letter key, Shift, Backspace, Space, Enter, Recalibrate, and page arrow.
    letter = next(k for k in keys if len(str(k.key_action)) == 1 and str(k.key_action).isalpha())
    shift = next(k for k in keys if k.key_action == "SHIFT")
    backspace = next(k for k in keys if k.key_action == "BACKSPACE")
    space = next(k for k in keys if k.key_action == " ")
    enter = next(k for k in keys if k.key_action == "ENTER")
    calib = next(k for k in keys if k.key_id == "system:calibrate")
    arrow = next(
        k
        for k in keys
        if k.key_id in ("system:page_right", "system:page_left")
    )
    for k in (letter, shift, backspace, space, enter, calib, arrow):
        assert region.contains(k.rect.center()), f"{k.key_id} outside typing region"

    # Export helper with layout_keys matches union helper.
    via_api = typing_region_rect(
        vk.keyboard_widget,
        vk.calibrate_btn,
        suggestion_bar_widget=vk._suggestion_bar_widget,
        layout_keys=keys,
    )
    assert via_api == region

    # Region is taller than keyboard widget alone (suggestion row above keys).
    kb = letter_keys_region_rect(vk.keyboard_widget)
    assert region.top() <= kb.top()
    assert region.height() >= kb.height()


def _show_product_keyboard(qapp):
    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    vk._keyboard_layout_builder.update_responsive_sizes()
    vk._keyboard_layout_builder.export_keyboard_layout()
    qapp.processEvents()
    return vk


def _letter_keys(keys):
    return [
        k
        for k in keys
        if len(str(k.key_action)) == 1 and str(k.key_action).isalpha()
    ]


def test_page_arrow_width_is_12_to_22_percent_of_letter_area(qapp):
    """006 SC-001: arrow pane ~17% of letter-area width (research R2 5:1 band)."""
    vk = _show_product_keyboard(qapp)
    area = getattr(vk, "_letter_area_widget", None)
    assert area is not None, "expected letter-area pane for paged layout"
    area_w = float(area.width())
    assert area_w > 0

    keys = inspect_keyboard_layout(vk.main_content_widget)
    by_id = {k.key_id: k for k in keys}
    assert "system:page_right" in by_id
    arrow_w = float(by_id["system:page_right"].rect.width())
    fraction = arrow_w / area_w
    assert 0.12 <= fraction <= 0.22, f"arrow/letter-area width fraction {fraction:.3f}"


def test_mean_visible_letter_width_exceeds_letter_area_over_ten(qapp):
    """006 SC-001: mean letter width > letter-area/10 (relative, not pixels)."""
    vk = _show_product_keyboard(qapp)
    area = getattr(vk, "_letter_area_widget", None)
    assert area is not None, "expected letter-area pane for paged layout"
    area_w = float(area.width())
    assert area_w > 0

    keys = inspect_keyboard_layout(vk.main_content_widget)
    letters = _letter_keys(keys)
    assert letters, "expected visible letter keys"
    mean_w = sum(float(k.rect.width()) for k in letters) / float(len(letters))
    assert mean_w > area_w / 10.0, (
        f"mean letter width {mean_w:.1f} should exceed letter-area/10 {area_w / 10.0:.1f}"
    )


def test_page_arrow_height_spans_first_two_letter_rows(qapp):
    """006: one tall arrow beside rows 1–2 only; third row is full width (R1/R2)."""
    vk = _show_product_keyboard(qapp)
    keys = inspect_keyboard_layout(vk.main_content_widget)
    by_id = {k.key_id: k for k in keys}
    assert "system:page_right" in by_id
    arrow = by_id["system:page_right"]
    letters = _letter_keys(keys)
    assert letters
    row1 = [k for k in letters if str(k.key_action).lower() in "qwert"]
    row2 = [k for k in letters if str(k.key_action).lower() in "asdfg"]
    row3 = [k for k in letters if str(k.key_action).lower() in "zxcv"]
    assert row1 and row2 and row3
    two_top = min(int(k.rect.top()) for k in row1)
    two_bottom = max(int(k.rect.bottom()) for k in row2)
    row3_top = min(int(k.rect.top()) for k in row3)
    mean_letter_h = sum(float(k.rect.height()) for k in letters) / float(len(letters))
    assert float(arrow.rect.height()) > mean_letter_h * 1.4
    assert float(arrow.rect.height()) < mean_letter_h * 2.6
    slack = max(8.0, mean_letter_h * 0.35)
    assert abs(int(arrow.rect.top()) - two_top) <= slack
    assert abs(int(arrow.rect.bottom()) - two_bottom) <= slack
    assert int(arrow.rect.bottom()) <= row3_top + int(slack * 0.25)
    assert int(arrow.rect.bottom()) < int(row3[0].center[1])


def test_typing_region_includes_page_arrow_on_both_pages(qapp):
    """T032: typing_region_rect unions the visible system:page_* arrow (006)."""
    from gazekey.typing.gaze_ui_mapper import typing_region_from_layout_keys, typing_region_rect

    vk = _show_product_keyboard(qapp)
    for page, arrow_id in (("left", "system:page_right"), ("right", "system:page_left")):
        if vk.letter_page != page:
            vk.switch_letter_page(page)
        keys = inspect_keyboard_layout(vk.main_content_widget)
        region = typing_region_from_layout_keys(keys)
        by_id = {k.key_id: k for k in keys}
        assert arrow_id in by_id
        assert region.contains(by_id[arrow_id].rect.center())
        via_api = typing_region_rect(
            vk.keyboard_widget,
            vk.calibrate_btn,
            suggestion_bar_widget=vk._suggestion_bar_widget,
            layout_keys=keys,
        )
        assert via_api == region
        for action in ("SHIFT", "BACKSPACE", " ", "ENTER"):
            key = next(k for k in keys if k.key_action == action)
            assert region.contains(key.rect.center()), f"{page} {action} outside region"
        assert any(k.key_id == "system:calibrate" for k in keys)
        assert region.contains(by_id["system:calibrate"].rect.center())
