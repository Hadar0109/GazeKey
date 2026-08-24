"""Process-wide runtime configuration (CLI → config boundary).

Entry points parse ``argparse`` once and call :func:`apply_config`. Runtime
modules read :func:`get_config` only — no ``os.environ`` / ``GAZEKEY_*`` fallback.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class AppConfig:
    """Immutable snapshot of launch options."""

    verbose: bool = False
    calib_mode: str = ""  # tools-only leftover; not a product flag
    calib_debug: bool = False
    gaze_debug: bool = False
    camera_preview_during_calib: bool = False  # unused on product; tools leftover
    calib_geom_debug: bool = False  # tools CLI only
    auto_benchmark: bool = False  # True only for ``python -m tools.evaluation``


_CONFIG = AppConfig()


def get_config() -> AppConfig:
    return _CONFIG


def apply_config(config: AppConfig) -> None:
    global _CONFIG
    _CONFIG = config


def reset_config() -> None:
    """Restore defaults (tests)."""
    apply_config(AppConfig())


def effective_rt2_debug(cfg: AppConfig | None = None) -> bool:
    c = cfg if cfg is not None else get_config()
    return bool(c.verbose or c.gaze_debug)


def effective_calib_debug(cfg: AppConfig | None = None) -> bool:
    c = cfg if cfg is not None else get_config()
    return bool(c.verbose or c.calib_debug)


def _add_shared_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Detailed calibration/runtime console logs",
    )
    parser.add_argument(
        "--calib-debug",
        action="store_true",
        help="Verbose official-calibration logs",
    )
    parser.add_argument(
        "--gaze-debug",
        action="store_true",
        help="Extra mapped-gaze debug labels on preview",
    )


def _add_tools_options(parser: argparse.ArgumentParser) -> None:
    _add_shared_options(parser)
    parser.add_argument(
        "--calib-mode",
        metavar="MODE",
        default="",
        help="Historical layout label for tools records (not a product mapper)",
    )
    parser.add_argument(
        "--camera-preview-during-calib",
        action="store_true",
        help="Unused on the GazeFollower product path (tools leftover)",
    )
    parser.add_argument(
        "--calib-geom-debug",
        action="store_true",
        help="Post-fit train/LOOCV geometry overlay (tools only)",
    )


def _config_from_ns(ns: argparse.Namespace, *, auto_benchmark: bool) -> AppConfig:
    return AppConfig(
        verbose=bool(getattr(ns, "verbose", False)),
        calib_mode=str(getattr(ns, "calib_mode", "") or "").strip(),
        calib_debug=bool(getattr(ns, "calib_debug", False)),
        gaze_debug=bool(getattr(ns, "gaze_debug", False)),
        camera_preview_during_calib=bool(
            getattr(ns, "camera_preview_during_calib", False)
        ),
        calib_geom_debug=bool(getattr(ns, "calib_geom_debug", False)),
        auto_benchmark=bool(auto_benchmark),
    )


def parse_product_args(argv: list[str] | None = None) -> AppConfig:
    """CLI for ``python main.py``."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="GazeKey product: official GazeFollower calibration → typing",
    )
    _add_shared_options(parser)
    ns = parser.parse_args(argv)
    return _config_from_ns(ns, auto_benchmark=False)


def parse_preview_args(argv: list[str] | None = None) -> AppConfig:
    """CLI for ``python -m tools.preview``."""
    parser = argparse.ArgumentParser(
        prog="python -m tools.preview",
        description="GazeKey developer mapped-gaze preview",
    )
    _add_tools_options(parser)
    ns = parser.parse_args(argv)
    return _config_from_ns(ns, auto_benchmark=False)


def parse_evaluation_args(argv: list[str] | None = None) -> AppConfig:
    """CLI for ``python -m tools.evaluation`` (implies auto-benchmark)."""
    parser = argparse.ArgumentParser(
        prog="python -m tools.evaluation",
        description="GazeKey developer benchmark/evaluation",
    )
    _add_tools_options(parser)
    ns = parser.parse_args(argv)
    return _config_from_ns(ns, auto_benchmark=True)


def with_overrides(**kwargs) -> AppConfig:
    """Return a copy of the current config with fields replaced (tests)."""
    return replace(get_config(), **kwargs)
