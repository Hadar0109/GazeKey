"""Paged large-target keyboard: page contents and switch isolation (006)."""

from __future__ import annotations

from gazekey.layout.layout_inspector import inspect_keyboard_layout
from gazekey.typing.key_hit_tester import hit_test_layout_keys
from gazekey.ui.virtual_keyboard import VirtualKeyboard

LEFT_LETTERS = frozenset("qwertasdfgzxcv")
RIGHT_LETTERS = frozenset("yuiophjklbnm")


def _show_product_keyboard(qapp) -> VirtualKeyboard:
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    vk._keyboard_layout_builder.update_responsive_sizes()
    vk._keyboard_layout_builder.export_keyboard_layout()
    qapp.processEvents()
    return vk


def _letter_actions(keys) -> set[str]:
    return {
        str(k.key_action).lower()
        for k in keys
        if len(str(k.key_action)) == 1 and str(k.key_action).isalpha()
    }


def test_default_letter_page_is_left(qapp):
    vk = _show_product_keyboard(qapp)
    assert vk.letter_page == "left"


def test_left_page_exports_qwert_asdfg_zxcv_with_shift_and_backspace(qapp):
    vk = _show_product_keyboard(qapp)
    keys = inspect_keyboard_layout(vk.main_content_widget)
    letters = _letter_actions(keys)
    assert LEFT_LETTERS <= letters
    actions = {str(k.key_action) for k in keys}
    assert "SHIFT" in actions
    assert "BACKSPACE" in actions

    z_key = next(k for k in keys if str(k.key_action).lower() == "z")
    shift = next(k for k in keys if k.key_action == "SHIFT")
    backspace = next(k for k in keys if k.key_action == "BACKSPACE")
    row_tol = max(8.0, float(z_key.rect.height()) * 0.6)
    assert abs(shift.center[1] - z_key.center[1]) < row_tol
    assert abs(backspace.center[1] - z_key.center[1]) < row_tol


def test_left_page_export_omits_right_page_letters(qapp):
    vk = _show_product_keyboard(qapp)
    keys = inspect_keyboard_layout(vk.main_content_widget)
    letters = _letter_actions(keys)
    assert letters.isdisjoint(RIGHT_LETTERS)


def test_switch_letter_page_immediately_isolates_previous_page_letters(qapp):
    """T013 checkpoint / T031 regression: previous-page letters gone without deleteLater wait."""
    vk = _show_product_keyboard(qapp)
    before = inspect_keyboard_layout(vk.main_content_widget)
    left_ids = [
        k.key_id
        for k in before
        if len(str(k.key_action)) == 1 and str(k.key_action).lower() in LEFT_LETTERS
    ]
    left_centers = [
        (k.key_id, k.center)
        for k in before
        if len(str(k.key_action)) == 1 and str(k.key_action).lower() in LEFT_LETTERS
    ]
    assert left_ids

    vk.switch_letter_page("right")

    after = inspect_keyboard_layout(vk.main_content_widget)
    after_ids = {k.key_id for k in after}
    after_letters = _letter_actions(after)
    for key_id in left_ids:
        assert key_id not in after_ids
    assert after_letters.isdisjoint(LEFT_LETTERS)

    for key_id, (cx, cy) in left_centers:
        idx = hit_test_layout_keys(after, cx, cy)
        if idx is None:
            continue
        hit = after[idx]
        assert hit.key_id != key_id
        hit_action = str(hit.key_action).lower()
        assert hit_action not in LEFT_LETTERS


def test_activating_visible_arrow_switches_page_and_arrow_identity(qapp):
    """T018: visible → switches to right page with ←; left letters gone immediately."""
    vk = _show_product_keyboard(qapp)
    assert vk.letter_page == "left"
    arrow = vk.page_switch_btn
    assert arrow.property("gazeKeyId") == "system:page_right"
    arrow.click()

    assert vk.letter_page == "right"
    new_arrow = vk.page_switch_btn
    assert new_arrow is not None
    assert new_arrow.property("gazeKeyId") == "system:page_left"
    assert new_arrow.text() == "←"
    keys = inspect_keyboard_layout(vk.main_content_widget)
    letters = _letter_actions(keys)
    assert letters.isdisjoint(LEFT_LETTERS)
    assert RIGHT_LETTERS <= letters
    ids = {k.key_id for k in keys}
    assert "system:page_left" in ids
    assert "system:page_right" not in ids


def test_letter_page_survives_minimize_and_restore(qapp):
    """T022: minimize/restore must not reset the current letter page."""
    vk = _show_product_keyboard(qapp)
    vk.switch_letter_page("right")
    assert vk.letter_page == "right"
    vk.on_minimize_clicked()
    vk.on_restore_clicked()
    qapp.processEvents()
    assert vk.letter_page == "right"
    keys = inspect_keyboard_layout(vk.main_content_widget)
    assert RIGHT_LETTERS <= _letter_actions(keys)


def test_recalibrate_return_resets_to_left_plain_show_does_not(qapp, monkeypatch):
    """T023: only the post-official-recalibrate hook resets to left."""
    from types import SimpleNamespace

    from PySide6.QtGui import QShowEvent

    vk = _show_product_keyboard(qapp)
    vk.switch_letter_page("right")
    vk.showEvent(QShowEvent())
    qapp.processEvents()
    assert vk.letter_page == "right"

    monkeypatch.setattr(
        "gazekey.backend.startup.run_official_recalibrate",
        lambda lifecycle, keyboard: True,
    )
    vk._gf_lifecycle = SimpleNamespace()
    vk.on_calibrate_clicked()
    assert vk.letter_page == "left"
    keys = inspect_keyboard_layout(vk.main_content_widget)
    letters = _letter_actions(keys)
    assert LEFT_LETTERS <= letters
    assert letters.isdisjoint(RIGHT_LETTERS)


def test_page_switch_preserves_shift_armed_and_typing_context(qapp):
    """T021: rebuild must not clear one-shot Shift or suggestion prefix/epoch."""
    vk = _show_product_keyboard(qapp)
    vk._typing_runtime.session.activate()
    vk._typing_runtime.session.arm_shift()
    epoch = vk._typing_context.get_epoch()
    prefix = vk._typing_context.get_prefix()
    vk.switch_letter_page("right")
    assert vk._typing_runtime.session.shift_oneshot_armed is True
    assert vk._typing_context.get_epoch() == epoch
    assert vk._typing_context.get_prefix() == prefix
    assert vk.shift_btn.isChecked()
    assert next(iter(vk.letter_keys.values())).text().isupper()


def _assert_shift_backspace_hit_testable(keys) -> None:
    shift = next(k for k in keys if k.key_action == "SHIFT")
    backspace = next(k for k in keys if k.key_action == "BACKSPACE")
    for key in (shift, backspace):
        idx = hit_test_layout_keys(keys, key.center[0], key.center[1])
        assert idx is not None
        assert keys[idx].key_id == key.key_id


def _assert_suggestion_slots_exported_when_blank(vk, keys) -> None:
    assert len(vk.suggestion_buttons) == 3
    suggestion_ids = [k.key_id for k in keys if str(k.key_id).startswith("suggestion:")]
    assert suggestion_ids == ["suggestion:0", "suggestion:1", "suggestion:2"]
    for btn in vk.suggestion_buttons:
        assert not btn.isEnabled()
        assert btn.text() == ""


def test_shift_backspace_and_suggestions_on_both_pages(qapp):
    """T025: Shift/Backspace hit-testable on both pages; blank suggestion slots exported."""
    vk = _show_product_keyboard(qapp)
    left_keys = inspect_keyboard_layout(vk.main_content_widget)
    _assert_shift_backspace_hit_testable(left_keys)
    _assert_suggestion_slots_exported_when_blank(vk, left_keys)

    vk.switch_letter_page("right")
    right_keys = inspect_keyboard_layout(vk.main_content_widget)
    _assert_shift_backspace_hit_testable(right_keys)
    _assert_suggestion_slots_exported_when_blank(vk, right_keys)
    actions = {str(k.key_action) for k in right_keys}
    assert "SHIFT" in actions
    assert "BACKSPACE" in actions


def test_left_page_letters_form_three_distinct_rows(qapp):
    """T033: QWERT / ASDFG / ZXCV stay three inspect rows despite the two-row arrow."""
    vk = _show_product_keyboard(qapp)
    assert vk.letter_page == "left"
    keys = inspect_keyboard_layout(vk.main_content_widget)
    by_action = {
        str(k.key_action).lower(): k
        for k in keys
        if len(str(k.key_action)) == 1 and str(k.key_action).isalpha()
    }
    row1 = [by_action[ch].row_index for ch in "qwert"]
    row2 = [by_action[ch].row_index for ch in "asdfg"]
    row3 = [by_action[ch].row_index for ch in "zxcv"]
    assert len(set(row1)) == 1, row1
    assert len(set(row2)) == 1, row2
    assert len(set(row3)) == 1, row3
    assert len({row1[0], row2[0], row3[0]}) == 3, (row1[0], row2[0], row3[0])
    assert row1[0] < row2[0] < row3[0]


def test_calibrate_exported_on_both_pages(qapp):
    """T029: Calibrate stays system:calibrate on both letter pages."""
    vk = _show_product_keyboard(qapp)
    left = inspect_keyboard_layout(vk.main_content_widget)
    assert any(k.key_id == "system:calibrate" for k in left)
    assert vk.calibrate_btn.property("gazeKeyId") == "system:calibrate"
    calib_left = vk.calibrate_btn

    vk.switch_letter_page("right")
    right = inspect_keyboard_layout(vk.main_content_widget)
    assert any(k.key_id == "system:calibrate" for k in right)
    assert vk.calibrate_btn is calib_left
    assert vk.calibrate_btn.property("gazeKeyAction") == "system:calibrate"
    idx = hit_test_layout_keys(
        right,
        next(k for k in right if k.key_id == "system:calibrate").center[0],
        next(k for k in right if k.key_id == "system:calibrate").center[1],
    )
    assert idx is not None
    assert right[idx].key_id == "system:calibrate"


def _attach_fake_os(vk: VirtualKeyboard):
    from gazekey.input.os_input_adapter import FakeOsInputAdapter
    from gazekey.typing.action_dispatcher import ActionDispatcher

    fake = FakeOsInputAdapter()
    vk._action_dispatcher = ActionDispatcher(fake)
    vk._typing_runtime.dispatcher = vk._action_dispatcher
    vk._action_dispatcher.on_action_delivered(vk._on_os_action_delivered)
    vk._typing_runtime.session.activate()
    vk._typing_runtime.set_os_inject_enabled(True)
    return fake


def _assert_letters_case(vk: VirtualKeyboard, *, upper: bool) -> None:
    assert vk.letter_keys
    for char, btn in vk.letter_keys.items():
        expected = char.upper() if upper else char.lower()
        assert btn.text() == expected, f"{char!r} shown as {btn.text()!r}"


def test_shift_oneshot_returns_letters_to_lowercase_on_left_page(qapp):
    vk = _show_product_keyboard(qapp)
    fake = _attach_fake_os(vk)
    _assert_letters_case(vk, upper=False)

    vk.on_shift_clicked(True)
    assert vk._typing_runtime.session.shift_oneshot_armed is True
    assert vk.shift_btn.isChecked()
    _assert_letters_case(vk, upper=True)

    vk.on_key_pressed("q")
    assert fake.injected[-1].text == "Q"
    assert vk._typing_runtime.session.shift_oneshot_armed is False
    assert not vk.shift_btn.isChecked()
    _assert_letters_case(vk, upper=False)


def test_shift_oneshot_returns_letters_to_lowercase_on_right_page(qapp):
    vk = _show_product_keyboard(qapp)
    fake = _attach_fake_os(vk)
    vk.on_shift_clicked(True)
    _assert_letters_case(vk, upper=True)

    vk.switch_letter_page("right")
    assert vk._typing_runtime.session.shift_oneshot_armed is True
    _assert_letters_case(vk, upper=True)
    assert "h" in vk.letter_keys

    vk.on_key_pressed("h")
    assert fake.injected[-1].text == "H"
    assert vk._typing_runtime.session.shift_oneshot_armed is False
    assert not vk.shift_btn.isChecked()
    _assert_letters_case(vk, upper=False)


def test_shift_stays_uppercase_until_a_letter_is_typed(qapp):
    vk = _show_product_keyboard(qapp)
    _attach_fake_os(vk)
    vk.on_shift_clicked(True)
    vk.switch_letter_page("right")
    vk.switch_letter_page("left")
    assert vk._typing_runtime.session.shift_oneshot_armed is True
    _assert_letters_case(vk, upper=True)
    vk._sync_typing_session_ui()
    assert vk._typing_runtime.session.shift_oneshot_armed is True
    _assert_letters_case(vk, upper=True)
