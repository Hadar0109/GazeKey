"""Session-scoped artifact paths under ``runs/<session_id>/``."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

CALIBRATION_SUMMARY_FILE = "calibration_summary.txt"
BENCHMARK_SUMMARY_FILE = "benchmark_summary.txt"
BENCHMARK_DIAG_FILE = "benchmark_diag.json"
COVERAGE_FILE = "coverage.json"
GEOMETRY_CHECK_FILE = "geometry_check.txt"
CALIBRATION_DEBUG_CSV = "calibration_debug.csv"
CALIBRATION_RATIO_SPACE_CSV = "calibration_ratio_space.csv"
KEYBOARD_LAYOUT_FILE = "keyboard_layout.csv"
CALIBRATION_V2_FILE = "calibration_v2.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def runs_root(runs_dir: Optional[Union[Path, str]] = None) -> Path:
    if runs_dir is None:
        return _repo_root() / "runs"
    return Path(runs_dir)


def sanitize_session_id(session_id: str) -> str:
    safe = "".join(c for c in str(session_id) if c.isalnum() or c in ("-", "_"))
    return safe or "session"


def folder_session_id(session_id: str) -> str:
    """Map a benchmark run id (``<calib>-bench<ts>``) to its session folder name."""
    sid = sanitize_session_id(session_id)
    marker = "-bench"
    if marker in sid:
        return sid.split(marker, 1)[0]
    return sid


def session_dir(session_id: str, *, runs_dir: Optional[Union[Path, str]] = None) -> Path:
    return runs_root(runs_dir) / folder_session_id(session_id)


def ensure_session_dir(session_id: str, *, runs_dir: Optional[Union[Path, str]] = None) -> Path:
    path = session_dir(session_id, runs_dir=runs_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifact_path(
    session_id: str,
    filename: str,
    *,
    runs_dir: Optional[Union[Path, str]] = None,
) -> Path:
    return session_dir(session_id, runs_dir=runs_dir) / filename


def calibration_summary_path(session_id: str, *, runs_dir: Optional[Union[Path, str]] = None) -> Path:
    return artifact_path(session_id, CALIBRATION_SUMMARY_FILE, runs_dir=runs_dir)


def benchmark_summary_path(session_id: str, *, runs_dir: Optional[Union[Path, str]] = None) -> Path:
    return artifact_path(session_id, BENCHMARK_SUMMARY_FILE, runs_dir=runs_dir)


def benchmark_diag_path(session_id: str, *, runs_dir: Optional[Union[Path, str]] = None) -> Path:
    return artifact_path(session_id, BENCHMARK_DIAG_FILE, runs_dir=runs_dir)


def coverage_path(session_id: str, *, runs_dir: Optional[Union[Path, str]] = None) -> Path:
    return artifact_path(session_id, COVERAGE_FILE, runs_dir=runs_dir)


def geometry_check_path(session_id: str, *, runs_dir: Optional[Union[Path, str]] = None) -> Path:
    return artifact_path(session_id, GEOMETRY_CHECK_FILE, runs_dir=runs_dir)


def keyboard_layout_path(session_id: str, *, runs_dir: Optional[Union[Path, str]] = None) -> Path:
    return artifact_path(session_id, KEYBOARD_LAYOUT_FILE, runs_dir=runs_dir)


def calibration_v2_path(session_id: str, *, runs_dir: Optional[Union[Path, str]] = None) -> Path:
    return artifact_path(session_id, CALIBRATION_V2_FILE, runs_dir=runs_dir)
