"""5-point calibration session state machine.

This module used to collect samples for a fixed wall-clock window per dot.
That approach often produces bad fits when gaze is jittery.

Now the session supports **fixation-style gating** (lock-on + completion),
similar to how gaze-driven UIs (e.g. OptiKey) gate interactions:
- wait for gaze to become stable (lock-on)
- then collect stable samples (completion)
"""

from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Deque, List, Optional, Tuple

import numpy as np

from gazekey.calibration.gaze_features import iris_span_across_points
from gazekey.calibration.gaze_mapper import GazeMapper, fit_gaze_mapper
from gazekey.calibration.calibration_validation import validate_calibration_gaze

# Timing and validation thresholds
PREPARE_MS = 2000
COLLECT_MS = 2000

# Fixation-style gating (lock-on + completion) used by the overlay.
LOCK_ON_MS = 350
COMPLETE_MS = 650
POINT_TIMEOUT_MS = 8000

MIN_SAMPLES = 20
MAX_SPREAD_RATIO = 0.08
MAX_FIT_RMS_PX = 100.0
# After each dot (except the first), gaze ratio must shift vs previous dot mean
MIN_SHIFT_FROM_PREVIOUS = 0.012

POINT_NAMES_5 = [
    "top-left",
    "top-right",
    "center",
    "bottom-left",
    "bottom-right",
]

POINT_NAMES_9 = [
    "top-left",
    "top",
    "top-right",
    "left",
    "center",
    "right",
    "bottom-left",
    "bottom",
    "bottom-right",
]


def point_names_for_count(n: int) -> List[str]:
    if n == 5:
        return POINT_NAMES_5
    if n == 9:
        return POINT_NAMES_9
    return [f"point-{i + 1}" for i in range(n)]


class Phase(Enum):
    IDLE = auto()
    PREPARE = auto()
    COLLECT = auto()
    DONE = auto()

class CollectState(Enum):
    WAIT_LOCK = auto()
    COLLECTING = auto()


@dataclass
class CalibrationResult:
    success: bool
    message: str
    mapper: Optional[GazeMapper] = None
    screen_targets: Optional[List[Tuple[float, float]]] = None
    iris_means: Optional[List[Tuple[float, float]]] = None
    diagnostics: Optional[str] = None


def compute_calibration_targets(
    screen_x: int,
    screen_y: int,
    screen_w: int,
    screen_h: int,
    margin_ratio: float = 0.10,
) -> List[Tuple[float, float]]:
    """Return 9 screen targets in a 3x3 grid with safe margins."""
    mx = screen_w * margin_ratio
    my = screen_h * margin_ratio
    xs = [screen_x + mx, screen_x + screen_w / 2.0, screen_x + screen_w - mx]
    ys = [screen_y + my, screen_y + screen_h / 2.0, screen_y + screen_h - my]
    return [(x, y) for y in ys for x in xs]


class CalibrationSession:
    """Collects gaze-ratio samples at known screen positions and fits IDW mapper."""

    def __init__(
        self,
        screen_targets: List[Tuple[float, float]],
        frame_w: float = 640.0,
        frame_h: float = 480.0,
    ):
        if len(screen_targets) < 5:
            raise ValueError("Expected at least 5 screen targets")
        self.screen_targets = screen_targets
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.point_names = point_names_for_count(len(screen_targets))
        self._point_index = 0
        self._phase = Phase.IDLE
        self._current_samples: List[Tuple[float, float]] = []
        self._completed_iris_means: List[Tuple[float, float]] = []
        self._collect_state = CollectState.WAIT_LOCK
        self._elapsed_in_point_ms = 0.0
        self._elapsed_collect_ms = 0.0
        self._lock_window: Deque[Tuple[float, float]] = deque()
        self._lock_window_ms = 0.0

    @property
    def point_index(self) -> int:
        return self._point_index

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def current_target(self) -> Tuple[float, float]:
        return self.screen_targets[self._point_index]

    @property
    def is_finished(self) -> bool:
        return self._phase == Phase.DONE

    @property
    def point_count(self) -> int:
        return len(self.screen_targets)

    def current_point_name(self) -> str:
        return self.point_names[self._point_index]

    def reset(self) -> None:
        self._point_index = 0
        self._phase = Phase.IDLE
        self._current_samples = []
        self._completed_iris_means = []
        self._collect_state = CollectState.WAIT_LOCK
        self._elapsed_in_point_ms = 0.0
        self._elapsed_collect_ms = 0.0
        self._lock_window.clear()
        self._lock_window_ms = 0.0

    def begin_prepare(self) -> None:
        self._phase = Phase.PREPARE
        self._current_samples = []
        self._collect_state = CollectState.WAIT_LOCK
        self._elapsed_in_point_ms = 0.0
        self._elapsed_collect_ms = 0.0
        self._lock_window.clear()
        self._lock_window_ms = 0.0

    def begin_collect(self) -> None:
        self._phase = Phase.COLLECT
        self._current_samples = []
        self._collect_state = CollectState.WAIT_LOCK
        self._elapsed_in_point_ms = 0.0
        self._elapsed_collect_ms = 0.0
        self._lock_window.clear()
        self._lock_window_ms = 0.0

    def add_sample(self, gaze_h: float, gaze_v: float) -> None:
        if self._phase != Phase.COLLECT:
            return
        self._current_samples.append((gaze_h, gaze_v))

    def process_sample(
        self,
        gaze_h: float,
        gaze_v: float,
        dt_ms: float,
    ) -> Optional["CalibrationResult"]:
        """
        Fixation-gated sample ingestion used by the UI.

        Returns a CalibrationResult only when calibration finishes (success/failure).
        Otherwise returns None.
        """
        if self._phase != Phase.COLLECT:
            return None

        dt_ms_f = float(max(0.0, dt_ms))
        self._elapsed_in_point_ms += dt_ms_f
        if self._elapsed_in_point_ms > POINT_TIMEOUT_MS:
            self._phase = Phase.DONE
            idx = self._point_index + 1
            name = self.point_names[self._point_index]
            return CalibrationResult(
                success=False,
                message=(
                    f"Point {idx} ({name}): timed out waiting for a stable gaze. "
                    "Try again and keep your eyes still on the dot."
                ),
            )

        sample = (float(gaze_h), float(gaze_v))

        if self._collect_state == CollectState.WAIT_LOCK:
            self._push_lock_window(sample, dt_ms=dt_ms_f)
            if self._lock_window_ms >= LOCK_ON_MS and self._samples_are_stable(
                list(self._lock_window)
            ):
                # Ensure gaze actually moved vs previous dot (avoid re-locking on old gaze).
                mean_x = float(np.mean([s[0] for s in self._lock_window]))
                mean_y = float(np.mean([s[1] for s in self._lock_window]))
                if self._completed_iris_means:
                    prev = self._completed_iris_means[-1]
                    shift = float(np.hypot(mean_x - prev[0], mean_y - prev[1]))
                    if shift < MIN_SHIFT_FROM_PREVIOUS:
                        return None

                self._collect_state = CollectState.COLLECTING
                self._elapsed_collect_ms = 0.0
                self._current_samples = list(self._lock_window)
            return None

        # COLLECTING
        self._elapsed_collect_ms += dt_ms_f
        self._current_samples.append(sample)

        # If gaze becomes unstable, fall back to re-lock.
        if not self._samples_are_stable(self._current_samples):
            self._collect_state = CollectState.WAIT_LOCK
            self._elapsed_collect_ms = 0.0
            self._current_samples = []
            self._lock_window.clear()
            self._lock_window_ms = 0.0
            return None

        if self._elapsed_collect_ms >= COMPLETE_MS and len(self._current_samples) >= MIN_SAMPLES:
            return self.finish_collect()

        return None

    def finish_collect(self) -> Optional[CalibrationResult]:
        """Validate current point; advance or complete calibration."""
        validation = self._validate_current_point()
        if validation is not None:
            self._phase = Phase.DONE
            return validation

        idx = self._point_index + 1
        name = self.point_names[self._point_index]
        m = len(self._current_samples)
        filtered = self._filter_samples_iqr(self._current_samples)
        k = len(filtered)
        print(f"Point {idx} ({name}): IQR filter kept {k} of {m} samples.")

        if k < MIN_SAMPLES:
            self._phase = Phase.DONE
            return CalibrationResult(
                success=False,
                message=(
                    f"Point {idx} ({name}): too many unstable frames after filtering "
                    f"(kept {k} of {m}). Keep your eyes still and look directly at the dot."
                ),
            )

        mean_x = float(np.mean([s[0] for s in filtered]))
        mean_y = float(np.mean([s[1] for s in filtered]))
        self._completed_iris_means.append((mean_x, mean_y))

        self._point_index += 1
        self._current_samples = []
        self._collect_state = CollectState.WAIT_LOCK
        self._elapsed_in_point_ms = 0.0
        self._elapsed_collect_ms = 0.0
        self._lock_window.clear()
        self._lock_window_ms = 0.0

        if self._point_index >= len(self.screen_targets):
            return self._finalize()

        self._phase = Phase.IDLE
        return None

    def _push_lock_window(self, sample: Tuple[float, float], dt_ms: float) -> None:
        self._lock_window.append(sample)
        self._lock_window_ms += dt_ms
        # Cap length to avoid unbounded growth (approx. 2s at 60fps).
        while len(self._lock_window) > 120:
            self._lock_window.popleft()

    @staticmethod
    def _samples_are_stable(samples: List[Tuple[float, float]]) -> bool:
        if len(samples) < 6:
            return True
        xs = np.array([s[0] for s in samples], dtype=np.float64)
        ys = np.array([s[1] for s in samples], dtype=np.float64)
        spread = max(float(np.std(xs)), float(np.std(ys)))
        return spread <= MAX_SPREAD_RATIO

    def _validate_current_point(self) -> Optional[CalibrationResult]:
        idx = self._point_index + 1
        name = self.point_names[self._point_index]
        n = len(self._current_samples)

        if n < MIN_SAMPLES:
            return CalibrationResult(
                success=False,
                message=(
                    f"Point {idx} ({name}): only {n} samples (need at least {MIN_SAMPLES}). "
                    "Keep your head still and look at the dot."
                ),
            )

        xs = np.array([s[0] for s in self._current_samples])
        ys = np.array([s[1] for s in self._current_samples])
        spread = max(float(np.std(xs)), float(np.std(ys)))

        if spread > MAX_SPREAD_RATIO:
            return CalibrationResult(
                success=False,
                message=(
                    f"Point {idx} ({name}): gaze too unstable "
                    f"(spread {spread:.3f}, max {MAX_SPREAD_RATIO:.2f}). "
                    "Keep your head still and look at the dot."
                ),
            )

        mean_x = float(np.mean(xs))
        mean_y = float(np.mean(ys))
        if self._completed_iris_means:
            prev = self._completed_iris_means[-1]
            shift = float(np.hypot(mean_x - prev[0], mean_y - prev[1]))
            if shift < MIN_SHIFT_FROM_PREVIOUS:
                return CalibrationResult(
                    success=False,
                    message=(
                        f"Point {idx} ({name}): eyes did not move enough from the "
                        f"previous dot ({shift:.2f}). Look directly at the white dot."
                    ),
                )

        return None

    @staticmethod
    def _filter_samples_iqr(
        samples: List[Tuple[float, float]],
    ) -> List[Tuple[float, float]]:
        xs = np.array([s[0] for s in samples], dtype=np.float64)
        ys = np.array([s[1] for s in samples], dtype=np.float64)
        q1_x, q3_x = np.percentile(xs, 25), np.percentile(xs, 75)
        q1_y, q3_y = np.percentile(ys, 25), np.percentile(ys, 75)
        iqr_x = q3_x - q1_x
        iqr_y = q3_y - q1_y
        lo_x, hi_x = q1_x - 1.5 * iqr_x, q3_x + 1.5 * iqr_x
        lo_y, hi_y = q1_y - 1.5 * iqr_y, q3_y + 1.5 * iqr_y
        return [
            (x, y)
            for x, y in samples
            if lo_x <= x <= hi_x and lo_y <= y <= hi_y
        ]

    @staticmethod
    def _build_diagnostics(
        iris_means: List[Tuple[float, float]],
        pairs: Optional[List[Tuple[Tuple[float, float], Tuple[float, float]]]] = None,
        mapper: Optional[GazeMapper] = None,
    ) -> Optional[str]:
        lines: List[str] = []
        if pairs is not None and mapper is not None:
            for i, ((ix, iy), (sx, sy)) in enumerate(pairs):
                mx, my = mapper.map_point(ix, iy)
                err = float(np.hypot(mx - sx, my - sy))
                lines.append(f"  {i + 1}: {err:.0f}px")
        span_x, span_y = iris_span_across_points(iris_means)
        lines.append(
            f"Gaze range across dots: {span_x:.2f} horizontal, {span_y:.2f} vertical."
        )
        return "\n".join(lines) if lines else None

    def _finalize(self) -> CalibrationResult:
        self._phase = Phase.DONE
        pairs = list(zip(self._completed_iris_means, self.screen_targets))
        partial_diagnostics = self._build_diagnostics(self._completed_iris_means)

        gaze_error = validate_calibration_gaze(
            self._completed_iris_means,
            self.screen_targets,
            self.frame_w,
        )
        if gaze_error is not None:
            return CalibrationResult(
                success=False,
                message=gaze_error,
                diagnostics=partial_diagnostics,
            )

        fit = fit_gaze_mapper(
            pairs,
            frame_w=self.frame_w,
            frame_h=self.frame_h,
            max_rms_px=MAX_FIT_RMS_PX,
        )

        if not fit.success or fit.mapper is None:
            return CalibrationResult(
                success=False,
                message=fit.message,
                diagnostics=partial_diagnostics,
            )

        diagnostics = self._build_diagnostics(
            self._completed_iris_means,
            pairs=pairs,
            mapper=fit.mapper,
        )
        return CalibrationResult(
            success=True,
            message=fit.message,
            mapper=fit.mapper,
            screen_targets=list(self.screen_targets),
            iris_means=list(self._completed_iris_means),
            diagnostics=diagnostics,
        )
