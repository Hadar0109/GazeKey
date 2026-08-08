"""Runtime session id helper (product — not an artifact writer)."""

from __future__ import annotations

import uuid


def new_session_id() -> str:
    """Return a short unique id for correlating a calibration session."""
    return uuid.uuid4().hex[:12]
