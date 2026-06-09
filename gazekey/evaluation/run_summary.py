"""Console and lightweight file records for calibration and benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

RunType = Literal["calibration", "benchmark"]
RunStatus = Literal["passed", "failed"]


@dataclass(frozen=True)
class BenchmarkThresholds:
    """CQ-1 / SC-001–SC-004 thresholds for the default 15-key benchmark."""

    benchmark_key_count: int = 15
    # SC-001: 10/15 correct passes (display ~67%; not strict fractional 0.67).
    min_keys_correct: int = 10
    max_median_error_px: float = 55.0
    min_row_accuracy: float = 0.80
    min_session_floor_keys: int = 8  # SC-004 floor on 15-key set (~53%)
    max_session_spread_fraction: float = 0.20


def benchmark_thresholds() -> BenchmarkThresholds:
    return BenchmarkThresholds()


def display_key_hit_pct(keys_correct: int, keys_total: int) -> int:
    """Rounded display percentage (10/15 → 67%)."""
    if keys_total <= 0:
        return 0
    return int(round(100.0 * keys_correct / keys_total))


@dataclass
class RunSummary:
    session_id: str
    run_type: RunType
    status: RunStatus
    primary_metrics: dict[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


class RunSummaryWriter:
    def __init__(self, runs_dir: Optional[Path] = None) -> None:
        self.runs_dir = runs_dir or (_repo_root() / "runs")

    def format_console(self, summary: RunSummary) -> str:
        tag = summary.run_type
        st = summary.status.upper()
        sid = summary.session_id
        if summary.run_type == "calibration":
            layout = summary.primary_metrics.get("layout", "n/a")
            targets = summary.primary_metrics.get("targets", "n/a")
            line = f"[{tag}] {st} session={sid} layout={layout} targets={targets}"
            loocv = summary.primary_metrics.get("loocv_rms_px")
            if loocv is not None:
                line = f"{line} loocv_rms={float(loocv):.1f}px (supplementary)"
            warn_n = summary.primary_metrics.get("quality_warning_count", 0)
            if warn_n:
                line = f"{line} quality_warnings={warn_n}"
        else:
            correct = summary.primary_metrics.get("keys_correct", 0)
            total = summary.primary_metrics.get("keys_total", 0)
            pct = summary.primary_metrics.get("key_hit_pct", 0)
            row_ok = summary.primary_metrics.get("rows_correct", 0)
            row_total = summary.primary_metrics.get("keys_total", 0)
            median = summary.primary_metrics.get("median_error_px", 0.0)
            line = (
                f"[{tag}] {st} session={sid} keys={correct}/{total} ({pct:.0f}%) "
                f"row={row_ok}/{row_total} median_err={median:.0f}px"
            )
        if summary.failure_reason:
            line = f"{line} reason={summary.failure_reason}"
        return line

    def write(self, summary: RunSummary, *, append_text: Optional[str] = None) -> Path:
        line = self.format_console(summary)
        print(line)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        path = self.runs_dir / f"{summary.run_type}_{summary.session_id}.txt"
        body = line + "\n"
        if append_text:
            body += append_text.rstrip() + "\n"
        path.write_text(body, encoding="utf-8")
        return path

    def write_calibration_summary(
        self,
        *,
        session_id: str,
        status: RunStatus,
        layout: str,
        targets_collected: int,
        targets_total: int,
        failure_reason: Optional[str] = None,
        loocv_rms_px: Optional[float] = None,
        quality_warnings: Optional[list[str]] = None,
    ) -> RunSummary:
        warnings = list(quality_warnings or [])
        summary = RunSummary(
            session_id=session_id,
            run_type="calibration",
            status=status,
            primary_metrics={
                "layout": layout,
                "targets": f"{targets_collected}/{targets_total}",
                "loocv_rms_px": loocv_rms_px,
                "quality_warning_count": len(warnings),
                "quality_warnings": warnings[:5],
            },
            failure_reason=failure_reason,
        )
        self.write(summary)
        return summary

    def write_benchmark_summary(
        self,
        *,
        session_id: str,
        metrics,
        status: RunStatus,
        failure_reason: Optional[str] = None,
        failure_analysis: Optional[str] = None,
    ) -> RunSummary:
        summary = RunSummary(
            session_id=session_id,
            run_type="benchmark",
            status=status,
            primary_metrics={
                "keys_correct": metrics.keys_correct,
                "keys_total": metrics.keys_total,
                "key_hit_pct": display_key_hit_pct(metrics.keys_correct, metrics.keys_total),
                "rows_correct": metrics.rows_correct,
                "row_accuracy_pct": 100.0 * metrics.row_accuracy,
                "median_error_px": metrics.median_pixel_error,
            },
            failure_reason=failure_reason,
        )
        self.write(summary, append_text=failure_analysis)
        return summary


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
