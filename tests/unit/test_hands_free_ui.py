"""Hands-free GazeFollower UI waits and continue-prompt rewrites."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from gazekey.backend.hands_free_ui import (
    CALI_INSTRUCTION,
    PREVIEW_BUTTON_TEXT,
    PREVIEW_HOLD_SEC,
    RESULT_CLOSE_TEXT,
    after_listen_event,
    after_listen_keys,
    reset_hands_free_state,
    rewrite_continue_prompt,
    set_monotonic,
)
from gazekey.backend.lifecycle import GazeFollowerLifecycle
from tests.unit.test_lifecycle import FakeGazeFollower, _patch_official

_REPO = Path(__file__).resolve().parents[2]
_HANDS_FREE = _REPO / "gazekey" / "backend" / "hands_free_ui.py"
_FORBIDDEN_IMPORTS = (
    "gazekey.backend.geometry",
    "gazekey.backend.adapter",
    "gazekey.typing.dwell_engine",
    "SVRCalibration",
)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now


def _use_clock() -> _Clock:
    reset_hands_free_state()
    clock = _Clock()
    set_monotonic(clock.monotonic)
    return clock


def teardown_function() -> None:
    reset_hands_free_state()
    set_monotonic(None)


def test_rewrite_continue_prompt_replaces_only_press_key_copy():
    assert rewrite_continue_prompt("Stop Previewing (Tap `Space`)") == PREVIEW_BUTTON_TEXT
    assert rewrite_continue_prompt(
        "Please look at the dot.\nPress `SPACE` to continue."
    ) == CALI_INSTRUCTION
    result = rewrite_continue_prompt(
        "Calibration succeed.\nPress `Space` to continue OR `R` to recalibration"
    )
    assert RESULT_CLOSE_TEXT in result
    assert "Press" not in result
    assert "Space" not in result
    assert rewrite_continue_prompt(CALI_INSTRUCTION) == CALI_INSTRUCTION
    assert rewrite_continue_prompt("Calibration model is fitting.\nPlease wait.") == (
        "Calibration model is fitting.\nPlease wait."
    )


def test_preview_host_auto_stops_after_five_seconds_without_keydown():
    clock = _use_clock()
    host = SimpleNamespace(running=True, update_images=lambda *_a, **_k: None)
    after_listen_event(host, skip_event=False)
    assert host.running is True
    clock.now = PREVIEW_HOLD_SEC - 0.1
    after_listen_event(host, skip_event=False)
    assert host.running is True
    clock.now = PREVIEW_HOLD_SEC
    after_listen_event(host, skip_event=False)
    assert host.running is False


def test_guidance_host_auto_stops_after_two_seconds():
    clock = _use_clock()
    host = SimpleNamespace(running=True)
    after_listen_event(host, skip_event=False)
    clock.now = 1.9
    after_listen_event(host, skip_event=False)
    assert host.running is True
    clock.now = 2.0
    after_listen_event(host, skip_event=False)
    assert host.running is False


def test_skip_event_does_not_stop_collection_and_resets_timer():
    clock = _use_clock()
    host = SimpleNamespace(running=True, update_images=lambda *_a, **_k: None)
    after_listen_event(host, skip_event=False)
    clock.now = 10.0
    after_listen_event(host, skip_event=True)
    assert host.running is True
    after_listen_event(host, skip_event=False)
    assert host.running is True
    clock.now = 15.0
    after_listen_event(host, skip_event=False)
    assert host.running is False


def test_listen_keys_returns_space_after_result_hold():
    clock = _use_clock()
    assert after_listen_keys(None) is None
    clock.now = 1.9
    assert after_listen_keys(None) is None
    clock.now = 2.0
    assert after_listen_keys(None) == "space"


def test_listen_keys_honors_early_space_and_r():
    _use_clock()
    assert after_listen_keys("space") == "space"
    assert after_listen_keys("r") == "r"


def test_construct_sets_hands_free_cali_instruction(monkeypatch):
    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    gf = life.construct()
    assert gf.config.cali_instruction == CALI_INSTRUCTION
    assert "SPACE" not in gf.config.cali_instruction
    assert "Press" not in gf.config.cali_instruction


def test_hands_free_module_does_not_import_geometry_adapter_dwell_or_svr():
    src = _HANDS_FREE.read_text(encoding="utf-8")
    for token in _FORBIDDEN_IMPORTS:
        assert token not in src, token


def test_install_is_idempotent_and_patches_pygame_backend():
    from gazefollower.ui.CameraPreviewerUI import CameraPreviewerUI
    from gazefollower.ui.UIBackend import PyGameUIBackend

    from gazekey.backend.hands_free_ui import install_hands_free_ui

    install_hands_free_ui()
    first_listen = PyGameUIBackend.listen_event
    first_init = CameraPreviewerUI.__init__
    install_hands_free_ui()
    assert PyGameUIBackend.listen_event is first_listen
    assert CameraPreviewerUI.__init__ is first_init
    assert getattr(PyGameUIBackend.listen_event, "_gazekey_hands_free")
    assert getattr(PyGameUIBackend.listen_keys, "_gazekey_hands_free")
    assert getattr(PyGameUIBackend.draw_text, "_gazekey_hands_free")


def test_install_sets_preview_button_text_without_press_space():
    import pygame

    from gazefollower.ui.CameraPreviewerUI import CameraPreviewerUI

    from gazekey.backend.hands_free_ui import install_hands_free_ui

    pygame.init()
    try:
        win = pygame.Surface((200, 200))
        install_hands_free_ui()
        ui = CameraPreviewerUI(win=win, backend_name="pygame")
        assert ui._button_text == PREVIEW_BUTTON_TEXT
        assert "Space" not in ui._button_text
        assert "Press" not in ui._button_text
        assert "click" not in ui._button_text.lower()
    finally:
        pygame.quit()
