"""Contract: suggestion dwell/mouse → suffix+Space via ActionDispatcher (003)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QRect

from gazekey.input.os_input_adapter import FakeOsInputAdapter
from gazekey.prediction.suggestion_dispatch import dispatch_suggestion_completion
from gazekey.prediction.typing_context import TypingContext
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.dwell_engine import DWELL_SEC, DwellEngine
from gazekey.typing.gaze_typing_runtime import GazeTypingRuntime, MappedGazePoint
from gazekey.typing.key_action import KeyActionKind, KeyActionSource
from gazekey.typing.typing_session import TypingSession


def _key(key_id: str, action: str, rect: QRect, *, enabled: bool = True) -> SimpleNamespace:
    btn = MagicMock()
    btn.isEnabled.return_value = enabled
    return SimpleNamespace(
        key_id=key_id,
        key_action=action,
        key_label=action,
        rect=rect,
        button=btn,
    )


def test_dwell_suggestion_dispatches_suffix_and_space():
    from gazekey.typing.key_action import KeyAction

    adapter = FakeOsInputAdapter()
    session = TypingSession()
    session.activate()
    dispatcher = ActionDispatcher(adapter)
    ctx = TypingContext()
    for ch in "hel":
        ctx.on_action_delivered(
            KeyAction(
                kind=KeyActionKind.CHAR,
                text=ch,
                source=KeyActionSource.MOUSE,
                key_id="k",
                timestamp=1.0,
            ),
            ok=True,
        )
    assert ctx.get_prefix() == "hel"

    accepts: list = []

    def on_accept(key_id: str, source: KeyActionSource) -> None:
        accepts.append((key_id, source))
        published = dispatch_suggestion_completion(
            word="hello",
            prefix=ctx.get_prefix(),
            accept_epoch=ctx.get_epoch(),
            current_epoch=ctx.get_epoch(),
            dispatcher=dispatcher,
            session=session,
            source=source,
            key_id=key_id,
            clock=lambda: 1.0,
        )
        for action in published:
            ctx.on_action_delivered(action, ok=True)

    runtime = GazeTypingRuntime(
        session,
        DwellEngine(),
        dispatcher,
        on_suggestion_accept=on_accept,
    )
    keys = [
        _key("suggestion:0", "suggestion:0", QRect(0, 0, 80, 40), enabled=True),
        _key("r01c00:a", "a", QRect(200, 200, 40, 40), enabled=True),
    ]
    result = runtime.on_mapped_gaze(MappedGazePoint(40, 20, True), DWELL_SEC, keys)
    assert result.suggestion_accepted is True
    assert accepts and accepts[0][0] == "suggestion:0"
    assert [a.text for a in adapter.injected] == ["l", "o", " "]
    assert ctx.get_prefix() == ""


def test_mouse_suggestion_same_path():
    adapter = FakeOsInputAdapter()
    session = TypingSession()
    session.activate()
    dispatcher = ActionDispatcher(adapter)
    called: list = []

    def on_accept(key_id: str, source: KeyActionSource) -> None:
        called.append(source)
        dispatch_suggestion_completion(
            word="help",
            prefix="hel",
            accept_epoch=1,
            current_epoch=1,
            dispatcher=dispatcher,
            session=session,
            source=source,
            key_id=key_id,
            clock=lambda: 1.0,
        )

    runtime = GazeTypingRuntime(
        session,
        DwellEngine(),
        dispatcher,
        on_suggestion_accept=on_accept,
    )
    runtime.on_mouse_key(key_id="suggestion:1", action="suggestion:1")
    assert called == [KeyActionSource.MOUSE]
    assert [a.text for a in adapter.injected] == ["p", " "]


def test_disabled_suggestion_slot_not_dwellable():
    adapter = FakeOsInputAdapter()
    session = TypingSession()
    session.activate()
    accepts: list = []
    runtime = GazeTypingRuntime(
        session,
        DwellEngine(),
        ActionDispatcher(adapter),
        on_suggestion_accept=lambda kid, src: accepts.append(kid),
    )
    keys = [_key("suggestion:0", "suggestion:0", QRect(0, 0, 80, 40), enabled=False)]
    # hit_test_layout_keys skips disabled buttons
    from gazekey.typing.key_hit_tester import hit_test_layout_keys

    assert hit_test_layout_keys(keys, 40, 20) is None
    result = runtime.on_mapped_gaze(MappedGazePoint(40, 20, True), DWELL_SEC, keys)
    assert result.published is None
    assert result.suggestion_accepted is False
    assert accepts == []
    assert adapter.injected == []


def test_suggestion_after_mixed_page_prefix_still_sends_suffix_and_space():
    """T028: prefix he (H right page, E left page) still completes hello as suffix+Space."""
    from gazekey.typing.key_action import KeyAction
    from gazekey.typing.key_semantics import PAGE_LEFT_KEY_ID

    adapter = FakeOsInputAdapter()
    session = TypingSession()
    session.activate()
    dispatcher = ActionDispatcher(adapter)
    ctx = TypingContext()
    switches: list[str] = []

    def _deliver(ch: str) -> None:
        ctx.on_action_delivered(
            KeyAction(
                kind=KeyActionKind.CHAR,
                text=ch,
                source=KeyActionSource.MOUSE,
                key_id="k",
                timestamp=1.0,
            ),
            ok=True,
        )

    _deliver("h")
    runtime = GazeTypingRuntime(
        session,
        DwellEngine(),
        dispatcher,
        on_page_switch=lambda: switches.append("switch"),
        on_suggestion_accept=lambda key_id, source: dispatch_suggestion_completion(
            word="hello",
            prefix=ctx.get_prefix(),
            accept_epoch=ctx.get_epoch(),
            current_epoch=ctx.get_epoch(),
            dispatcher=dispatcher,
            session=session,
            source=source,
            key_id=key_id,
            clock=lambda: 1.0,
        ),
    )
    assert runtime.on_mouse_key(key_id=PAGE_LEFT_KEY_ID, action=PAGE_LEFT_KEY_ID) is None
    _deliver("e")
    assert ctx.get_prefix() == "he"
    assert switches == ["switch"]

    runtime.on_mouse_key(key_id="suggestion:0", action="suggestion:0")
    assert [a.text for a in adapter.injected] == ["l", "l", "o", " "]
