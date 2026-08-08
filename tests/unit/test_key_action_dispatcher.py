"""Unit tests: KeyAction request vs delivered with FakeOsInputAdapter."""

from __future__ import annotations

from gazekey.input.os_input_adapter import FakeOsInputAdapter, OsInjectResult
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.key_action import KeyAction, KeyActionKind, KeyActionSource


def _char_action(text: str = "a", key_id: str = "key_a") -> KeyAction:
    return KeyAction(
        kind=KeyActionKind.CHAR,
        text=text,
        source=KeyActionSource.DWELL,
        key_id=key_id,
        timestamp=1.0,
    )


def test_publish_notifies_requested_then_delivered_on_success():
    adapter = FakeOsInputAdapter()
    dispatcher = ActionDispatcher(adapter)
    events: list[tuple] = []

    dispatcher.on_action_requested(lambda a: events.append(("requested", a)))
    dispatcher.on_action_delivered(
        lambda a, r: events.append(("delivered", a, r))
    )

    action = _char_action("x")
    result = dispatcher.publish(action)

    assert result.ok is True
    assert result.error is None
    assert adapter.injected == [action]
    assert [e[0] for e in events] == ["requested", "delivered"]
    assert events[0][1] is action
    assert events[1][1] is action
    assert events[1][2] == OsInjectResult(ok=True)


def test_publish_delivered_with_ok_false_when_adapter_fails():
    adapter = FakeOsInputAdapter(fail=True, error="no_target")
    dispatcher = ActionDispatcher(adapter)
    requested: list[KeyAction] = []
    delivered: list[tuple[KeyAction, OsInjectResult]] = []

    dispatcher.on_action_requested(requested.append)
    dispatcher.on_action_delivered(lambda a, r: delivered.append((a, r)))

    action = _char_action("z")
    result = dispatcher.publish(action)

    assert len(requested) == 1
    assert requested[0] is action
    assert len(delivered) == 1
    assert delivered[0][0] is action
    assert result.ok is False
    assert result.error == "no_target"
    assert delivered[0][1].ok is False
    assert delivered[0][1].error == "no_target"
    # Failure still records the attempted inject on the fake.
    assert adapter.injected == [action]


def test_key_action_kinds_and_optional_text():
    char = KeyAction(
        kind=KeyActionKind.CHAR,
        text="A",
        source=KeyActionSource.MOUSE,
        key_id="key_a",
        timestamp=2.0,
    )
    backspace = KeyAction(
        kind=KeyActionKind.BACKSPACE,
        source=KeyActionSource.DWELL,
        key_id="key_backspace",
        timestamp=3.0,
    )
    enter = KeyAction(
        kind=KeyActionKind.ENTER,
        source=KeyActionSource.DWELL,
        key_id="key_enter",
        timestamp=4.0,
    )

    assert char.text == "A"
    assert backspace.text is None
    assert enter.kind is KeyActionKind.ENTER

    adapter = FakeOsInputAdapter()
    dispatcher = ActionDispatcher(adapter)
    assert dispatcher.publish(backspace).ok is True
    assert dispatcher.publish(enter).ok is True
    assert [a.kind for a in adapter.injected] == [
        KeyActionKind.BACKSPACE,
        KeyActionKind.ENTER,
    ]
