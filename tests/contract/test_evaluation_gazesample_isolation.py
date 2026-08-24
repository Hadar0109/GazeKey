"""T051: GazeFollower evaluation scoring does not use FeatureExtractor / Ridge / PCA4."""

from __future__ import annotations

import ast
from pathlib import Path

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QPushButton

from gazekey.backend.gaze_sample import GazeSample
from gazekey.layout.layout_inspector import KeyGeometryRow
from tools.evaluation.gazesample_scoring import (
    evaluate_key_accuracy_from_screen_points,
    screen_points_from_samples,
    write_gaze_replay,
)
from tools.evaluation.run_summary import FEATURE_004_EVAL_BEFORE, GF_EVAL_FIDELITY_NOTES

_REPO = Path(__file__).resolve().parents[2]


def test_gazesample_scoring_source_omits_legacy_estimator_imports():
    src = (_REPO / "tools/evaluation/gazesample_scoring.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    for name in imported:
        assert not name.startswith("gazekey.features")
        assert not name.startswith("gazekey.mapping")
        assert not name.startswith("gazekey.runtime.mapper_runtime")
        assert "extractor" not in name.lower()
        assert "ridge" not in name.lower()


def test_screen_points_from_valid_samples_only():
    samples = [
        GazeSample(1, True, 10.0, 20.0, 10.0, 20.0, "SUCCESS", 20.0, 21.0),
        GazeSample(2, False, 99.0, 99.0, None, None, "FACE_MISSING", 0.0, 0.0),
    ]
    assert screen_points_from_samples(samples) == [(10.0, 20.0)]


def test_evaluate_screen_points_hits_live_qrect(qapp):
    btn = QPushButton()
    target = KeyGeometryRow(
        key_id="key_a",
        key_label="A",
        key_action="a",
        row_index=0,
        col_index=0,
        button=btn,
        rect=QRect(0, 0, 40, 40),
        center=(20.0, 20.0),
        hitbox=QRect(0, 0, 40, 40),
        is_special_key=False,
        weight=1.0,
    )
    row = evaluate_key_accuracy_from_screen_points(
        target_label="A",
        target=target,
        points=[(20.0, 20.0), (21.0, 19.0)],
        keys=[target],
    )
    assert row.inside_tight is True
    assert row.is_correct is True
    assert row.collect_frames == 2


def test_gf_eval_notes_cite_feature_004_as_eval_before_only():
    assert "14938da0bdf0" in FEATURE_004_EVAL_BEFORE
    assert "34fb259ccdfd" in FEATURE_004_EVAL_BEFORE
    assert "689c8a8ce90c" in FEATURE_004_EVAL_BEFORE
    assert "4f665467b260" in FEATURE_004_EVAL_BEFORE
    assert "eval_before only" in FEATURE_004_EVAL_BEFORE
    assert "GazeSample" in GF_EVAL_FIDELITY_NOTES
    assert "HeuristicFilter" in GF_EVAL_FIDELITY_NOTES


def test_write_gaze_replay_omits_webcam_frames(tmp_path):
    samples = [GazeSample(1, True, 1.0, 2.0, 1.0, 2.0, "SUCCESS", 20.0, 21.0)]
    path = write_gaze_replay(samples, path=tmp_path / "sess.gaze_replay.jsonl")
    text = path.read_text(encoding="utf-8")
    assert "webcam" not in text.lower()
    assert "frame" not in text.lower()
    assert '"x": 1.0' in text
