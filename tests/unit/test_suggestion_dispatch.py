"""Unit tests for suggestion_dispatch (suffix, epoch, Shift casing)."""

from __future__ import annotations

from gazekey.input.os_input_adapter import FakeOsInputAdapter
from gazekey.prediction.suggestion_dispatch import (
    compute_suggestion_suffix,
    dispatch_suggestion_completion,
)
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.key_action import KeyActionSource
from gazekey.typing.typing_session import TypingSession


def test_compute_suffix_hel_hello():
    assert compute_suggestion_suffix("hel", "hello") == "lo"
    assert compute_suggestion_suffix("hello", "hello") == ""


def test_dispatch_hel_hello_suffix_and_space():
    adapter = FakeOsInputAdapter()
    dispatcher = ActionDispatcher(adapter)
    session = TypingSession()
    session.activate()
    published = dispatch_suggestion_completion(
        word="hello",
        prefix="hel",
        accept_epoch=3,
        current_epoch=3,
        dispatcher=dispatcher,
        session=session,
        source=KeyActionSource.DWELL,
        key_id="suggestion:0",
        clock=lambda: 1.0,
    )
    assert [a.text for a in published] == ["l", "o", " "]
    assert [a.text for a in adapter.injected] == ["l", "o", " "]


def test_stale_epoch_no_dispatch():
    adapter = FakeOsInputAdapter()
    dispatcher = ActionDispatcher(adapter)
    session = TypingSession()
    session.activate()
    published = dispatch_suggestion_completion(
        word="hello",
        prefix="hel",
        accept_epoch=2,
        current_epoch=3,
        dispatcher=dispatcher,
        session=session,
        clock=lambda: 1.0,
    )
    assert published == []
    assert adapter.injected == []


def test_shift_armed_nonempty_prefix_clears_shift_lowercase_suffix():
    adapter = FakeOsInputAdapter()
    dispatcher = ActionDispatcher(adapter)
    session = TypingSession()
    session.activate()
    session.arm_shift()
    assert session.shift_oneshot_armed
    published = dispatch_suggestion_completion(
        word="hello",
        prefix="hel",
        accept_epoch=1,
        current_epoch=1,
        dispatcher=dispatcher,
        session=session,
        clock=lambda: 1.0,
    )
    assert [a.text for a in published] == ["l", "o", " "]
    assert all(t.islower() or t == " " for t in (a.text for a in adapter.injected))
    assert not session.shift_oneshot_armed
    # Must not produce mixed casing like helLo
    assert "L" not in "".join(a.text or "" for a in adapter.injected)


def test_partial_failure_stops_batch():
    adapter = FakeOsInputAdapter()
    dispatcher = ActionDispatcher(adapter)
    session = TypingSession()
    session.activate()
    count = {"n": 0}

    original = adapter.inject

    def fail_after_first(action):
        count["n"] += 1
        if count["n"] >= 2:
            adapter.fail = True
            adapter.error = "fail"
        return original(action)

    adapter.inject = fail_after_first  # type: ignore[method-assign]

    published = dispatch_suggestion_completion(
        word="hello",
        prefix="hel",
        accept_epoch=1,
        current_epoch=1,
        dispatcher=dispatcher,
        session=session,
        clock=lambda: 1.0,
    )
    assert [a.text for a in published] == ["l", "o"]
    assert len(adapter.injected) == 2
