"""Suggestion accept → sequential CHAR suffix + Space via ActionDispatcher."""

from __future__ import annotations

from typing import Callable, Sequence

from gazekey.input.os_input_adapter import OsInjectResult
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.key_action import KeyAction, KeyActionKind, KeyActionSource
from gazekey.typing.typing_session import TypingSession


def compute_suggestion_suffix(prefix: str, word: str) -> str:
    """Return lowercase suffix to dispatch (may be empty if word == prefix)."""
    p = (prefix or "").lower()
    w = (word or "").lower()
    if not w.startswith(p):
        return ""
    return w[len(p) :]


def dispatch_suggestion_completion(
    *,
    word: str,
    prefix: str,
    accept_epoch: int,
    current_epoch: int,
    dispatcher: ActionDispatcher,
    session: TypingSession,
    source: KeyActionSource = KeyActionSource.DWELL,
    key_id: str = "suggestion:0",
    clock: Callable[[], float],
) -> Sequence[KeyAction]:
    """
    Dispatch suffix CHAR* + Space through existing ActionDispatcher.

    - Stale epoch → no dispatch.
    - Shift armed + non-empty lowercase prefix → clear Shift; do not apply to suffix.
    - Stop on first delivery failure; context evolves only via deliveries.
    """
    if int(accept_epoch) != int(current_epoch):
        return []

    suffix = compute_suggestion_suffix(prefix, word)
    # Prefer v1 Shift rule (research R5): non-empty prefix → clear without applying.
    if session.shift_oneshot_armed and prefix:
        session.clear_shift()

    published: list[KeyAction] = []
    timestamp = float(clock())

    for ch in suffix:
        action = KeyAction(
            kind=KeyActionKind.CHAR,
            text=ch.lower(),
            source=source,
            key_id=key_id,
            timestamp=timestamp,
        )
        result: OsInjectResult = dispatcher.publish(action)
        published.append(action)
        if not result.ok:
            return published

    space = KeyAction(
        kind=KeyActionKind.CHAR,
        text=" ",
        source=source,
        key_id=key_id,
        timestamp=timestamp,
    )
    result = dispatcher.publish(space)
    published.append(space)
    if not result.ok:
        return published
    return published
