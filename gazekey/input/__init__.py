"""OS input boundary — adapters only; pynput stays behind this package."""

from gazekey.input.os_input_adapter import FakeOsInputAdapter, OsInjectResult, OsInputAdapter

__all__ = [
    "FakeOsInputAdapter",
    "OsInjectResult",
    "OsInputAdapter",
]
