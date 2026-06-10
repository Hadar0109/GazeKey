"""T032 Iteration 4: read-only calibration coverage diagnostic."""

from __future__ import annotations

import json
import math

from gazekey.evaluation.coverage_diagnostics import (
    build_coverage_report,
    coverage_path,
    write_coverage_diagnostics,
)


def _square_anchors():
    return [(0.0, 0.0), (100.0, 0.0), (0.0, 100.0), (100.0, 100.0)]


def _keys():
    return [
        {"key_label": "IN", "key_action": "i", "x": 50.0, "y": 50.0, "row_index": 0, "is_special": False},
        {"key_label": "EDGE", "key_action": "e", "x": 0.0, "y": 0.0, "row_index": 0, "is_special": False},
        {"key_label": "OUT", "key_action": "o", "x": 200.0, "y": 50.0, "row_index": 1, "is_special": True},
    ]


def test_inside_outside_classification_and_counts():
    report = build_coverage_report(anchors=_square_anchors(), keys=_keys(), calibration_mode="keyboard_full9")

    by_label = {k["key_label"]: k for k in report["keys"]}
    assert by_label["IN"]["inside_hull"] is True
    assert by_label["EDGE"]["inside_hull"] is True  # on the hull boundary counts as inside
    assert by_label["OUT"]["inside_hull"] is False

    overall = report["overall"]
    assert overall["n_keys"] == 3
    assert overall["n_inside_hull"] == 2
    assert overall["n_outside_hull"] == 1
    assert "OUT" in overall["outside_keys"]
    assert math.isclose(overall["inside_fraction"], 2.0 / 3.0, rel_tol=1e-6)


def test_nearest_anchor_distance():
    report = build_coverage_report(anchors=_square_anchors(), keys=_keys())
    by_label = {k["key_label"]: k for k in report["keys"]}
    # Center key is sqrt(50^2 + 50^2) from each corner.
    assert math.isclose(by_label["IN"]["nearest_anchor_px"], math.hypot(50.0, 50.0), rel_tol=1e-6)
    # Outside key nearest corner is (100, 0) -> distance 100*?: dx=100, dy=50
    assert math.isclose(by_label["OUT"]["nearest_anchor_px"], math.hypot(100.0, 50.0), rel_tol=1e-6)


def test_letters_and_specials_split():
    report = build_coverage_report(anchors=_square_anchors(), keys=_keys())
    assert report["letters"]["n_keys"] == 2
    assert report["specials"]["n_keys"] == 1
    assert report["by_row"]["0"]["n_keys"] == 2
    assert report["by_row"]["1"]["n_keys"] == 1


def test_bboxes_present():
    report = build_coverage_report(anchors=_square_anchors(), keys=_keys())
    assert report["anchor_bbox"]["width"] == 100.0
    assert report["key_bbox"]["x_max"] == 200.0
    assert report["n_anchors"] == 4
    assert len(report["hull_vertices"]) >= 3


def test_degenerate_anchors_do_not_crash():
    # Collinear anchors -> no area hull; everything reported outside, no exception.
    report = build_coverage_report(anchors=[(0.0, 0.0), (10.0, 0.0)], keys=_keys())
    assert report["overall"]["n_inside_hull"] == 0
    assert report["overall"]["n_outside_hull"] == 3


def test_write_and_roundtrip(tmp_path):
    report = build_coverage_report(
        anchors=_square_anchors(), keys=_keys(), session_id="sess123", calibration_mode="keyboard_wide9"
    )
    path = write_coverage_diagnostics(report, session_id="sess123", runs_dir=str(tmp_path))
    assert path == coverage_path("sess123", runs_dir=str(tmp_path))

    with open(path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["session_id"] == "sess123"
    assert loaded["calibration_mode"] == "keyboard_wide9"
    assert loaded["overall"]["n_keys"] == 3
