"""T041: invalid GazeSample cancels in-progress dwell and publishes no OS inject."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QRect

from gazekey.backend.gaze_sample import GazeSample
from gazekey.input.os_input_adapter import FakeOsInputAdapter
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.dwell_engine import DWELL_SEC, DwellEngine, DwellPhase
from gazekey.typing.gaze_typing_runtime import GazeTypingRuntime, MappedGazePoint
from gazekey.typing.key_action import KeyAction
from gazekey.typing.typing_session import TypingSession
from gazekey.ui.virtual_keyboard import VirtualKeyboard


def _key(key_id: str, action: str, rect: QRect) -> SimpleNamespace:
    return SimpleNamespace(key_id=key_id, key_action=action, key_label=action, rect=rect)


def _valid(x: float, y: float) -> GazeSample:
    return GazeSample(
        timestamp_ns=1,
        valid=True,
        x=x,
        y=y,
        calibrated_x=x,
        calibrated_y=y,
        tracking_state="SUCCESS",
        left_openness=20.0,
        right_openness=21.0,
    )


def _invalid() -> GazeSample:
    return GazeSample(
        timestamp_ns=2,
        valid=False,
        x=20.0,
        y=20.0,
        calibrated_x=None,
        calibrated_y=None,
        tracking_state="SUCCESS",
        left_openness=5.0,
        right_openness=20.0,
    )


def test_invalid_sample_cancels_in_progress_dwell_and_publishes_no_key_action():
    adapter = FakeOsInputAdapter()
    session = TypingSession()
    session.activate()
    dwell = DwellEngine()
    runtime = GazeTypingRuntime(session, dwell, ActionDispatcher(adapter))
    keys = [_key("key_a", "a", QRect(0, 0, 40, 40))]

    runtime.on_mapped_gaze(MappedGazePoint.from_gaze_sample(_valid(20, 20)), 0.4, keys)
    assert dwell.phase is DwellPhase.PROGRESSING
    assert adapter.injected == []

    result = runtime.on_mapped_gaze(MappedGazePoint.from_gaze_sample(_invalid()), 0.05, keys)
    assert result.published is None
    assert result.dwell.fired is False
    assert dwell.phase is DwellPhase.CANCELLED
    assert adapter.injected == []

    result = runtime.on_mapped_gaze(
        MappedGazePoint.from_gaze_sample(_valid(20, 20)), DWELL_SEC, keys
    )
    assert result.published is not None
    assert isinstance(result.published, KeyAction)


def test_invalid_openness_on_gaze_sample_cancels_keyboard_dwell(qapp, monkeypatch):
    times = iter([100.0, 100.4, 100.45, 100.5, 100.55, 100.6])
    monkeypatch.setattr("gazekey.runtime.gaze_loop.time.perf_counter", lambda: next(times))
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    vk._official_gaze_ready = True
    vk._layout_keys = [_key("key_a", "a", QRect(0, 0, 40, 40))]
    vk._ensure_typing_auto_started()
    published: list[object] = []
    monkeypatch.setattr(
        vk._typing_runtime.dispatcher,
        "publish",
        lambda action: published.append(action),
    )
    vk._gaze_loop.on_gaze_sample(_valid(20, 20))
    vk._gaze_loop.on_gaze_sample(_valid(20, 20))
    assert vk._dwell_engine.phase is DwellPhase.PROGRESSING
    vk._gaze_loop.on_gaze_sample(_invalid())
    assert vk._dwell_engine.phase is DwellPhase.CANCELLED
    assert published == []
    vk._gaze_smoother.filter_or_reject = MagicMock()
    vk._gaze_loop.on_gaze_sample(_invalid())
    vk._gaze_smoother.filter_or_reject.assert_not_called()
