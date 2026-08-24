"""BenchmarkEvalSession timing and per-key smoother reset hooks."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from tools.evaluation.benchmark_runner import COLLECT_MS, SETTLE_MS
from tools.evaluation.benchmark_session import BenchmarkEvalSession
from gazekey.layout.layout_inspector import KeyGeometryRow


def _key(label: str, *, x: float = 100.0, y: float = 100.0) -> KeyGeometryRow:
    return KeyGeometryRow(
        key_id=label.lower(),
        key_label=label,
        key_action=label.lower() if label != "Space" else " ",
        row_index=0,
        col_index=0,
        button=MagicMock(),
        rect=MagicMock(),
        center=(x, y),
        hitbox=MagicMock(),
        is_special_key=False,
        weight=1.0,
    )


def _feat(ts: int = 0) -> SimpleNamespace:
    return SimpleNamespace(timestamp_ms=ts)


def test_on_key_begin_called_at_session_start_and_after_each_key():
    calls: list[str] = []
    samples = [("Q", _key("Q")), ("E", _key("E", x=200.0))]

    session = BenchmarkEvalSession(
        samples,
        keys_for_hit_test=[k for _, k in samples],
        predict_screen_xy=lambda _f: (100.0, 100.0),
        on_key_begin=lambda: calls.append("reset"),
    )
    t = 0
    session.begin(t)
    assert calls == ["reset"]

    t += SETTLE_MS
    session.tick(t)
    t += COLLECT_MS
    session.tick(t, features=_feat(t))
    assert calls == ["reset", "reset"]

    t += SETTLE_MS
    session.tick(t)
    t += COLLECT_MS
    session.tick(t, features=_feat(t))
    assert calls == ["reset", "reset"]
    assert session.finished
