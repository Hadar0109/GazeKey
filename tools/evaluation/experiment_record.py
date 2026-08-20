"""Persist Feature 004 ExperimentRecord files under ``runs/<session_id>/``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from tools.evaluation.session_paths import artifact_path, ensure_session_dir

EXPERIMENT_RECORD_FILE = "experiment_record.md"
HADAR_WRONG_FOCUS_FILE = "hadar_wrong_focus.md"

EXPERIMENT_RECORD_TEMPLATE = """# ExperimentRecord

- hypothesis: {hypothesis}
- logical_area: {logical_area}
- change: {change}
- eval_before: {eval_before}
- eval_after: {eval_after}
- decision: {decision}
- keep_git_sha: {keep_git_sha}
- notes: {notes}
"""

HADAR_WRONG_FOCUS_TEMPLATE = """# hadar USER GATE (suggestions unused)

- session_id: {session_id}
- word: hadar
- suggestions_used: no
- wrong_focus_letters:
  - H: {h_focus}
  - A: {a_focus}
  - D: {d_focus}
  - R: {r_focus}
- dwell_notes: {dwell_notes}
- compared_to_baseline_a_b: {compared_to}
"""


@dataclass
class ExperimentRecord:
    hypothesis: str
    logical_area: str
    change: str
    eval_before: str
    eval_after: str
    decision: str
    keep_git_sha: str = "n/a"
    notes: str = ""

    def __post_init__(self) -> None:
        area = str(self.logical_area).strip().lower()
        allowed = {"eval", "collection", "sync", "geometry", "coverage", "mapper"}
        if area not in allowed:
            raise ValueError(f"logical_area must be one of {sorted(allowed)}")
        decision = str(self.decision).strip().lower()
        allowed_decisions = {
            "keep",
            "revert",
            "inconclusive",
            "currentstatebaseline a",
            "currentstatebaseline b",
            "pending",
        }
        if decision not in allowed_decisions:
            raise ValueError(f"decision must be keep|revert|inconclusive (or a baseline label)")
        if decision == "keep" and (not str(self.keep_git_sha).strip() or str(self.keep_git_sha).strip().lower() in {"n/a", "none"}):
            raise ValueError("keep_git_sha is required when decision == keep")


def write_experiment_record(
    session_id: str,
    record: ExperimentRecord,
    *,
    runs_dir: Optional[Union[Path, str]] = None,
) -> Path:
    """Write ``experiment_record.md`` for this session. Evaluation-only I/O."""
    ensure_session_dir(session_id, runs_dir=runs_dir)
    path = artifact_path(session_id, EXPERIMENT_RECORD_FILE, runs_dir=runs_dir)
    body = EXPERIMENT_RECORD_TEMPLATE.format(
        hypothesis=record.hypothesis,
        logical_area=record.logical_area,
        change=record.change,
        eval_before=record.eval_before,
        eval_after=record.eval_after,
        decision=record.decision,
        keep_git_sha=record.keep_git_sha,
        notes=record.notes,
    )
    path.write_text(body, encoding="utf-8")
    return path


def write_hadar_wrong_focus(
    session_id: str,
    *,
    h_focus: str = "pending",
    a_focus: str = "pending",
    d_focus: str = "pending",
    r_focus: str = "pending",
    dwell_notes: str = "",
    compared_to: str = "n/a (this is a baseline capture)",
    runs_dir: Optional[Union[Path, str]] = None,
) -> Path:
    ensure_session_dir(session_id, runs_dir=runs_dir)
    path = artifact_path(session_id, HADAR_WRONG_FOCUS_FILE, runs_dir=runs_dir)
    body = HADAR_WRONG_FOCUS_TEMPLATE.format(
        session_id=session_id,
        h_focus=h_focus,
        a_focus=a_focus,
        d_focus=d_focus,
        r_focus=r_focus,
        dwell_notes=dwell_notes or "(fill after typing hadar with suggestions unused)",
        compared_to=compared_to,
    )
    path.write_text(body, encoding="utf-8")
    return path
