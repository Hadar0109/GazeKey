"""Shared session identifiers and Feature 004 location-result records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from gazekey.runtime.session_id import new_session_id
from tools.evaluation.benchmark_runner import KeyAccuracyResultRow

__all__ = ["LocationResult", "location_results_from_rows", "new_session_id"]


@dataclass(frozen=True)
class LocationResult:
    """Per-location mapped-key score (data-model LocationResult)."""

    label: str
    intended_rect: str
    was_calibration_location: bool
    rep_x: float
    rep_y: float
    inside_tight: bool
    focus_stability: float
    dx: float
    dy: float
    error_px: float
    dx_over_width: float
    dy_over_height: float
    row_correct: bool
    dwell_activated_id: Optional[str] = None


def location_results_from_rows(rows: Sequence[KeyAccuracyResultRow]) -> tuple[LocationResult, ...]:
    out: list[LocationResult] = []
    for r in rows:
        out.append(
            LocationResult(
                label=r.target_key,
                intended_rect=f"center=({r.target_center_x:.1f},{r.target_center_y:.1f})",
                was_calibration_location=bool(r.was_calibration_location),
                rep_x=float(r.predicted_x),
                rep_y=float(r.predicted_y),
                inside_tight=bool(r.inside_tight),
                focus_stability=float(r.focus_stability),
                dx=float(r.dx),
                dy=float(r.dy),
                error_px=float(r.error_px),
                dx_over_width=float(r.dx_over_width),
                dy_over_height=float(r.dy_over_height),
                row_correct=bool(r.row_correct),
            )
        )
    return tuple(out)


def format_location_results(rows: Sequence[KeyAccuracyResultRow]) -> str:
    """Plain-text per-location block for ``benchmark_summary.txt``."""
    lines = [
        "location_results:",
        "  label inside_tight focus_stability dx dy error_px dx/w dy/h row_correct slice",
    ]
    for r in rows:
        slices = []
        if r.was_calibration_location:
            slices.append("repeatability")
        if r.in_held_out_letter_slice:
            slices.append("held_out")
        if r.in_editing_control_slice:
            slices.append("editing")
        slice_s = ",".join(slices) or "other"
        lines.append(
            f"  {r.target_key} inside={int(r.inside_tight)} stab={r.focus_stability:.2f} "
            f"dx={r.dx:+.1f} dy={r.dy:+.1f} err={r.error_px:.1f} "
            f"dx/w={r.dx_over_width:.2f} dy/h={r.dy_over_height:.2f} "
            f"row={int(r.row_correct)} {slice_s}"
        )
    return "\n".join(lines)
