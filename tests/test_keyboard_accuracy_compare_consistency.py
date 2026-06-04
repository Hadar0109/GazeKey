"""Tests that live keyboard accuracy and compare replay use the same evaluation recipe."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import pytest
from PySide6.QtCore import QRect

from gazekey.debug.keyboard_accuracy import (
    KeyboardAccuracyEvalSession,
    RecordedKeyFrames,
    evaluate_key_accuracy_from_frames,
    predict_key_accuracy_screen_xy,
)
from gazekey.debug.keyboard_accuracy_compare import (
    evaluate_recorded_frames,
    validate_selected_mapper_matches_debug,
)
from gazekey.features.feature_smoother import PcaFeatureSmoother
from gazekey.features.feature_types import FrameFeatures
from gazekey.layout.layout_inspector import KeyGeometryRow
from gazekey.mapping.base import MapperPrediction


def _fake_key(
    *,
    key_id: str,
    label: str,
    action: str,
    rect: QRect,
    row: int = 0,
    col: int = 0,
    is_special: bool = False,
) -> KeyGeometryRow:
    cx = float(rect.center().x())
    cy = float(rect.center().y())
    return KeyGeometryRow(
        key_id=key_id,
        key_label=label,
        key_action=action,
        row_index=row,
        col_index=col,
        button=None,  # type: ignore[arg-type]
        rect=rect,
        center=(cx, cy),
        hitbox=rect,
        is_special_key=is_special,
        weight=1.0,
    )


def _feat(u_l: float, v_l: float, u_r: float, v_r: float) -> FrameFeatures:
    return FrameFeatures(
        timestamp_ms=0,
        face_detected=True,
        blink=False,
        confidence=1.0,
        Lh=0.5 + u_l,
        Lv=0.5 + v_l,
        Rh=0.5 + u_r,
        Rv=0.5 + v_r,
        avg_h=0.5 + 0.5 * (u_l + u_r),
        avg_v=0.5 + 0.5 * (v_l + v_r),
        eye_box_w=0.04,
        eye_box_h=0.02,
        face_x=0.6,
        face_y=0.55,
        pca_uL=u_l,
        pca_vL=v_l,
        pca_uR=u_r,
        pca_vR=v_r,
    )


@dataclass
class _LinearMapper:
    mapper_type: str
    ox: float
    oy: float
    sx: float
    sy: float

    def predict(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        if features.pca_uL is None or features.pca_vL is None:
            return None
        x = self.ox + self.sx * float(features.pca_uL)
        y = self.oy + self.sy * float(features.pca_vL)
        return MapperPrediction(x=x, y=y, quality=1.0)


def test_evaluate_recorded_frames_matches_live_session_recipe():
    keys = [
        _fake_key(key_id="q", label="q", action="q", rect=QRect(0, 0, 100, 100)),
        _fake_key(key_id="bksp", label="⌫", action="BACKSPACE", rect=QRect(900, 250, 200, 80), is_special=True),
    ]
    target = keys[0]
    frames = (
        _feat(0.0, 0.0, 0.0, 0.0),
        _feat(0.1, 0.0, 0.1, 0.0),
        _feat(0.2, 0.0, 0.2, 0.0),
    )
    model = _LinearMapper(mapper_type="test_linear", ox=50.0, oy=50.0, sx=100.0, sy=0.0)
    smoother = PcaFeatureSmoother(alpha=0.28)
    resets: List[int] = []

    def on_reset() -> None:
        smoother.reset()
        resets.append(1)

    def predict(raw: FrameFeatures) -> Optional[Tuple[float, float]]:
        return predict_key_accuracy_screen_xy(
            raw,
            model=model,
            feature_smoother=smoother,
        )

    session = KeyboardAccuracyEvalSession(
        [("Q", target)],
        keys_for_hit_test=keys,
        predict_screen_xy=predict,
        on_collect_begin=on_reset,
        settle_ms=0,
        collect_ms=100,
    )
    session.begin(0)
    assert session.tick(1) is None
    assert session.tick(2, features=frames[0]) is None
    assert session.tick(3, features=frames[1]) is None
    live_row = session.tick(120, features=frames[2])
    assert live_row is not None
    assert len(resets) >= 2

    recorded = [RecordedKeyFrames(target_label="Q", target=target, frames=frames)]
    replay_rows = evaluate_recorded_frames(recorded=recorded, keys=keys, model=model)
    assert len(replay_rows) == 1
    replay = replay_rows[0]

    assert live_row.predicted_x == pytest.approx(replay.predicted_x)
    assert live_row.predicted_y == pytest.approx(replay.predicted_y)
    assert live_row.predicted_key == replay.predicted_key
    assert live_row.is_correct == replay.is_correct


def test_validate_selected_mapper_matches_debug():
    keys = [_fake_key(key_id="q", label="q", action="q", rect=QRect(0, 0, 100, 100))]
    target = keys[0]
    frames = (_feat(0.1, 0.0, 0.1, 0.0), _feat(0.2, 0.0, 0.2, 0.0))
    model = _LinearMapper(mapper_type="selected_mapper", ox=40.0, oy=40.0, sx=100.0, sy=0.0)
    smoother = PcaFeatureSmoother(alpha=0.28)

    def predict(raw: FrameFeatures) -> Optional[Tuple[float, float]]:
        return predict_key_accuracy_screen_xy(
            raw,
            model=model,
            feature_smoother=smoother,
        )

    smoother.reset()
    debug_row = evaluate_key_accuracy_from_frames(
        target_label="Q",
        target=target,
        frames=frames,
        keys=keys,
        predict_screen_xy=predict,
    )
    compare_rows = evaluate_recorded_frames(
        recorded=[RecordedKeyFrames("Q", target, frames)],
        keys=keys,
        model=model,
    )
    validate_selected_mapper_matches_debug(
        [debug_row],
        [("selected_mapper", compare_rows)],
        "selected_mapper",
    )


def test_full_keyboard_hit_test_uses_special_keys():
    """Points over backspace must not be re-scored as nearest letter."""
    keys = [
        _fake_key(key_id="p", label="p", action="p", rect=QRect(1100, 100, 100, 60)),
        _fake_key(key_id="bksp", label="⌫", action="BACKSPACE", rect=QRect(1040, 260, 200, 70), is_special=True),
    ]
    target = keys[0]
    frames = (_feat(0.0, 0.0, 0.0, 0.0),)
    model = _LinearMapper(mapper_type="edge", ox=1272.0, oy=337.0, sx=0.0, sy=0.0)

    row = evaluate_recorded_frames(
        recorded=[RecordedKeyFrames("P", target, frames)],
        keys=keys,
        model=model,
    )[0]
    assert row.predicted_key != "P"
