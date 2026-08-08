"""Product runtime flags — reads process :mod:`gazekey.app_config` (CLI boundary).

No ``GAZEKEY_*`` environment-variable fallback.
"""

from __future__ import annotations

from dataclasses import dataclass

from gazekey.app_config import (
    effective_calib_debug,
    effective_rt2_debug,
    get_config,
)


def verbose() -> bool:
    return get_config().verbose


def camera_preview_during_calib() -> bool:
    """Allow the standard camera preview window during fixation (default off)."""
    return get_config().camera_preview_during_calib


def calib_mode_override() -> str:
    """Optional layout override from ``--calib-mode`` (empty → mapping default)."""
    return get_config().calib_mode


def gaze_debug() -> bool:
    return get_config().gaze_debug


def calib_debug() -> bool:
    return get_config().calib_debug


def verbose_fixation_ui() -> bool:
    return effective_calib_debug()


@dataclass(frozen=True)
class EnvFlags:
    """Snapshot of product UI runtime flags (read once at VirtualKeyboard init)."""

    verbose: bool
    rt2_debug: bool
    calib_debug: bool

    @classmethod
    def load(cls) -> EnvFlags:
        cfg = get_config()
        return cls(
            verbose=cfg.verbose,
            rt2_debug=effective_rt2_debug(cfg),
            calib_debug=effective_calib_debug(cfg),
        )
