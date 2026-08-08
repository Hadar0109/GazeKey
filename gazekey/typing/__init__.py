"""Active product typing utilities (hit testing, semantics, smoothing)."""

from gazekey.typing.gaze_smoother import GazeSmoother
from gazekey.typing.key_hit_tester import KeyHitTester, hit_test_layout_keys, hit_test_rects
from gazekey.typing.key_semantics import action_from_button, action_from_label

__all__ = [
    "GazeSmoother",
    "KeyHitTester",
    "action_from_button",
    "action_from_label",
    "hit_test_layout_keys",
    "hit_test_rects",
]
