"""Tests for keyboard-level accuracy diagnostics."""

from PySide6.QtCore import QRect

from gazekey.debug.keyboard_accuracy import (
    build_result_row,
    predict_key_at,
    print_accuracy_summary,
    resolve_sample_keys,
)
from gazekey.layout.layout_inspector import KeyGeometryRow


def _fake_key(
    *,
    key_id: str,
    label: str,
    action: str,
    rect: QRect,
    row: int = 0,
    col: int = 0,
) -> KeyGeometryRow:
    cx = float(rect.center().x())
    cy = float(rect.center().y())
    return KeyGeometryRow(
        key_id=key_id,
        key_label=label,
        key_action=action,
        row_index=row,
        col_index=col,
        button=None,  # type: ignore[arg-type]
        rect=rect,
        center=(cx, cy),
        hitbox=rect,
        is_special_key=action == " ",
        weight=1.0,
    )


def test_resolve_sample_keys_lowercase_actions():
    keys = [
        _fake_key(key_id="q", label="q", action="q", rect=QRect(0, 0, 40, 40), row=0, col=0),
        _fake_key(key_id="e", label="e", action="e", rect=QRect(50, 0, 40, 40), row=0, col=1),
        _fake_key(key_id="sp", label="Space", action=" ", rect=QRect(0, 80, 200, 30), row=3, col=1),
    ]
    resolved = resolve_sample_keys(keys, ["Q", "E", "Space"])
    assert [lbl for lbl, _ in resolved] == ["Q", "E", "Space"]
    assert resolved[0][1].key_action == "q"
    assert resolved[2][1].key_action == " "


def test_predict_key_at_contains_then_nearest_center():
    keys = [
        _fake_key(key_id="a", label="a", action="a", rect=QRect(0, 0, 100, 100)),
        _fake_key(key_id="b", label="b", action="b", rect=QRect(200, 0, 100, 100)),
    ]
    inside = predict_key_at(50.0, 50.0, keys)
    assert inside.key_id == "a"
    nearest = predict_key_at(150.0, 50.0, keys)
    assert nearest.key_id in {"a", "b"}


def test_build_result_row_and_summary(capsys):
    target = _fake_key(key_id="e", label="e", action="e", rect=QRect(100, 100, 40, 40))
    other = _fake_key(key_id="r", label="r", action="r", rect=QRect(200, 100, 40, 40))
    row = build_result_row(
        target_label="E",
        target=target,
        predicted_x=210.0,
        predicted_y=120.0,
        predicted=other,
    )
    assert row.target_key == "E"
    assert row.predicted_key == "R"
    assert not row.is_correct
    print_accuracy_summary([row])
    out = capsys.readouterr().out
    assert "accuracy:" in out
    assert "E -> R" in out
