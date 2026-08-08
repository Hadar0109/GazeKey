"""Centralized product ``GAZEKEY_*`` environment flag reads.

Developer-only flags live in ``tools.flags`` (``DEV_BENCHMARK``, ``CALIB_GEOM_DEBUG``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def env_bool(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def env_str(name: str, *, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def verbose() -> bool:
    return env_bool("GAZEKEY_VERBOSE")


def camera_preview_during_calib() -> bool:
    """Allow the standard camera preview window during fixation (default off)."""
    return env_bool("GAZEKEY_CAMERA_PREVIEW_DURING_CALIB")


def calib_mode_override() -> str:
    """Optional layout override — preserved / re-evaluate (may become tools-only later)."""
    return env_str("GAZEKEY_CALIB_MODE")


def gaze_debug() -> bool:
    """Extra gaze debug labels — preserved / re-evaluate."""
    return env_bool("GAZEKEY_GAZE_DEBUG")


def calib_debug() -> bool:
    """Verbose calibration overlay — preserved / re-evaluate."""
    return env_bool("GAZEKEY_CALIB_DEBUG")


def verbose_fixation_ui() -> bool:
    return verbose() or calib_debug()


@dataclass(frozen=True)
class EnvFlags:
    """Snapshot of product UI runtime flags (read once at VirtualKeyboard init)."""

    verbose: bool
    rt2_debug: bool
    calib_debug: bool

    @classmethod
    def load(cls) -> EnvFlags:
        v = verbose()
        return cls(
            verbose=v,
            rt2_debug=v or gaze_debug(),
            calib_debug=v or calib_debug(),
        )
