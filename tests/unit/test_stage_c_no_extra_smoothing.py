"""T031: Stage C pointing path must not stack GazeSmoother / PcaFeatureSmoother."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from gazekey.backend.debug_gaze_dot import DebugGazeOverlay
from gazekey.backend.gaze_sample import GazeSample
from gazekey.ui.virtual_keyboard import VirtualKeyboard

_REPO = Path(__file__).resolve().parents[2]
_SMOOTHER_TOKENS = (
    "GazeSmoother",
    "PcaFeatureSmoother",
    "filter_or_reject",
    "FEATURE_SMOOTHER_ALPHA",
    "GAZE_SMOOTHER_ALPHA",
)


def _source(rel: str) -> str:
    return (_REPO / rel).read_text(encoding="utf-8")


def test_stage_c_pointing_sources_do_not_name_extra_smoothers():
    debug = _source("gazekey/backend/debug_gaze_dot.py")
    startup = _source("gazekey/backend/startup.py")
    main = _source("main.py")
    life = _source("gazekey/backend/lifecycle.py")
    qt_xy = life.split("def debug_filtered_qt_xy", 1)[1].split(
        "def attach_qt_bridge", 1
    )[0]
    bridge = life.split("def attach_debug_get_gaze_info_bridge", 1)[1].split(
        "def release", 1
    )[0]
    wire = startup.split("def wire_debug_gaze_dot", 1)[1]
    offenders: list[str] = []
    for label, src in (
        ("debug_gaze_dot.py", debug),
        ("startup.wire_debug_gaze_dot", wire),
        ("main.py", main),
        ("lifecycle.debug_filtered_qt_xy", qt_xy),
        ("lifecycle.attach_debug_get_gaze_info_bridge", bridge),
    ):
        for token in _SMOOTHER_TOKENS:
            if token in src:
                offenders.append(f"{label}: {token}")
    assert offenders == [], "Stage C pointing path stacked extra smoothing:\n" + "\n".join(
        offenders
    )


def test_debug_overlay_does_not_call_gaze_or_feature_smoother(qapp):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    overlay = DebugGazeOverlay(vk.keyboard_widget, dpr=1.5)
    overlay.update_xy(640.0, 360.0)
    overlay.update_sample(
        GazeSample(
            timestamp_ns=1,
            valid=True,
            x=100.0,
            y=200.0,
            calibrated_x=100.0,
            calibrated_y=200.0,
            tracking_state="SUCCESS",
            left_openness=20.0,
            right_openness=21.0,
        )
    )
    qapp.processEvents()
    assert not hasattr(vk, "_gaze_smoother")
    assert not hasattr(vk, "_feature_smoother")
