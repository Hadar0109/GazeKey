"""Tests for X-interpolated Y residual correction (dormant; APPLY_LOCAL_Y_CORRECTION=False).

Archived offline test. Run manually:

    python -m pytest archive/tests/test_local_y_correction.py -q
"""

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.local_y_correction import (
    MapperWithLocalYCorrection,
    attach_local_y_correction,
    interpolate_y_residual,
)


class _StubMapper:
    mapper_type = "stub"
    alpha = 1.0
    clip_bounds = None

    def __init__(self, y_by_x: dict[float, float]) -> None:
        self._y_by_x = y_by_x

    def predict(self, features: FrameFeatures):
        from gazekey.mapping.base import MapperPrediction

        u = float(features.pca_uL or 0.0)
        x = u * 100.0
        y = float(self._y_by_x.get(round(u, 2), 200.0))
        return MapperPrediction(x=x, y=y, quality=1.0)


def test_interpolate_y_residual_endpoints():
    x = np.array([0.0, 100.0, 200.0])
    dy = np.array([10.0, 0.0, -10.0])
    assert interpolate_y_residual(100.0, x, dy) == 0.0
    assert interpolate_y_residual(-10.0, x, dy) == 10.0
    assert interpolate_y_residual(210.0, x, dy) == -10.0


def test_attach_local_y_correction_reduces_row_tilt():
    """Same target Y at different X should get similar corrected Y."""
    samples = []
    for u, ty in ((0.2, 300.0), (0.5, 300.0), (0.8, 300.0)):
        feat = FrameFeatures(
            timestamp_ms=0,
            face_detected=True,
            blink=False,
            confidence=1.0,
            Lh=u,
            Lv=0.5,
            Rh=u,
            Rv=0.5,
            avg_h=u,
            avg_v=0.5,
            eye_box_w=0.2,
            eye_box_h=0.1,
            face_x=0.5,
            face_y=0.5,
            pca_uL=u,
            pca_vL=0.5,
            pca_uR=u,
            pca_vR=0.5,
        )
        samples.append((feat, (u * 100.0, ty)))

    inner = _StubMapper({0.2: 320.0, 0.5: 300.0, 0.8: 280.0})
    wrapped = attach_local_y_correction(inner, samples=samples, verbose=False)
    ys = []
    for feat, _ in samples:
        pred = wrapped.predict(feat)
        assert pred is not None
        ys.append(pred.y)
    assert max(ys) - min(ys) < 5.0
