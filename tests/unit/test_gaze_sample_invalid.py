"""T015: invalid GazeSample cases; no hold-last."""

from __future__ import annotations

from types import SimpleNamespace

from gazekey.backend.adapter import gaze_info_to_sample


def _info(**overrides) -> SimpleNamespace:
    data = dict(
        timestamp=1,
        status=True,
        tracking_state=SimpleNamespace(name="SUCCESS"),
        filtered_gaze_coordinates=(100.0, 200.0),
        calibrated_gaze_coordinates=(100.0, 200.0),
        left_openness=40.0,
        right_openness=41.0,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_openness_at_threshold_is_invalid():
    sample = gaze_info_to_sample(_info(left_openness=10.0, right_openness=40.0))
    assert sample.valid is False


def test_openness_below_threshold_is_invalid():
    sample = gaze_info_to_sample(_info(left_openness=40.0, right_openness=9.9))
    assert sample.valid is False


def test_non_success_tracking_is_invalid():
    sample = gaze_info_to_sample(
        _info(tracking_state=SimpleNamespace(name="FACE_MISSING"))
    )
    assert sample.valid is False
    assert sample.tracking_state == "FACE_MISSING"


def test_non_finite_xy_is_invalid():
    sample = gaze_info_to_sample(_info(filtered_gaze_coordinates=(float("nan"), 1.0)))
    assert sample.valid is False
    assert sample.x == 0.0
    assert sample.y == 0.0


def test_status_false_is_invalid():
    sample = gaze_info_to_sample(_info(status=False))
    assert sample.valid is False


def test_invalid_does_not_hold_last_coordinates():
    first = gaze_info_to_sample(_info(timestamp=1, filtered_gaze_coordinates=(50.0, 60.0)))
    assert first.valid is True
    assert (first.x, first.y) == (50.0, 60.0)

    second = gaze_info_to_sample(
        _info(
            timestamp=2,
            status=False,
            filtered_gaze_coordinates=(None, None),
        )
    )
    assert second.valid is False
    assert second.timestamp_ns == 2
    assert (second.x, second.y) == (0.0, 0.0)
    assert (second.x, second.y) != (first.x, first.y)
