"""Outlier detection must not flag horizontal v-coupling on the same row."""

from __future__ import annotations

from gazekey.calibration2.outliers import check_target_mean_outlier
from gazekey.calibration2.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures


def _feat(u: float, v: float) -> FrameFeatures:
    return FrameFeatures(
        timestamp_ms=0,
        face_detected=True,
        blink=False,
        confidence=1.0,
        Lh=0.5,
        Lv=0.5,
        Rh=0.5,
        Rv=0.5,
        avg_h=0.5,
        avg_v=0.5 + v,
        eye_box_w=0.04,
        eye_box_h=0.02,
        face_x=0.5,
        face_y=0.5,
        pca_uL=u,
        pca_vL=v,
        pca_uR=u,
        pca_vR=v,
    )


def test_row_coupling_not_flagged_as_outlier():
    targets = [
        CalibrationTarget("T01", "bottom_left", "", 0, 639),
        CalibrationTarget("T02", "bottom", "", 100, 639),
        CalibrationTarget("T03", "bottom_right", "", 200, 639),
    ]
    # Coupled v decreases as u increases (same row, different x).
    feats = [_feat(-0.3, 0.19), _feat(0.0, 0.09), _feat(0.3, 0.07)]
    for i in range(3):
        msg = check_target_mean_outlier(
            idx=i,
            feature=feats[i],
            targets=targets,
            peer_features=feats,
        )
        assert msg is None, f"unexpected outlier for coupled row: {msg}"
