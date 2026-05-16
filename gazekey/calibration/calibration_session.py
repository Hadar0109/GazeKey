"""5-point calibration session state machine."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

import numpy as np

from gazekey.calibration.gaze_features import iris_span_across_points
from gazekey.calibration.gaze_mapper import GazeMapper, fit_gaze_mapper
from gazekey.calibration.calibration_validation import validate_calibration_gaze

# Timing and validation thresholds
PREPARE_MS = 2000
COLLECT_MS = 2000
MIN_SAMPLES = 20
MAX_SPREAD_RATIO = 0.08
MAX_FIT_RMS_PX = 100.0
# After each dot (except the first), gaze ratio must shift vs previous dot mean
MIN_SHIFT_FROM_PREVIOUS = 0.012

POINT_NAMES = [
    "top-left",
    "top-right",
    "center",
    "bottom-left",
    "bottom-right",
]


class Phase(Enum):
    IDLE = auto()
    PREPARE = auto()
    COLLECT = auto()
    DONE = auto()


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
    """Return 5 screen targets: TL, TR, center, BL, BR with safe margins."""
    mx = screen_w * margin_ratio
    my = screen_h * margin_ratio
    return [
        (screen_x + mx, screen_y + my),
        (screen_x + screen_w - mx, screen_y + my),
        (screen_x + screen_w / 2.0, screen_y + screen_h / 2.0),
        (screen_x + mx, screen_y + screen_h - my),
        (screen_x + screen_w - mx, screen_y + screen_h - my),
    ]


class CalibrationSession:
    """Collects gaze-ratio samples at known screen positions and fits IDW mapper."""

    def __init__(
        self,
        screen_targets: List[Tuple[float, float]],
        frame_w: float = 640.0,
        frame_h: float = 480.0,
    ):
        if len(screen_targets) != 5:
            raise ValueError("Expected exactly 5 screen targets")
        self.screen_targets = screen_targets
        self.frame_w = frame_w
        self.frame_h = frame_h
        self._point_index = 0
        self._phase = Phase.IDLE
        self._current_samples: List[Tuple[float, float]] = []
        self._completed_iris_means: List[Tuple[float, float]] = []

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
        return len(POINT_NAMES)

    def current_point_name(self) -> str:
        return POINT_NAMES[self._point_index]

    def reset(self) -> None:
        self._point_index = 0
        self._phase = Phase.IDLE
        self._current_samples = []
        self._completed_iris_means = []

    def begin_prepare(self) -> None:
        self._phase = Phase.PREPARE
        self._current_samples = []

    def begin_collect(self) -> None:
        self._phase = Phase.COLLECT
        self._current_samples = []

    def add_sample(self, gaze_h: float, gaze_v: float) -> None:
        if self._phase != Phase.COLLECT:
            return
        self._current_samples.append((gaze_h, gaze_v))

    def finish_collect(self) -> Optional[CalibrationResult]:
        """Validate current point; advance or complete calibration."""
        validation = self._validate_current_point()
        if validation is not None:
            self._phase = Phase.DONE
            return validation

        idx = self._point_index + 1
        name = POINT_NAMES[self._point_index]
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

        if self._point_index >= 5:
            return self._finalize()

        self._phase = Phase.IDLE
        return None

    def _validate_current_point(self) -> Optional[CalibrationResult]:
        idx = self._point_index + 1
        name = POINT_NAMES[self._point_index]
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
                lines.append(f"  {i + 1} ({POINT_NAMES[i]}): {err:.0f}px")
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
