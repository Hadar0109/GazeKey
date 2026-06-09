"""Console logging gate for the MVP calibration-mapping path (FR-015, FR-016)."""

from __future__ import annotations

import os


def mvp_verbose() -> bool:
    return os.environ.get("GAZEKEY_VERBOSE", "0").strip() == "1"


def mvp_log(message: str, *, always: bool = False) -> None:
    """Print when always=True or GAZEKEY_VERBOSE=1."""
    if always or mvp_verbose():
        print(message)
