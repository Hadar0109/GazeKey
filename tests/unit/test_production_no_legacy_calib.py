"""T023 / T026: production keyboard does not start legacy calibration or a second window."""

from __future__ import annotations

from gazekey.ui.virtual_keyboard import VirtualKeyboard


def test_production_keyboard_does_not_start_legacy_calibration(qapp):
    vk = VirtualKeyboard()
    assert not hasattr(vk, "tracking_manager")
    assert not hasattr(vk, "_calibration_overlay")
    vk.on_app_started()
    qapp.processEvents()
    assert vk._is_calibrating is False
    assert not hasattr(vk, "tracking_manager")
    assert not hasattr(vk, "_calibration_overlay")


def test_legacy_start_calibration_not_invoked_on_production_startup(qapp):
    vk = VirtualKeyboard()
    assert not hasattr(vk, "_start_calibration_if_needed")
    assert vk._is_calibrating is False
    assert not hasattr(vk, "_calibration_overlay")
    assert not hasattr(vk, "tracking_manager")
