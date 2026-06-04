"""Runtime CSV logging for intent/selection debugging.

Phase 0 goal:
- Provide a stable CSV schema and write minimal useful rows without changing
  runtime behavior.

Later phases can replace placeholder fields with true intent probabilities and
selection policy state.
"""

from __future__ import annotations

import csv
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_runtime_confidence_path() -> Path:
    return _repo_root() / "runtime_key_confidence.csv"


@dataclass
class RuntimeLogRow:
    timestamp_ms: int
    layout_version: str
    calibration_version: int
    mapper_type: str

    blink: bool
    confidence: float
    Lh: Optional[float]
    Lv: Optional[float]
    Rh: Optional[float]
    Rv: Optional[float]
    avg_h: Optional[float]
    avg_v: Optional[float]
    eye_box_w: Optional[float]
    eye_box_h: Optional[float]
    face_x: Optional[float]
    face_y: Optional[float]

    mapped_x: Optional[float]
    mapped_y: Optional[float]
    mapped_quality: Optional[float]
    row_name: str
    row_confidence: Optional[float]

    focused_key_id: str
    focused_key_label: str
    focused_confidence: float
    challenger_key_id: str
    challenger_confidence: float
    switch_allowed: bool
    fixation_state: str
    dwell_progress: float
    activated_key_id: str
    velocity_px_s: Optional[float]
    stability_score: Optional[float]


class RuntimeKeyConfidenceLogger:
    def __init__(self, path: Optional[Path] = None, enabled: bool = True) -> None:
        self.path = path or default_runtime_confidence_path()
        self.enabled = enabled
        self.session_id = uuid.uuid4().hex[:12]
        self._did_write_header = False

    @property
    def fieldnames(self) -> list[str]:
        return [
            "session_id",
            "timestamp_ms",
            "layout_version",
            "calibration_version",
            "mapper_type",
            "blink",
            "confidence",
            "Lh",
            "Lv",
            "Rh",
            "Rv",
            "avg_h",
            "avg_v",
            "eye_box_w",
            "eye_box_h",
            "face_x",
            "face_y",
            "mapped_x",
            "mapped_y",
            "mapped_quality",
            "row_name",
            "row_confidence",
            "focused_key_id",
            "focused_key_label",
            "focused_confidence",
            "challenger_key_id",
            "challenger_confidence",
            "switch_allowed",
            "fixation_state",
            "dwell_progress",
            "activated_key_id",
            "velocity_px_s",
            "stability_score",
        ]

    def log(self, row: RuntimeLogRow) -> None:
        if not self.enabled:
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Append mode; write header once per file creation.
        file_exists = self.path.is_file()
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=self.fieldnames)
            if not file_exists and not self._did_write_header:
                w.writeheader()
                self._did_write_header = True
            w.writerow(
                {
                    "session_id": self.session_id,
                    **row.__dict__,
                }
            )

