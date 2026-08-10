"""Unit tests for TypingContext delivery-only updates (003)."""

from __future__ import annotations

from gazekey.prediction.typing_context import TypingContext
from gazekey.typing.key_action import KeyAction, KeyActionKind, KeyActionSource


def _char(text: str, *, key_id: str = "k") -> KeyAction:
    return KeyAction(
        kind=KeyActionKind.CHAR,
        text=text,
        source=KeyActionSource.MOUSE,
        key_id=key_id,
        timestamp=1.0,
    )


def _backspace() -> KeyAction:
    return KeyAction(
        kind=KeyActionKind.BACKSPACE,
        source=KeyActionSource.MOUSE,
        key_id="bs",
        timestamp=1.0,
    )


def _enter() -> KeyAction:
    return KeyAction(
        kind=KeyActionKind.ENTER,
        source=KeyActionSource.MOUSE,
        key_id="enter",
        timestamp=1.0,
    )


def test_letter_append_builds_prefix():
    ctx = TypingContext()
    for ch in "hel":
        assert ctx.on_action_delivered(_char(ch), ok=True)
    assert ctx.get_prefix() == "hel"
    assert ctx.get_epoch() == 3


def test_backspace_shortens_prefix():
    ctx = TypingContext()
    for ch in "hel":
        ctx.on_action_delivered(_char(ch), ok=True)
    epoch = ctx.get_epoch()
    assert ctx.on_action_delivered(_backspace(), ok=True)
    assert ctx.get_prefix() == "he"
    assert ctx.get_epoch() == epoch + 1


def test_space_clears_prefix():
    ctx = TypingContext()
    for ch in "hi":
        ctx.on_action_delivered(_char(ch), ok=True)
    assert ctx.on_action_delivered(_char(" "), ok=True)
    assert ctx.get_prefix() == ""


def test_enter_clears_prefix():
    ctx = TypingContext()
    ctx.on_action_delivered(_char("a"), ok=True)
    assert ctx.on_action_delivered(_enter(), ok=True)
    assert ctx.get_prefix() == ""


def test_failed_inject_leaves_prefix_unchanged():
    ctx = TypingContext()
    ctx.on_action_delivered(_char("h"), ok=True)
    epoch = ctx.get_epoch()
    assert ctx.on_action_delivered(_char("e"), ok=False) is False
    assert ctx.get_prefix() == "h"
    assert ctx.get_epoch() == epoch


def test_suggestion_suffix_and_space_clear_via_delivery_only():
    """hel + accept hello → deliveries l,o,Space → empty prefix; no extra clear."""
    ctx = TypingContext()
    for ch in "hel":
        ctx.on_action_delivered(_char(ch), ok=True)
    assert ctx.get_prefix() == "hel"
    ctx.on_action_delivered(_char("l"), ok=True)
    ctx.on_action_delivered(_char("o"), ok=True)
    assert ctx.get_prefix() == "hello"
    ctx.on_action_delivered(_char(" "), ok=True)
    assert ctx.get_prefix() == ""
