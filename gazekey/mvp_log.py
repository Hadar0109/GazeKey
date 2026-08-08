"""Console logging gate for the MVP calibration-mapping path (FR-015, FR-016)."""

from __future__ import annotations

from gazekey.app_config import get_config


def mvp_verbose() -> bool:
    return get_config().verbose


def mvp_log(message: str, *, always: bool = False) -> None:
    """Print when always=True or ``--verbose`` was set at launch."""
    if always or mvp_verbose():
        print(message)
