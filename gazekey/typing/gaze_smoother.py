"""Exponential moving average filter for mapped gaze screen coordinates."""

import math
from typing import Optional, Tuple

_FAST_ALPHA = 0.55
_SLOW_ALPHA = 0.18
_ADAPTIVE_DELTA_PX = 80.0


class GazeSmoother:
    """Reduce jitter so dwell can complete and hit testing stays stable."""

    def __init__(self, alpha: float = 0.35) -> None:
        self._default_alpha = alpha
        self._x: Optional[float] = None
        self._y: Optional[float] = None

    def reset(self) -> None:
        self._x = None
        self._y = None

    def _adaptive_alpha(self, x: float, y: float) -> float:
        if self._x is None:
            return self._default_alpha
        delta = math.hypot(x - self._x, y - self._y)
        return _FAST_ALPHA if delta > _ADAPTIVE_DELTA_PX else _SLOW_ALPHA

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        if self._x is None:
            self._x, self._y = x, y
        else:
            a = self._adaptive_alpha(x, y)
            self._x = a * x + (1.0 - a) * self._x
            self._y = a * y + (1.0 - a) * self._y
        return self._x, self._y

    def filter_or_reject(
        self,
        x: float,
        y: float,
        is_blinking: bool,
    ) -> Tuple[float, float]:
        if is_blinking and self._x is not None and self._y is not None:
            return self._x, self._y
        return self.filter(x, y)
