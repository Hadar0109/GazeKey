"""T040 / T039: GazeSample → MappedGazePoint → hit-test never uses the legacy estimator."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock

from gazekey.backend.gaze_sample import GazeSample
from gazekey.typing.gaze_typing_runtime import MappedGazePoint
from gazekey.typing.key_hit_tester import hit_test_layout_keys
from gazekey.ui.virtual_keyboard import VirtualKeyboard

_REPO = Path(__file__).resolve().parents[2]
_FORBIDDEN = (
    "FeatureExtractor",
    "Pca4BaselineMapper",
    "Ridge",
    "MapperRuntime",
    "key_accuracy_predict_screen_xy",
    "GazeSmoother",
    "PcaFeatureSmoother",
    "filter_or_reject",
    "pca_vL",
    "pca_vR",
)


def _fn_source(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(path.read_text(encoding="utf-8"), node) or ""
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                    return ast.get_source_segment(path.read_text(encoding="utf-8"), child) or ""
    raise AssertionError(f"{name} not found in {path}")


def test_from_gaze_sample_and_on_gaze_sample_omit_legacy_tokens():
    mapped = _fn_source(
        _REPO / "gazekey/typing/gaze_typing_runtime.py", "from_gaze_sample"
    )
    loop = _fn_source(_REPO / "gazekey/runtime/gaze_loop.py", "on_gaze_sample")
    offenders: list[str] = []
    for label, src in (("from_gaze_sample", mapped), ("on_gaze_sample", loop)):
        for token in _FORBIDDEN:
            if token in src:
                offenders.append(f"{label}: {token}")
    assert offenders == []


def test_gazesample_mapped_point_hit_test_does_not_call_mapper(qapp, monkeypatch):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    vk._keyboard_layout_builder.export_keyboard_layout()
    vk._official_gaze_ready = True
    vk._ensure_typing_auto_started()
    monkeypatch.setattr(
        "gazekey.features.FeatureExtractor.from_eye_data",
        MagicMock(side_effect=AssertionError("FeatureExtractor")),
    )
    monkeypatch.setattr(
        vk._mapper_runtime,
        "key_accuracy_predict_screen_xy",
        MagicMock(side_effect=AssertionError("MapperRuntime.predict")),
    )
    monkeypatch.setattr(vk._gaze_smoother, "filter_or_reject", MagicMock())
    sample = GazeSample(
        timestamp_ns=1,
        valid=True,
        x=50.0,
        y=60.0,
        calibrated_x=50.0,
        calibrated_y=60.0,
        tracking_state="SUCCESS",
        left_openness=20.0,
        right_openness=21.0,
    )
    gaze = MappedGazePoint.from_gaze_sample(sample)
    assert gaze.valid is True
    assert (gaze.x, gaze.y) == (50.0, 60.0)
    hit_test_layout_keys(vk._layout_keys, gaze.x, gaze.y)
    vk._gaze_loop.on_gaze_sample(sample)
    vk._gaze_smoother.filter_or_reject.assert_not_called()


def test_invalid_sample_maps_to_zero_xy_not_hold_last():
    invalid = GazeSample(
        timestamp_ns=2,
        valid=False,
        x=999.0,
        y=999.0,
        calibrated_x=None,
        calibrated_y=None,
        tracking_state="FACE_MISSING",
        left_openness=0.0,
        right_openness=0.0,
    )
    gaze = MappedGazePoint.from_gaze_sample(invalid)
    assert gaze == MappedGazePoint(x=0.0, y=0.0, valid=False)
