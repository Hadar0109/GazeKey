"""Format per-key benchmark failures for run summaries (FR-023)."""

from __future__ import annotations

from typing import List, Sequence

from tools.evaluation.benchmark_runner import KeyAccuracyResultRow


def format_failure_analysis(
    rows: Sequence[KeyAccuracyResultRow],
    *,
    likely_cause: str = "unknown",
) -> str:
    """Short written conclusion: which keys/rows failed and likely cause."""
    if not rows:
        return "failure_analysis: no benchmark rows"

    missed = [r for r in rows if not r.is_correct]
    row_missed = [r for r in rows if not r.row_correct]
    lines: List[str] = [
        "failure_analysis:",
        f"  likely_cause: {likely_cause}",
        f"  keys_failed: {len(missed)}/{len(rows)}",
        f"  rows_failed: {len(row_missed)}/{len(rows)}",
    ]
    if missed:
        lines.append("  per_key_misses:")
        for r in missed:
            lines.append(
                f"    {r.target_key} -> {r.predicted_key} "
                f"dx={r.dx:+.1f} dy={r.dy:+.1f} err={r.error_px:.1f}px"
            )
    if row_missed and len(row_missed) != len(missed):
        bad_rows = sorted({r.target_key for r in row_missed if r.is_correct})
        if bad_rows:
            lines.append(f"  row_only_errors: {', '.join(bad_rows)}")
    return "\n".join(lines)


def infer_likely_cause(rows: Sequence[KeyAccuracyResultRow]) -> str:
    """Heuristic tag for failure-pattern guide (mapping vs geometry vs collection)."""
    if not rows:
        return "collection"
    row_fail = sum(1 for r in rows if not r.row_correct)
    col_fail = sum(1 for r in rows if not r.is_correct and r.row_correct)
    if row_fail > len(rows) // 2:
        dys = [abs(r.dy) for r in rows if not r.is_correct]
        if dys and sum(dys) / len(dys) > 40.0:
            return "mapping"
        return "mapping"
    if col_fail > len(rows) // 3:
        return "geometry"
    return "mapping"
