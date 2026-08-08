"""Developer-tooling environment flags (not product defaults).

Product ``gazekey.ui.env_flags`` must not own these. Tools entry points and
artifact writers read them here.
"""

from __future__ import annotations

import os


def env_bool(name: str, *, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def dev_benchmark_enabled() -> bool:
    """Auto-start 15-key benchmark after tools calib+preview (``GAZEKEY_DEV_BENCHMARK=1``)."""
    return env_bool("GAZEKEY_DEV_BENCHMARK")


def calib_geom_debug(*, calib_debug_cached: bool = False) -> bool:
    """Post-fit geometry overlay for tools sessions (``GAZEKEY_CALIB_GEOM_DEBUG=1``).

    ``calib_debug_cached`` may mirror the product host's ``CALIB_DEBUG`` snapshot when
    tools are attached; product itself does not read ``CALIB_GEOM_DEBUG``.
    """
    return bool(calib_debug_cached) or env_bool("GAZEKEY_CALIB_GEOM_DEBUG")
