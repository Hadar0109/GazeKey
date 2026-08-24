"""Developer calibration artifact writers (legacy PCA path removed in Stage G).

Kept as a no-op host so ``tools.devtools_install`` still constructs DevTools.
"""

from __future__ import annotations

from typing import Any, Optional


class CalibFinishArtifacts:
    """No-op: GazeFollower production does not write PCA mapper snapshots."""

    def __init__(self, host: Any, *, runs_dir: Any) -> None:
        self._host = host
        self._runs_dir = runs_dir

    def write_run_summary(self, writer: Any, **kwargs: Any) -> None:
        del writer, kwargs

    def write_mapper_snapshot(self, **kwargs: Any) -> None:
        del kwargs

    def on_success(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs

    def on_failure(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs

    def reset_debug_csvs(self) -> None:
        return
