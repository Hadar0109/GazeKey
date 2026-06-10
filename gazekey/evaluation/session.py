"""Shared session identifiers for calibration and benchmark runs."""

from __future__ import annotations

import uuid


def new_session_id() -> str:
    """Return a short unique id for a calibration or benchmark run."""
    return uuid.uuid4().hex[:12]
