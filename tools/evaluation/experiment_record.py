"""Persist Feature 004 ExperimentRecord files under ``runs/<session_id>/``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union

from tools.evaluation.session_paths import artifact_path, ensure_session_dir, folder_session_id

EXPERIMENT_RECORD_FILE = "experiment_record.md"
HADAR_WRONG_FOCUS_FILE = "hadar_wrong_focus.md"

FEATURE_004_EVAL_BEFORE = (
    "Feature 004 A/B 14938da0bdf0, 34fb259ccdfd; "
    "Feature 004 T060 689c8a8ce90c, 4f665467b260 (eval_before only)"
)

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
- keystroke_focus (intended -> focused):
  1. H -> {h_focus}
  2. A -> {a_focus}
  3. D -> {d_focus}
  4. A -> {a2_focus}
  5. R -> {r_focus}
- wrong_focus_count: {wrong_focus_count}
- dwell_notes: {dwell_notes}
- compared_to_baseline_a_b: {compared_to}
"""

HADAR_KEYSTROKES = ("H", "A", "D", "A", "R")


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


def count_wrong_focus(observed: Sequence[str]) -> str:
    """``n/5`` wrong-focus keystrokes for ``hadar``, or ``pending`` if unanswered."""
    if len(observed) != len(HADAR_KEYSTROKES):
        raise ValueError(f"expected {len(HADAR_KEYSTROKES)} observations for 'hadar'")
    seen = [str(v).strip() for v in observed]
    if any(not v or v.lower() == "pending" for v in seen):
        return "pending"
    wrong = sum(
        1 for intended, got in zip(HADAR_KEYSTROKES, seen) if got.upper() != intended.upper()
    )
    return f"{wrong}/{len(HADAR_KEYSTROKES)}"


def write_hadar_wrong_focus(
    session_id: str,
    *,
    h_focus: str = "pending",
    a_focus: str = "pending",
    d_focus: str = "pending",
    a2_focus: str = "pending",
    r_focus: str = "pending",
    dwell_notes: str = "",
    compared_to: str = "n/a (this is a baseline capture)",
    runs_dir: Optional[Union[Path, str]] = None,
    overwrite: bool = False,
) -> Path:
    ensure_session_dir(session_id, runs_dir=runs_dir)
    path = artifact_path(session_id, HADAR_WRONG_FOCUS_FILE, runs_dir=runs_dir)
    if path.exists() and not overwrite:
        # A gate the user already answered must survive a re-run of the same session.
        return path
    observed = (h_focus, a_focus, d_focus, a2_focus, r_focus)
    body = HADAR_WRONG_FOCUS_TEMPLATE.format(
        session_id=folder_session_id(session_id),
        h_focus=h_focus,
        a_focus=a_focus,
        d_focus=d_focus,
        a2_focus=a2_focus,
        r_focus=r_focus,
        wrong_focus_count=count_wrong_focus(observed),
        dwell_notes=dwell_notes or "(fill after typing hadar with suggestions unused)",
        compared_to=compared_to,
    )
    path.write_text(body, encoding="utf-8")
    return path
