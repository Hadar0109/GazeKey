"""Exponential moving average filter for mapped gaze screen coordinates."""

from typing import Optional, Tuple


class GazeSmoother:
    """Reduce jitter so dwell can complete and hit testing stays stable."""

    def __init__(self, alpha: float = 0.35) -> None:
        self._alpha = alpha
        self._x: Optional[float] = None
        self._y: Optional[float] = None

    def reset(self) -> None:
        self._x = None
        self._y = None

    def filter(self, x: float, y: float) -> Tuple[float, float]:
        if self._x is None:
            self._x, self._y = x, y
        else:
            a = self._alpha
            self._x = a * x + (1.0 - a) * self._x
            self._y = a * y + (1.0 - a) * self._y
        return self._x, self._y
