"""Read-only calibration coverage diagnostic (T032).

Given the calibration anchor points and the centers of every interactive key on the FULL
keyboard, report which keys fall inside the convex hull of the calibration anchors, which
fall outside (extrapolation risk), and the distance from each key to its nearest anchor.

This is a pure reporting artifact: it never changes mapping behavior. It is written at
calibration finish (calibration-data only, matching the real calibrate-only flow) so a
layout's coverage of the interactive surface can be compared across candidates.
"""

from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Optional, Sequence, Tuple

Point = Tuple[float, float]

SCHEMA_VERSION = 1


def _convex_hull(points: Sequence[Point]) -> List[Point]:
    """Andrew's monotone chain. Returns hull vertices counter-clockwise (no repeat)."""
    pts = sorted(set((float(x), float(y)) for x, y in points))
    if len(pts) <= 2:
        return list(pts)

    def cross(o: Point, a: Point, b: Point) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: List[Point] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: List[Point] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _point_in_hull(pt: Point, hull: Sequence[Point]) -> bool:
    """Inside-or-on test for a convex polygon (CCW). Degenerate hulls return False."""
    n = len(hull)
    if n < 3:
        return False
    x, y = pt
    sign = 0
    for i in range(n):
        ax, ay = hull[i]
        bx, by = hull[(i + 1) % n]
        cross = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        if cross < -1e-9:
            cur = -1
        elif cross > 1e-9:
            cur = 1
        else:
            continue  # on edge
        if sign == 0:
            sign = cur
        elif cur != sign:
            return False
    return True


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _nearest_anchor_px(pt: Point, anchors: Sequence[Point]) -> float:
    if not anchors:
        return float("nan")
    return min(_dist(pt, a) for a in anchors)


def _bbox(points: Sequence[Point]) -> Optional[Dict[str, float]]:
    if not points:
        return None
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return {
        "x_min": min(xs),
        "x_max": max(xs),
        "y_min": min(ys),
        "y_max": max(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
    }


def _coverage_block(keys: Sequence[Dict]) -> Dict:
    total = len(keys)
    inside = sum(1 for k in keys if k["inside_hull"])
    dists = [k["nearest_anchor_px"] for k in keys if not math.isnan(k["nearest_anchor_px"])]
    return {
        "n_keys": total,
        "n_inside_hull": inside,
        "n_outside_hull": total - inside,
        "inside_fraction": (inside / total) if total else 0.0,
        "outside_keys": [k["key_label"] for k in keys if not k["inside_hull"]],
        "max_nearest_anchor_px": max(dists) if dists else 0.0,
        "mean_nearest_anchor_px": (sum(dists) / len(dists)) if dists else 0.0,
    }


def build_coverage_report(
    *,
    anchors: Sequence[Point],
    keys: Sequence[Dict],
    calibration_mode: str = "",
    session_id: str = "",
) -> Dict:
    """Assemble the coverage report.

    ``keys`` is a list of dicts with at least: ``key_label`` (str), ``x`` (float),
    ``y`` (float), ``row_index`` (int), ``is_special`` (bool).
    """
    anchor_pts: List[Point] = [(float(x), float(y)) for x, y in anchors]
    hull = _convex_hull(anchor_pts)

    key_rows: List[Dict] = []
    for k in keys:
        pt = (float(k["x"]), float(k["y"]))
        inside = _point_in_hull(pt, hull)
        key_rows.append(
            {
                "key_label": str(k.get("key_label", "")),
                "key_action": str(k.get("key_action", "")),
                "x": pt[0],
                "y": pt[1],
                "row_index": int(k.get("row_index", -1)),
                "is_special": bool(k.get("is_special", False)),
                "inside_hull": inside,
                "nearest_anchor_px": _nearest_anchor_px(pt, anchor_pts),
            }
        )

    by_row: Dict[str, Dict] = {}
    rows = sorted({k["row_index"] for k in key_rows})
    for ri in rows:
        by_row[str(ri)] = _coverage_block([k for k in key_rows if k["row_index"] == ri])

    letter_keys = [k for k in key_rows if not k["is_special"]]
    special_keys = [k for k in key_rows if k["is_special"]]

    return {
        "schema_version": SCHEMA_VERSION,
        "run_type": "calibration_coverage",
        "session_id": str(session_id),
        "calibration_mode": str(calibration_mode),
        "n_anchors": len(anchor_pts),
        "anchor_bbox": _bbox(anchor_pts),
        "key_bbox": _bbox([(k["x"], k["y"]) for k in key_rows]),
        "hull_vertices": [[round(x, 3), round(y, 3)] for x, y in hull],
        "overall": _coverage_block(key_rows),
        "letters": _coverage_block(letter_keys),
        "specials": _coverage_block(special_keys),
        "by_row": by_row,
        "keys": key_rows,
    }


def coverage_path(session_id: str, runs_dir: str = "runs") -> str:
    safe = "".join(c for c in str(session_id) if c.isalnum() or c in ("-", "_")) or "session"
    return os.path.join(runs_dir, f"coverage_{safe}.json")


def write_coverage_diagnostics(
    report: Dict,
    *,
    session_id: str,
    runs_dir: str = "runs",
) -> str:
    os.makedirs(runs_dir, exist_ok=True)
    path = coverage_path(session_id, runs_dir=runs_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return path
