"""Developer-tooling flags — reads process :mod:`gazekey.app_config` (CLI boundary).

No ``GAZEKEY_*`` environment-variable fallback. Evaluation entry sets
``auto_benchmark=True``; ``--calib-geom-debug`` is independent of verbose/calib-debug.
"""

from __future__ import annotations

from gazekey.app_config import get_config


def auto_benchmark_enabled() -> bool:
    """True when launched via ``python -m tools.evaluation`` (entry implies evaluation)."""
    return get_config().auto_benchmark


# Back-compat alias for call sites / tests still using the old name.
def dev_benchmark_enabled() -> bool:
    return auto_benchmark_enabled()


def calib_geom_debug() -> bool:
    """Post-fit geometry overlay — tools ``--calib-geom-debug`` only."""
    return get_config().calib_geom_debug
