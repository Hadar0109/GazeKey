"""T002: ExperimentRecord persist + keep_git_sha required on keep."""

from __future__ import annotations

import pytest

from tools.evaluation.experiment_record import ExperimentRecord, write_experiment_record


def test_keep_requires_git_sha():
    with pytest.raises(ValueError):
        ExperimentRecord(
            hypothesis="x",
            logical_area="eval",
            change="none",
            eval_before="A,B",
            eval_after="C",
            decision="keep",
            keep_git_sha="n/a",
        )


def test_write_experiment_record_round_trip(tmp_path):
    rec = ExperimentRecord(
        hypothesis="baseline",
        logical_area="eval",
        change="none (current-state baseline)",
        eval_before="n/a",
        eval_after="sessA",
        decision="CurrentStateBaseline A",
        notes="inventory in mapping_path_inventory.md",
    )
    path = write_experiment_record("sessA", rec, runs_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert path == tmp_path / "sessA" / "experiment_record.md"
    assert "logical_area: eval" in text
    assert "keep_git_sha:" in text
    assert "CurrentStateBaseline A" in text
