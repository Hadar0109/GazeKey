"""Active MVP typing utilities (hit testing, text buffer, smoothing)."""

from gazekey.typing.gaze_smoother import GazeSmoother
from gazekey.typing.key_hit_tester import KeyHitTester, hit_test_layout_keys, hit_test_rects
from gazekey.typing.key_semantics import action_from_button, action_from_label
from gazekey.typing.text_buffer import TextBufferController

__all__ = [
    "GazeSmoother",
    "KeyHitTester",
    "TextBufferController",
    "action_from_button",
    "action_from_label",
    "hit_test_layout_keys",
    "hit_test_rects",
]
