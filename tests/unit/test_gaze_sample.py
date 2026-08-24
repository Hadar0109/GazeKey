"""T014: GazeSample validity rules (all five required for valid=True)."""

from __future__ import annotations

from types import SimpleNamespace

from gazekey.backend.adapter import gaze_info_to_sample
from gazekey.backend.gaze_sample import GazeSample
from gazekey.backend.geometry import GeometryConfig


def _info(**overrides) -> SimpleNamespace:
    data = dict(
        timestamp=1_000,
        status=True,
        tracking_state=SimpleNamespace(name="SUCCESS"),
        filtered_gaze_coordinates=(100.0, 200.0),
        calibrated_gaze_coordinates=(101.0, 201.0),
        left_openness=40.0,
        right_openness=41.0,
        features=[9.9, 8.8],
        raw_gaze_coordinates=(0.1, 0.2),
        event="UNKNOWN",
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def test_valid_true_requires_all_five_rules():
    sample = gaze_info_to_sample(_info())
    assert sample.valid is True
    assert sample.x == 100.0
    assert sample.y == 200.0
    assert sample.calibrated_x == 101.0
    assert sample.calibrated_y == 201.0
    assert sample.tracking_state == "SUCCESS"
    assert sample.left_openness == 40.0
    assert sample.right_openness == 41.0
    assert sample.timestamp_ns == 1_000
    assert not hasattr(sample, "features")
    assert "features" not in GazeSample.__dataclass_fields__


def test_identity_geometry_keeps_filtered_xy():
    sample = gaze_info_to_sample(_info(), GeometryConfig(transform="identity"))
    assert (sample.x, sample.y) == (100.0, 200.0)


def test_origin_and_dpr_transform():
    geom = GeometryConfig(transform="origin+dpr", origin_offset=(10.0, 20.0), dpr=2.0)
    sample = gaze_info_to_sample(_info(), geom)
    assert sample.x == 10.0 + 100.0 / 2.0
    assert sample.y == 20.0 + 200.0 / 2.0
