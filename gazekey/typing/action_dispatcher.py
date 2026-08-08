"""ActionDispatcher — requested vs delivered KeyAction semantics."""

from __future__ import annotations

from typing import Callable, List

from gazekey.input.os_input_adapter import OsInjectResult, OsInputAdapter
from gazekey.typing.key_action import KeyAction

OnActionRequested = Callable[[KeyAction], None]
OnActionDelivered = Callable[[KeyAction, OsInjectResult], None]


class ActionDispatcher:
    """Publish KeyActions: notify requested → inject → notify delivered."""

    def __init__(self, adapter: OsInputAdapter) -> None:
        self._adapter = adapter
        self._on_requested: List[OnActionRequested] = []
        self._on_delivered: List[OnActionDelivered] = []

    def on_action_requested(self, callback: OnActionRequested) -> None:
        """Register an observer for selection/request (before inject)."""
        self._on_requested.append(callback)

    def on_action_delivered(self, callback: OnActionDelivered) -> None:
        """Register an observer for delivery outcome (after inject)."""
        self._on_delivered.append(callback)

    def publish(self, action: KeyAction) -> OsInjectResult:
        """Notify requested, inject via adapter, then notify delivered."""
        for callback in list(self._on_requested):
            callback(action)
        result = self._adapter.inject(action)
        for callback in list(self._on_delivered):
            callback(action, result)
        return result
