"""T023 / T026: production keyboard does not start legacy calibration or a second window."""

from __future__ import annotations

from unittest.mock import MagicMock

from gazekey.ui.virtual_keyboard import VirtualKeyboard


def test_production_keyboard_does_not_start_legacy_calibration(qapp, monkeypatch):
    monkeypatch.setattr(
        "gazekey.runtime.tracking_controller.TrackingController.ensure_started",
        MagicMock(return_value=True),
    )
    vk = VirtualKeyboard()
    assert vk._needs_first_calibration is False
    assert vk.tracking_manager is None
    assert vk._calibration_overlay is None
    vk.on_app_started()
    qapp.processEvents()
    assert vk.tracking_manager is None
    assert vk._is_calibrating is False
    assert vk._calibration_overlay is None


def test_legacy_start_calibration_not_invoked_on_production_startup(qapp):
    vk = VirtualKeyboard()
    vk._start_calibration_if_needed()
    assert vk._calibration_overlay is None
    assert vk.tracking_manager is None
    assert vk._is_calibrating is False
