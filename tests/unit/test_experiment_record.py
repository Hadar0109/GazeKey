"""T002: ExperimentRecord persist + keep_git_sha required on keep."""

from __future__ import annotations

import pytest

from tools.evaluation.experiment_record import (
    ExperimentRecord,
    count_wrong_focus,
    write_experiment_record,
    write_hadar_wrong_focus,
)


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


def test_hadar_gate_template_lands_in_session_folder_not_bench_folder(tmp_path):
    path = write_hadar_wrong_focus("sessA-bench1786898690", runs_dir=tmp_path)
    assert path == tmp_path / "sessA" / "hadar_wrong_focus.md"
    text = path.read_text(encoding="utf-8")
    assert "session_id: sessA" in text
    assert "suggestions_used: no" in text
    assert "wrong_focus_count: pending" in text


def test_hadar_gate_records_all_five_keystrokes_including_the_repeated_a(tmp_path):
    path = write_hadar_wrong_focus(
        "sessA",
        h_focus="J",
        a_focus="D",
        d_focus="F",
        a2_focus="D",
        r_focus="G",
        runs_dir=tmp_path,
    )
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    assert "1. H -> J" in lines
    assert "2. A -> D" in lines
    assert "3. D -> F" in lines
    assert "4. A -> D" in lines
    assert "5. R -> G" in lines


def test_wrong_focus_count_scores_hadar_not_the_unique_letters():
    assert count_wrong_focus(["J", "D", "F", "D", "G"]) == "5/5"
    assert count_wrong_focus(["H", "S", "F", "S", "F"]) == "4/5"
    assert count_wrong_focus(["h", "a", "d", "a", "r"]) == "0/5"
    assert count_wrong_focus(["J", "D", "F", "D", "pending"]) == "pending"
    with pytest.raises(ValueError):
        count_wrong_focus(["J", "D", "F", "G"])


def test_hadar_gate_answers_survive_a_rerun_of_the_same_session(tmp_path):
    path = write_hadar_wrong_focus("sessA", runs_dir=tmp_path)
    path.write_text(path.read_text(encoding="utf-8").replace("H -> pending", "H -> J"), "utf-8")
    again = write_hadar_wrong_focus("sessA", runs_dir=tmp_path)
    assert again == path
    assert "H -> J" in path.read_text(encoding="utf-8")
    write_hadar_wrong_focus("sessA", runs_dir=tmp_path, overwrite=True)
    assert "H -> pending" in path.read_text(encoding="utf-8")
