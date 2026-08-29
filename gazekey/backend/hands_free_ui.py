"""Hands-free continuation for official GazeFollower pygame UI.

Patches pygame event waits and continue-prompt copy only. Does not change
calibration math, gaze estimation, geometry, or collection timers.
"""

from __future__ import annotations

import time
from typing import Any, Callable

PREVIEW_HOLD_SEC = 5.0
GUIDANCE_HOLD_SEC = 2.0
RESULT_HOLD_SEC = 2.0

PREVIEW_BUTTON_TEXT = "Continuing automatically"
CALI_INSTRUCTION = "Please look at the dot.\nCalibration will start automatically."
RESULT_CLOSE_TEXT = "This screen will close automatically."

CONTINUE_PROMPT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("Stop Previewing (Tap `Space`)", PREVIEW_BUTTON_TEXT),
    ("Press `SPACE` to continue.", "Calibration will start automatically."),
    (
        "Press `Space` to continue OR `R` to recalibration",
        RESULT_CLOSE_TEXT,
    ),
)

_PATCH_MARK = "_gazekey_hands_free"

_monotonic: Callable[[], float] = time.monotonic
_host_started: dict[int, float] = {}
_result_t0: float | None = None


def rewrite_continue_prompt(text: str) -> str:
    """Replace official press-key continue prompts. Idempotent."""
    rewritten = text
    for old, new in CONTINUE_PROMPT_REPLACEMENTS:
        rewritten = rewritten.replace(old, new)
    return rewritten


def set_monotonic(monotonic_fn: Callable[[], float] | None) -> None:
    """Test hook: inject a fake clock. Pass None to restore time.monotonic."""
    global _monotonic
    _monotonic = time.monotonic if monotonic_fn is None else monotonic_fn


def reset_hands_free_state() -> None:
    """Test hook: clear per-host / result timers."""
    global _result_t0
    _host_started.clear()
    _result_t0 = None


def _hold_sec(host: Any) -> float:
    if hasattr(host, "update_images") or hasattr(host, "stop_button_rect"):
        return PREVIEW_HOLD_SEC
    return GUIDANCE_HOLD_SEC


def after_listen_event(host: Any, skip_event: bool) -> None:
    """Auto-stop preview/guidance waits. No-op during collection/fit."""
    if skip_event:
        _host_started.pop(id(host), None)
        return
    started = _host_started.setdefault(id(host), _monotonic())
    if _monotonic() - started >= _hold_sec(host):
        host.running = False


def after_listen_keys(pressed: str | None) -> str | None:
    """Honor a real key; otherwise auto-accept after RESULT_HOLD_SEC."""
    global _result_t0
    if pressed is not None:
        _result_t0 = None
        return pressed
    now = _monotonic()
    if _result_t0 is None:
        _result_t0 = now
    if now - _result_t0 >= RESULT_HOLD_SEC:
        _result_t0 = None
        return "space"
    return None


def _wrap_text_method(orig: Callable[..., Any]) -> Callable[..., Any]:
    def wrapped(self: Any, text: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(text, str):
            text = rewrite_continue_prompt(text)
        return orig(self, text, *args, **kwargs)

    setattr(wrapped, _PATCH_MARK, True)
    return wrapped


def install_hands_free_ui() -> None:
    """Idempotent GazeKey patches on official pygame UI entry points."""
    from gazefollower.ui.CameraPreviewerUI import CameraPreviewerUI
    from gazefollower.ui.UIBackend import PyGameUIBackend

    if getattr(PyGameUIBackend.listen_event, _PATCH_MARK, False):
        return

    orig_listen_event = PyGameUIBackend.listen_event
    orig_listen_keys = PyGameUIBackend.listen_keys
    orig_preview_init = CameraPreviewerUI.__init__

    def listen_event(self: Any, host: Any, skip_event: bool = False) -> None:
        orig_listen_event(self, host, skip_event=skip_event)
        after_listen_event(host, skip_event)

    def listen_keys(self: Any, key: Any) -> str | None:
        return after_listen_keys(orig_listen_keys(self, key))

    def preview_init(self: Any, *args: Any, **kwargs: Any) -> None:
        orig_preview_init(self, *args, **kwargs)
        self._button_text = PREVIEW_BUTTON_TEXT

    setattr(listen_event, _PATCH_MARK, True)
    setattr(listen_keys, _PATCH_MARK, True)
    setattr(preview_init, _PATCH_MARK, True)

    PyGameUIBackend.listen_event = listen_event
    PyGameUIBackend.listen_keys = listen_keys
    PyGameUIBackend.draw_text = _wrap_text_method(PyGameUIBackend.draw_text)
    PyGameUIBackend.draw_text_on_screen_center = _wrap_text_method(
        PyGameUIBackend.draw_text_on_screen_center
    )
    PyGameUIBackend.draw_text_in_bottom_right_corner = _wrap_text_method(
        PyGameUIBackend.draw_text_in_bottom_right_corner
    )
    CameraPreviewerUI.__init__ = preview_init
