"""CSV logging for calibration v2.

This module is intentionally usable before calibration v2 is fully implemented:
- It provides stable schemas (Phase 0 instrumentation-first).
- Callers can log accepted/rejected samples and final summaries.
"""

from __future__ import annotations

import csv
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_calibration_samples_path() -> Path:
    return _repo_root() / "calibration_samples.csv"


def default_calibration_summary_path() -> Path:
    return _repo_root() / "calibration_summary.csv"


@dataclass(frozen=True)
class CalibrationSampleRow:
    calibration_version: int
    session_id: str
    sample_index: int

    target_id: str
    target_key_id: str
    target_label: str
    target_screen_x: float
    target_screen_y: float

    timestamp_ms: int
    face_detected: bool
    blink: bool

    left_eye_h: Optional[float]
    left_eye_v: Optional[float]
    right_eye_h: Optional[float]
    right_eye_v: Optional[float]
    avg_h: Optional[float]
    avg_v: Optional[float]
    eye_box_w: Optional[float]
    eye_box_h: Optional[float]
    face_x: Optional[float]
    face_y: Optional[float]
    head_stability: Optional[float]
    confidence: float

    fixation_state: str
    accepted: bool
    rejection_reason: str
    quality_score: Optional[float]
    window_std_h: Optional[float]
    window_std_v: Optional[float]
    velocity: Optional[float]
    stable_duration_ms: Optional[float]
    pca_uL: Optional[float] = None
    pca_vL: Optional[float] = None
    pca_uR: Optional[float] = None
    pca_vR: Optional[float] = None


@dataclass(frozen=True)
class CalibrationSummaryRow:
    calibration_version: int
    session_id: str

    # Either "target" or "overall"
    record_type: str

    target_id: str
    target_label: str
    target_screen_x: Optional[float]
    target_screen_y: Optional[float]

    n_seen: int
    n_accepted: int
    n_rejected: int

    quality_score: Optional[float]
    estimated_error_px: Optional[float]

    mapper_type: str
    calibration_mode: str


def schema_notes() -> str:
    """
    Human-readable schema intent (kept in code for easy debugging).

    - `target_id`: "T01".."T09" (default) or "T01".."T13" (precision).
    - `target_key_id`: stable key id from keyboard_layout.csv when a target
       corresponds to a specific key; empty for area targets.
    - `target_screen_x/y`: always global screen pixels.
    """
    return "calibration v2 csv schemas"


class CalibrationCsvLogger:
    def __init__(
        self,
        *,
        samples_path: Optional[Path] = None,
        summary_path: Optional[Path] = None,
        enabled: bool = True,
        session_id: Optional[str] = None,
    ) -> None:
        self.samples_path = samples_path or default_calibration_samples_path()
        self.summary_path = summary_path or default_calibration_summary_path()
        self.enabled = enabled
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self._wrote_samples_header = False
        self._summary_rows: List[CalibrationSummaryRow] = []

    def begin_calibration_run(self) -> None:
        """Truncate per-run debug CSVs so each calibration starts with fresh files."""
        if not self.enabled:
            return
        self._summary_rows = []
        self.samples_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.samples_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.sample_fieldnames)
            w.writeheader()
            self._wrote_samples_header = True
        with open(self.summary_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.summary_fieldnames)
            w.writeheader()

    @property
    def sample_fieldnames(self) -> list[str]:
        return [
            "calibration_version",
            "session_id",
            "sample_index",
            "target_id",
            "target_key_id",
            "target_label",
            "target_screen_x",
            "target_screen_y",
            "timestamp_ms",
            "face_detected",
            "blink",
            "left_eye_h",
            "left_eye_v",
            "right_eye_h",
            "right_eye_v",
            "avg_h",
            "avg_v",
            "eye_box_w",
            "eye_box_h",
            "face_x",
            "face_y",
            "head_stability",
            "confidence",
            "fixation_state",
            "accepted",
            "rejection_reason",
            "quality_score",
            "window_std_h",
            "window_std_v",
            "velocity",
            "stable_duration_ms",
            "pca_uL",
            "pca_vL",
            "pca_uR",
            "pca_vR",
        ]

    @property
    def summary_fieldnames(self) -> list[str]:
        return [
            "calibration_version",
            "session_id",
            "record_type",
            "target_id",
            "target_label",
            "target_screen_x",
            "target_screen_y",
            "n_seen",
            "n_accepted",
            "n_rejected",
            "quality_score",
            "estimated_error_px",
            "mapper_type",
            "calibration_mode",
        ]

    def log_sample(self, row: CalibrationSampleRow) -> None:
        if not self.enabled:
            return
        if not self._wrote_samples_header:
            self.begin_calibration_run()
        self.samples_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.samples_path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.sample_fieldnames)
            w.writerow(row.__dict__)

    def log_summary(self, row: CalibrationSummaryRow) -> None:
        """Queue summary rows; written once via `flush_summary()`."""
        if not self.enabled:
            return
        self._summary_rows.append(row)

    def flush_summary(self, *, overwrite: bool = True) -> None:
        """Write summary rows once at end of calibration.

        We overwrite by default to ensure `calibration_summary.csv` contains only
        one row per target plus one overall row for the latest calibration run.
        """
        if not self.enabled:
            return
        self.summary_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "w" if overwrite else "a"
        with open(self.summary_path, mode, newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.summary_fieldnames)
            w.writeheader()
            for row in self._summary_rows:
                w.writerow(row.__dict__)

