"""Shared session identifiers — prefer ``gazekey.runtime.session_id`` in product code."""

from __future__ import annotations

from gazekey.runtime.session_id import new_session_id

__all__ = ["new_session_id"]
