"""Tests for keyboard accuracy mapper stage diagnostics."""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
from PySide6.QtCore import QRect

from gazekey.calibration2.targets import CalibrationTarget
from gazekey.debug.keyboard_accuracy import RecordedKeyFrames
from gazekey.debug.keyboard_accuracy_mapper_diag import (
    diagnose_recorded_keys,
    rank_calibration_anchors,
    trace_mapper_frame,
    unwrap_mapper_stack,
)
from gazekey.features.feature_smoother import PcaFeatureSmoother
from gazekey.features.feature_types import FrameFeatures
from gazekey.layout.layout_inspector import KeyGeometryRow
from gazekey.mapping.local_y_correction import MapperWithLocalYCorrection
from gazekey.mapping.ridge import Pca4BaselineMapper
from gazekey.mapping.row_bias import attach_row_y_bias


def _feat(
    *,
    u_l: float = 0.0,
    v_l: float = 0.0,
    u_r: float = 0.0,
    v_r: float = 0.0,
) -> FrameFeatures:
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
        avg_v=0.5 + 0.5 * (v_l + v_r),
        eye_box_w=0.04,
        eye_box_h=0.02,
        face_x=0.5,
        face_y=0.6,
        pca_uL=u_l,
        pca_vL=v_l,
        pca_uR=u_r,
        pca_vR=v_r,
    )


def _fake_key(label: str, action: str, rect: QRect) -> KeyGeometryRow:
    cx = float(rect.center().x())
    cy = float(rect.center().y())
    return KeyGeometryRow(
        key_id=action,
        key_label=label,
        key_action=action,
        row_index=0,
        col_index=0,
        button=None,  # type: ignore[arg-type]
        rect=rect,
        center=(cx, cy),
        hitbox=rect,
        is_special_key=False,
        weight=1.0,
    )


def _minimal_pca4_mapper(*, clip_bounds=None) -> Pca4BaselineMapper:
    n = 3
    Y = np.array([[100.0, 200.0], [200.0, 200.0], [300.0, 300.0]], dtype=np.float64)
    u_l = np.array([0.0, 0.5, 1.0], dtype=np.float64)
    u_r = np.array([0.0, 0.5, 1.0], dtype=np.float64)
    v_l = np.array([0.0, 0.0, 0.5], dtype=np.float64)
    v_r = np.array([0.0, 0.0, 0.5], dtype=np.float64)
    return Pca4BaselineMapper(
        w_x=np.array([100.0, 0.0], dtype=np.float64),
        b_x=100.0,
        mu_x=np.zeros(2, dtype=np.float64),
        sigma_x=np.ones(2, dtype=np.float64),
        w_y=np.array([100.0, 0.0], dtype=np.float64),
        b_y=150.0,
        mu_y=np.zeros(2, dtype=np.float64),
        sigma_y=np.ones(2, dtype=np.float64),
        alpha=1.0,
        train_u_l=u_l,
        train_u_r=u_r,
        train_v_l=v_l,
        train_v_r=v_r,
        train_Y=Y,
        clip_bounds=clip_bounds,
    )


def test_unwrap_mapper_stack_order():
    core = _minimal_pca4_mapper()
    wrapped = attach_row_y_bias(
        core,
        row_y_centers=(150.0, 220.0, 290.0),
        row_y_bias=(10.0, 0.0, -5.0),
    )
    wrapped = MapperWithLocalYCorrection(
        inner=wrapped,
        train_x=np.array([100.0, 200.0, 300.0], dtype=np.float64),
        train_dy=np.array([5.0, 0.0, -8.0], dtype=np.float64),
    )
    stack = unwrap_mapper_stack(wrapped)
    assert isinstance(stack.core, Pca4BaselineMapper)
    assert stack.row_bias is not None
    assert stack.local_y is not None


def test_trace_mapper_frame_applies_row_local_and_clamp():
    core = _minimal_pca4_mapper(clip_bounds=(0.0, 120.0, 500.0, 400.0))
    model = attach_row_y_bias(
        core,
        row_y_centers=(150.0, 220.0, 290.0),
        row_y_bias=(20.0, 0.0, 0.0),
    )
    model = MapperWithLocalYCorrection(
        inner=model,
        train_x=np.array([100.0, 200.0, 300.0], dtype=np.float64),
        train_dy=np.array([10.0, 0.0, 0.0], dtype=np.float64),
    )
    stack = unwrap_mapper_stack(model)
    smoother = PcaFeatureSmoother(alpha=0.28)
    # v_l=v_r=0 -> core_y_raw=150; row top bias 20 -> 130; local dy at x=100 is 10 -> 120
    trace = trace_mapper_frame(
        _feat(v_l=0.0, v_r=0.0, u_l=0.0, u_r=0.0),
        stack=stack,
        feature_smoother=smoother,
        clamp_xy=lambda x, y: (x, max(120.0, y)),
    )
    assert trace is not None
    assert trace.core_y == 150.0
    assert trace.row_idx == 0
    assert trace.row_bias == 20.0
    assert trace.y_after_row == 130.0
    assert trace.local_dy == 10.0
    assert trace.y_after_local == 120.0
    assert trace.y_final == 120.0


def test_rank_calibration_anchors_orders_by_distance():
    samples: List[Tuple[FrameFeatures, Tuple[float, float]]] = [
        (_feat(u_l=0.0, v_l=0.0, u_r=0.0, v_r=0.0), (100.0, 150.0)),
        (_feat(u_l=1.0, v_l=0.5, u_r=1.0, v_r=0.5), (300.0, 300.0)),
    ]
    targets = [
        CalibrationTarget("T01", "row0_left", "", 100.0, 150.0),
        CalibrationTarget("T02", "row2_right", "", 300.0, 300.0),
    ]
    ranked = rank_calibration_anchors(
        _feat(u_l=0.05, v_l=0.0, u_r=0.0, v_r=0.0),
        calib_samples=samples,
        calib_targets=targets,
    )
    assert ranked[0][2] == "row0_left"
    assert ranked[1][2] == "row2_right"


def test_diagnose_recorded_keys_writes_stage_deltas(tmp_path):
    core = _minimal_pca4_mapper(clip_bounds=(0.0, 100.0, 500.0, 400.0))
    model = attach_row_y_bias(
        core,
        row_y_centers=(150.0, 220.0, 290.0),
        row_y_bias=(0.0, 0.0, 0.0),
    )
    keys = [_fake_key("G", "g", QRect(600, 200, 40, 40))]
    frames = tuple(_feat(u_l=0.5, v_l=0.0, u_r=0.5, v_r=0.0) for _ in range(3))
    recorded = [RecordedKeyFrames(target_label="G", target=keys[0], frames=frames)]
    calib_samples = [(_feat(u_l=0.0, v_l=0.0, u_r=0.0, v_r=0.0), (100.0, 150.0))]
    calib_targets = [CalibrationTarget("T01", "row0_left", "", 100.0, 150.0)]

    stage_rows, anchor_rows = diagnose_recorded_keys(
        recorded=recorded,
        keys=keys,
        model=model,
        calib_samples=calib_samples,
        calib_targets=calib_targets,
    )
    assert len(stage_rows) == 1
    assert stage_rows[0].target_key == "G"
    assert stage_rows[0].core_y == 150.0
    assert len(anchor_rows) == 1
    assert anchor_rows[0].nearest_label == "row0_left"
