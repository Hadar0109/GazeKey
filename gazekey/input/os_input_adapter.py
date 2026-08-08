"""OsInputAdapter protocol and test fake (contracts/os-input.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Protocol

from gazekey.typing.key_action import KeyAction


@dataclass(frozen=True)
class OsInjectResult:
    """Delivery outcome from an OS inject attempt."""

    ok: bool
    error: Optional[str] = None


class OsInputAdapter(Protocol):
    """Boundary between requested KeyAction and native OS input."""

    def inject(self, action: KeyAction) -> OsInjectResult:
        """Attempt to deliver ``action`` to the focused OS target."""


@dataclass
class FakeOsInputAdapter:
    """In-memory adapter for unit tests — never touches the OS."""

    fail: bool = False
    error: str = "fake_failure"
    injected: List[KeyAction] = field(default_factory=list)

    def inject(self, action: KeyAction) -> OsInjectResult:
        self.injected.append(action)
        if self.fail:
            return OsInjectResult(ok=False, error=self.error)
        return OsInjectResult(ok=True)
