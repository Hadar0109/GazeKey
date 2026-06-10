"""Centralized GAZEKEY_* environment flag reads for the UI layer (T050)."""

from __future__ import annotations

import os
from dataclasses import dataclass


def env_bool(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def env_str(name: str, *, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def verbose() -> bool:
    return env_bool("GAZEKEY_VERBOSE")


def dev_benchmark_enabled() -> bool:
    return env_bool("GAZEKEY_DEV_BENCHMARK")


def camera_preview_during_calib() -> bool:
    """Allow the standard camera preview window during fixation (default off — CQ-4)."""
    return env_bool("GAZEKEY_CAMERA_PREVIEW_DURING_CALIB")


def calib_mode_override() -> str:
    return env_str("GAZEKEY_CALIB_MODE")


def selection_debug() -> bool:
    return env_bool("GAZEKEY_SELECTION_DEBUG")


def gaze_debug() -> bool:
    return env_bool("GAZEKEY_GAZE_DEBUG")


def gaze_debug_pred() -> bool:
    return env_bool("GAZEKEY_GAZE_DEBUG_PRED")


def gaze_debug_selection() -> bool:
    return env_bool("GAZEKEY_GAZE_DEBUG_SELECTION")


def calib_debug() -> bool:
    return env_bool("GAZEKEY_CALIB_DEBUG")


def calib_geom_debug(*, calib_debug_cached: bool = False) -> bool:
    return calib_debug_cached or env_bool("GAZEKEY_CALIB_GEOM_DEBUG")


def verbose_fixation_ui() -> bool:
    return verbose() or calib_debug()


@dataclass(frozen=True)
class EnvFlags:
    """Snapshot of UI runtime flags (typically read once at VirtualKeyboard init)."""

    verbose: bool
    selection_debug: bool
    rt2_debug: bool
    rt2_debug_pred: bool
    rt2_debug_selection: bool
    calib_debug: bool

    @classmethod
    def load(cls) -> EnvFlags:
        v = verbose()
        rt2 = v or gaze_debug()
        return cls(
            verbose=v,
            selection_debug=selection_debug(),
            rt2_debug=rt2,
            rt2_debug_pred=rt2 or gaze_debug_pred(),
            rt2_debug_selection=v or gaze_debug_selection(),
            calib_debug=v or calib_debug(),
        )
