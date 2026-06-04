"""Compute per-key intent probabilities from a mapped gaze point.

Phase 3 baseline model:
- geometric likelihood from distance to key center (Gaussian)
- bonus when inside enlarged hitbox
- key weight prior (e.g. Space slightly higher)

This deliberately stays simple and fast; hysteresis/anti-flicker live in selection policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QPoint, QRect

from gazekey.layout.layout_inspector import KeyGeometryRow


@dataclass(frozen=True)
class KeyIntentScore:
    key_id: str
    key_label: str
    key_action: str
    probability: float
    raw_score: float


def _gaussian(d: float, sigma: float) -> float:
    if sigma <= 1e-6:
        return 0.0
    return exp(-0.5 * (d / sigma) ** 2)


def score_keys(
    *,
    keys: Sequence[KeyGeometryRow],
    gaze_x: float,
    gaze_y: float,
    sigma_px: float = 80.0,
    sigma_y_px: Optional[float] = None,
    hitbox_bonus: float = 1.35,
    focused_key_id: Optional[str] = None,
    row_stickiness: float = 1.45,
    cross_row_penalty: float = 0.55,
) -> List[KeyIntentScore]:
    p = QPoint(int(gaze_x), int(gaze_y))
    sig_x = float(sigma_px)
    sig_y = float(sigma_y_px if sigma_y_px is not None else sigma_px * 1.35)

    focused_row: Optional[int] = None
    if focused_key_id is not None:
        for k in keys:
            if k.key_id == focused_key_id:
                focused_row = int(k.row_index)
                break

    scores: List[Tuple[KeyGeometryRow, float]] = []
    for k in keys:
        cx, cy = k.center
        dx = float(gaze_x - cx)
        dy = float(gaze_y - cy)
        # Anisotropic distance: tolerate more vertical jitter within a row.
        d = ((dx / max(sig_x, 1e-6)) ** 2 + (dy / max(sig_y, 1e-6)) ** 2) ** 0.5
        s = _gaussian(d, sigma=1.0) * float(k.weight)
        if k.hitbox.contains(p):
            s *= hitbox_bonus
        if focused_row is not None:
            if int(k.row_index) == focused_row:
                s *= float(row_stickiness)
            else:
                s *= float(cross_row_penalty)
        scores.append((k, float(s)))

    total = sum(s for _, s in scores)
    if total <= 1e-12:
        return [
            KeyIntentScore(
                key_id=k.key_id,
                key_label=k.key_label,
                key_action=k.key_action,
                probability=0.0,
                raw_score=0.0,
            )
            for k in keys
        ]

    out = [
        KeyIntentScore(
            key_id=k.key_id,
            key_label=k.key_label,
            key_action=k.key_action,
            probability=s / total,
            raw_score=s,
        )
        for k, s in scores
    ]
    out.sort(key=lambda r: r.probability, reverse=True)
    return out

