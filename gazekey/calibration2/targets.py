"""Keyboard-local calibration target generation (9 default, 13 optional)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PySide6.QtCore import QRect

from gazekey.layout.layout_inspector import KeyGeometryRow


@dataclass(frozen=True)
class CalibrationTarget:
    target_id: str  # "T01"...
    label: str
    key_id: str  # from keyboard_layout.csv when applicable; else ""
    screen_x: float
    screen_y: float
    # Optional 3xN grid indices for region gates (row 0=top .. 2=bottom).
    grid_row: int = -1
    grid_col: int = -1


def calibration_row_groups(
    targets: Sequence[CalibrationTarget],
) -> Tuple[List[int], List[int], List[int]]:
    """Return target indices for top / middle / bottom rows (9-point or grid labels)."""
    top: List[int] = []
    mid: List[int] = []
    bot: List[int] = []
    for i, t in enumerate(targets):
        if t.grid_row >= 0:
            if t.grid_row == 0:
                top.append(i)
            elif t.grid_row == 2:
                bot.append(i)
            else:
                mid.append(i)
            continue
        lab = str(t.label).lower()
        if "top" in lab or lab.startswith("row0"):
            top.append(i)
        elif "bottom" in lab or lab.startswith("row2"):
            bot.append(i)
        elif lab in {"left", "center", "right"} or "middle" in lab or lab.startswith("row1"):
            mid.append(i)
    return top, mid, bot


def _grid_points(rect: QRect, rows: int, cols: int, margin_ratio: float) -> List[Tuple[float, float]]:
    mx = rect.width() * margin_ratio
    my = rect.height() * margin_ratio
    x0 = rect.x() + mx
    x1 = rect.x() + rect.width() - mx
    y0 = rect.y() + my
    y1 = rect.y() + rect.height() - my

    if cols == 1:
        xs = [(x0 + x1) / 2.0]
    else:
        xs = [x0 + (x1 - x0) * (c / (cols - 1)) for c in range(cols)]
    if rows == 1:
        ys = [(y0 + y1) / 2.0]
    else:
        ys = [y0 + (y1 - y0) * (r / (rows - 1)) for r in range(rows)]
    return [(x, y) for y in ys for x in xs]  # row-major


def _pick_key_at_x_fraction(
    row_keys: List[KeyGeometryRow],
    frac: float,
) -> KeyGeometryRow:
    """Pick the letter key whose center X is nearest to frac along the row span."""
    xs = [float(k.center[0]) for k in row_keys]
    x0, x1 = min(xs), max(xs)
    if abs(x1 - x0) < 1e-3:
        return row_keys[0]
    target_x = x0 + float(frac) * (x1 - x0)
    return min(row_keys, key=lambda k: abs(float(k.center[0]) - target_x))


def _letter_keys_by_row(
    keys: Iterable[KeyGeometryRow],
) -> List[Tuple[int, List[KeyGeometryRow]]]:
    """Return [(row_index, keys)] for single-character letter keys, top to bottom."""
    letter = [k for k in keys if not k.is_special_key and len(k.key_action) == 1]
    if not letter:
        letter = [k for k in keys if not k.is_special_key]
    rows: dict[int, List[KeyGeometryRow]] = {}
    for k in letter:
        rows.setdefault(int(k.row_index), []).append(k)
    out = [(ri, sorted(rs, key=lambda k: k.center[0])) for ri, rs in sorted(rows.items())]
    return out


def _all_keys_by_row(
    keys: Iterable[KeyGeometryRow],
) -> List[Tuple[int, List[KeyGeometryRow]]]:
    """Return [(row_index, keys)] for ALL gaze-hittable keys (incl. specials), top to bottom.

    Unlike :func:`_letter_keys_by_row`, this keeps Shift/Ctrl/Alt/Space/Enter/Backspace so
    the full interactive keyboard bounding box (true left/right edges + Space/Enter row) is
    available for whole-keyboard coverage layouts.
    """
    rows: dict[int, List[KeyGeometryRow]] = {}
    for k in keys:
        rows.setdefault(int(k.row_index), []).append(k)
    ordered = sorted(
        rows.items(),
        key=lambda kv: float(np.mean([kk.center[1] for kk in kv[1]])),
    )
    return [(ri, sorted(rs, key=lambda k: k.center[0])) for ri, rs in ordered]


def _keyboard_full_coverage_targets(
    keys: Sequence[KeyGeometryRow],
) -> List[CalibrationTarget]:
    """Candidate A: ~9 anchors spanning the FULL interactive keyboard via real key centers.

    Three vertical bands (top interactive row, a middle row, the bottom Ctrl/Space/Enter
    row) x three columns (true leftmost / center / rightmost key per band). Anchors snap to
    real key centers so they remain stable fixation targets, and they reach the true
    left/right edges and the bottom row that ``keyboard15`` never covers.

    Bands are tagged grid_row 0/1/2 so :func:`calibration_row_groups` still yields three
    groups; the only change versus the letter-only layout is that the three row-Y centers
    now span the whole keyboard vertically (a layout effect, not a mapping-logic change).
    """
    rows = _all_keys_by_row(keys)
    n = len(rows)
    if n < 3:
        return []  # caller falls back to the standard letter layout

    # rows is already ordered top->bottom by mean center-y. Pick top, bottom, and the
    # interior row whose mean y is closest to the vertical midpoint (best 3-band spread;
    # avoids bunching two bands near the bottom when there are 4+ rows).
    def _row_mean_y(row: Tuple[int, List[KeyGeometryRow]]) -> float:
        return float(np.mean([k.center[1] for k in row[1]]))

    top_row = rows[0]
    bottom_row = rows[n - 1]
    mid_y = 0.5 * (_row_mean_y(top_row) + _row_mean_y(bottom_row))
    interior = rows[1:-1]
    mid_row = min(interior, key=lambda r: abs(_row_mean_y(r) - mid_y))
    band_rows = [top_row, mid_row, bottom_row]
    band_labels = ("top", "mid", "bottom")
    col_labels = ("left", "center", "right")

    out: List[CalibrationTarget] = []
    tid = 1
    for grid_row, (_phys_row, row_keys) in enumerate(band_rows):
        left = row_keys[0]
        right = row_keys[-1]
        center = row_keys[len(row_keys) // 2]
        for grid_col, k in enumerate((left, center, right)):
            cx, cy = k.center
            out.append(
                CalibrationTarget(
                    target_id=f"T{tid:02d}",
                    label=f"full_{band_labels[grid_row]}_{col_labels[grid_col]}",
                    key_id=str(k.key_id),
                    screen_x=float(cx),
                    screen_y=float(cy),
                    grid_row=int(grid_row),
                    grid_col=int(grid_col),
                )
            )
            tid += 1
    return out


def _keyboard_wide_targets(
    typing_region_rect: QRect,
    screen_rect: Optional[QRect],
    *,
    expand_frac: float = 0.6,
    screen_inset_frac: float = 0.04,
) -> List[CalibrationTarget]:
    """Candidate B: ~9 anchors on a 3x3 grid pushed WIDER than the keyboard toward the screen.

    The keyboard rect is grown by ``expand_frac`` of its size on each side, then clamped to
    the screen (minus ``screen_inset_frac`` so dots stay on-screen). Anchors are off-keyboard
    points (no key_id). Hypothesis: a wider, better-conditioned gaze range improves the
    PCA4->screen linear fit, with the keyboard becoming an interpolated interior region.
    """
    r = typing_region_rect
    ex = float(r.width()) * float(expand_frac)
    ey = float(r.height()) * float(expand_frac)
    x0 = float(r.x()) - ex
    x1 = float(r.x() + r.width()) + ex
    y0 = float(r.y()) - ey
    y1 = float(r.y() + r.height()) + ey

    if screen_rect is not None and screen_rect.width() > 0 and screen_rect.height() > 0:
        sx0 = float(screen_rect.x()) + float(screen_rect.width()) * screen_inset_frac
        sx1 = float(screen_rect.x() + screen_rect.width()) - float(screen_rect.width()) * screen_inset_frac
        sy0 = float(screen_rect.y()) + float(screen_rect.height()) * screen_inset_frac
        sy1 = float(screen_rect.y() + screen_rect.height()) - float(screen_rect.height()) * screen_inset_frac
        x0 = max(x0, sx0)
        x1 = min(x1, sx1)
        y0 = max(y0, sy0)
        y1 = min(y1, sy1)

    xs = [x0, 0.5 * (x0 + x1), x1]
    ys = [y0, 0.5 * (y0 + y1), y1]
    col_labels = ("left", "center", "right")
    row_labels = ("top", "mid", "bottom")

    out: List[CalibrationTarget] = []
    tid = 1
    for grid_row, y in enumerate(ys):
        for grid_col, x in enumerate(xs):
            out.append(
                CalibrationTarget(
                    target_id=f"T{tid:02d}",
                    label=f"wide_{row_labels[grid_row]}_{col_labels[grid_col]}",
                    key_id="",
                    screen_x=float(x),
                    screen_y=float(y),
                    grid_row=int(grid_row),
                    grid_col=int(grid_col),
                )
            )
            tid += 1
    return out


def keyboard_geometry_targets(
    *,
    keys: Sequence[KeyGeometryRow],
    typing_region_rect: QRect,
    mode: str = "keyboard15",
    screen_rect: Optional[QRect] = None,
) -> List[CalibrationTarget]:
    """
    Dense calibration targets aligned to real key centers inside the letter-key area.

    - keyboard15: 3 letter rows × 3 columns + 3 row-gap + 3 interior = 15
    - keyboard13: same without 2 interior anchors = 13
    - keyboard_full9: ~9 anchors across the FULL interactive keyboard (Candidate A, T032)
    - keyboard_wide9: ~9 anchors on a grid wider than the keyboard (Candidate B, T032)

    All ``keyboard*`` modes keep the same mapper treatment downstream (keyboard_mode=True);
    the only difference is anchor placement/count (the single Iteration-4 lever).
    """
    if mode == "keyboard_full9":
        full = _keyboard_full_coverage_targets(list(keys))
        if len(full) >= 9:
            return full
        mode = "keyboard15"  # too few rows detected; fall back to standard layout
    elif mode == "keyboard_wide9":
        return _keyboard_wide_targets(typing_region_rect, screen_rect)

    if mode not in {"keyboard15", "keyboard13"}:
        raise ValueError(f"Unknown keyboard geometry mode: {mode}")

    rows = _letter_keys_by_row(keys)
    if len(rows) < 2:
        return keyboard_local_targets(
            typing_region_rect=typing_region_rect,
            mode="precision13" if mode == "keyboard15" else "default9",
        )

    # Use the top three letter rows (typically Q, A, Z rows).
    if len(rows) > 3:
        rows = rows[:3]
    col_fracs = (0.08, 0.5, 0.92)
    col_labels = ("left", "center", "right")

    out: List[CalibrationTarget] = []
    tid = 1
    for grid_row, (_phys_row, row_keys) in enumerate(rows):
        for grid_col, frac in enumerate(col_fracs):
            k = _pick_key_at_x_fraction(row_keys, frac)
            cx, cy = k.center
            out.append(
                CalibrationTarget(
                    target_id=f"T{tid:02d}",
                    label=f"row{grid_row}_{col_labels[grid_col]}",
                    key_id=str(k.key_id),
                    screen_x=float(cx),
                    screen_y=float(cy),
                    grid_row=int(grid_row),
                    grid_col=int(grid_col),
                )
            )
            tid += 1

    # Row-gap targets between consecutive letter rows (center X of keyboard).
    r = typing_region_rect
    mid_x = float(r.x() + r.width() / 2.0)
    for gi in range(len(rows) - 1):
        y_a = float(np.mean([k.center[1] for k in rows[gi][1]]))
        y_b = float(np.mean([k.center[1] for k in rows[gi + 1][1]]))
        gap_y = 0.5 * (y_a + y_b)
        out.append(
            CalibrationTarget(
                target_id=f"T{tid:02d}",
                label=f"gap_{gi}_{gi+1}",
                key_id="",
                screen_x=mid_x,
                screen_y=float(gap_y),
                grid_row=-1,
                grid_col=1,
            )
        )
        tid += 1

    # Extra in-row anchors between left/center/right (constrains horizontal curvature).
    extra_fracs = ((0.28, 1), (0.72, 1))
    if mode == "keyboard15":
        extra_fracs = ((0.28, 0), (0.72, 0), (0.28, 2), (0.72, 2))
    for frac, grid_row in extra_fracs:
        if grid_row >= len(rows):
            continue
        _phys, row_keys = rows[grid_row]
        k = _pick_key_at_x_fraction(row_keys, frac)
        cx, cy = k.center
        out.append(
            CalibrationTarget(
                target_id=f"T{tid:02d}",
                label=f"row{grid_row}_x{int(frac * 100)}",
                key_id=str(k.key_id),
                screen_x=float(cx),
                screen_y=float(cy),
                grid_row=int(grid_row),
                grid_col=1,
            )
        )
        tid += 1

    return out


def keyboard_local_targets(
    *,
    typing_region_rect: QRect,
    mode: str = "default9",
    margin_ratio: float = 0.10,
) -> List[CalibrationTarget]:
    """
    Create keyboard-local targets in global screen coordinates.

    - default9: 3x3 grid inside typing region
    - precision13: 3x3 grid + 4 edge midpoints (top/bottom/left/right)
    """
    if mode not in {"default9", "precision13"}:
        raise ValueError(f"Unknown calibration mode: {mode}")

    pts9 = _grid_points(typing_region_rect, rows=3, cols=3, margin_ratio=margin_ratio)
    points: List[Tuple[float, float]] = list(pts9)
    labels: List[str] = [
        "top_left",
        "top",
        "top_right",
        "left",
        "center",
        "right",
        "bottom_left",
        "bottom",
        "bottom_right",
    ]

    if mode == "precision13":
        r = typing_region_rect
        mx = r.width() * margin_ratio
        my = r.height() * margin_ratio
        left_x = r.x() + mx
        right_x = r.x() + r.width() - mx
        top_y = r.y() + my
        bottom_y = r.y() + r.height() - my
        mid_x = r.x() + r.width() / 2.0
        mid_y = r.y() + r.height() / 2.0
        extra = [
            (mid_x, top_y),      # top_mid (already exists in 3x3 but kept distinct label? skip)
            (mid_x, bottom_y),   # bottom_mid
            (left_x, mid_y),     # left_mid
            (right_x, mid_y),    # right_mid
        ]
        # We already have (mid_x, top_y) and (mid_x, bottom_y) and left/right midpoints in 3x3.
        # For 13pt mode we instead add *quarter* points on each edge (closer to corners) which
        # better constrains curvature near edges without duplicating 3x3 nodes.
        qx1 = r.x() + mx + (r.width() - 2 * mx) * 0.25
        qx3 = r.x() + mx + (r.width() - 2 * mx) * 0.75
        qy1 = r.y() + my + (r.height() - 2 * my) * 0.25
        qy3 = r.y() + my + (r.height() - 2 * my) * 0.75
        extra = [
            (qx1, top_y),   # top_quarter_left
            (qx3, top_y),   # top_quarter_right
            (qx1, bottom_y),# bottom_quarter_left
            (qx3, bottom_y),# bottom_quarter_right
        ]
        points.extend(extra)
        labels.extend(
            [
                "top_quarter_left",
                "top_quarter_right",
                "bottom_quarter_left",
                "bottom_quarter_right",
            ]
        )

    out: List[CalibrationTarget] = []
    for i, ((x, y), label) in enumerate(zip(points, labels)):
        out.append(
            CalibrationTarget(
                target_id=f"T{i + 1:02d}",
                label=label,
                key_id="",
                screen_x=float(x),
                screen_y=float(y),
            )
        )
    return out


def fullscreen_targets(
    *,
    screen_rect: QRect,
    rows: int = 4,
    cols: int = 4,
    margin_px: int = 60,
) -> List[CalibrationTarget]:
    """Generate a rows x cols grid across the full screen (minus a pixel margin)."""
    r = QRect(screen_rect)
    m = int(max(0, margin_px))
    inner = QRect(r.x() + m, r.y() + m, max(1, r.width() - 2 * m), max(1, r.height() - 2 * m))
    pts = _grid_points(inner, rows=int(rows), cols=int(cols), margin_ratio=0.0)
    out: List[CalibrationTarget] = []
    for i, (x, y) in enumerate(pts):
        out.append(
            CalibrationTarget(
                target_id=f"T{i + 1:02d}",
                label=f"fs_{int(rows)}x{int(cols)}:{i+1}",
                key_id="",
                screen_x=float(x),
                screen_y=float(y),
            )
        )
    return out


def row_aware_targets(
    *,
    keys: Iterable[KeyGeometryRow],
    row_names: List[str],
    cols: int = 3,
) -> List[CalibrationTarget]:
    """Generate calibration targets at the center of each semantic keyboard row.

    This is designed for row-aware mapping where vertical is classified into bands.

    We compute one bounding box per semantic row and place `cols` targets across it.
    Targets are returned in top-to-bottom row order.
    """
    keys_list = list(keys)
    if not keys_list:
        return []

    # Group keys by row_index first; caller provides mapping row_index->semantic by names list order.
    row_indices = sorted({k.row_index for k in keys_list})
    if not row_indices:
        return []

    # Map physical row indices (sorted by y) into semantic row_names by rank.
    # If we have more physical rows than semantic rows, we merge by quantized rank.
    centers = []
    for r in row_indices:
        ys = [k.center[1] for k in keys_list if k.row_index == r]
        centers.append((float(sum(ys) / max(1, len(ys))), r))
    centers.sort(key=lambda t: t[0])
    ordered_rows = [r for _, r in centers]

    def sem_for_rank(rank: int) -> str:
        if len(ordered_rows) <= len(row_names):
            return row_names[min(rank, len(row_names) - 1)]
        # Quantize into len(row_names) bins.
        q = int(round((rank / max(1, len(ordered_rows) - 1)) * (len(row_names) - 1)))
        return row_names[max(0, min(len(row_names) - 1, q))]

    out: List[CalibrationTarget] = []
    tid = 1
    for rank, phys_row in enumerate(ordered_rows):
        sem = sem_for_rank(rank)
        row_keys = [k for k in keys_list if k.row_index == phys_row]
        if not row_keys:
            continue
        x0 = min(k.rect.left() for k in row_keys)
        x1 = max(k.rect.right() for k in row_keys)
        y0 = min(k.rect.top() for k in row_keys)
        y1 = max(k.rect.bottom() for k in row_keys)
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0

        xs: List[float]
        if cols <= 1:
            xs = [float(cx)]
        else:
            xs = [float(x0 + (x1 - x0) * (i / (cols - 1))) for i in range(cols)]

        for i, x in enumerate(xs):
            out.append(
                CalibrationTarget(
                    target_id=f"T{tid:02d}",
                    label=f"{sem}:{i+1}/{len(xs)}",
                    key_id="",
                    screen_x=float(x),
                    screen_y=float(cy),
                )
            )
            tid += 1
    return out

