"""5-point calibration session state machine."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

import numpy as np

from gazekey.calibration.gaze_mapper import GazeMapper, fit_gaze_mapper
from gazekey.calibration.calibration_validation import validate_calibration_gaze

# Timing and validation thresholds
PREPARE_MS = 2000
COLLECT_MS = 2000
MIN_SAMPLES = 20
MAX_SPREAD_PX = 15.0
MAX_FIT_RMS_PX = 100.0
# After each dot (except the first), iris must shift vs previous dot mean
MIN_SHIFT_FROM_PREVIOUS_PX = 4.0

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
    """Collects iris samples at known screen positions and fits affine model."""

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

    def add_sample(self, iris_x: float, iris_y: float) -> None:
        if self._phase != Phase.COLLECT:
            return
        self._current_samples.append((iris_x, iris_y))

    def finish_collect(self) -> Optional[CalibrationResult]:
        """Validate current point; advance or complete calibration."""
        validation = self._validate_current_point()
        if validation is not None:
            self._phase = Phase.DONE
            return validation

        mean_x = float(np.mean([s[0] for s in self._current_samples]))
        mean_y = float(np.mean([s[1] for s in self._current_samples]))
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

        if spread > MAX_SPREAD_PX:
            return CalibrationResult(
                success=False,
                message=(
                    f"Point {idx} ({name}): iris position too unstable "
                    f"(spread {spread:.1f} px, max {MAX_SPREAD_PX:.0f} px)."
                ),
            )

        mean_x = float(np.mean(xs))
        mean_y = float(np.mean(ys))
        if self._completed_iris_means:
            prev = self._completed_iris_means[-1]
            shift = float(np.hypot(mean_x - prev[0], mean_y - prev[1]))
            if shift < MIN_SHIFT_FROM_PREVIOUS_PX:
                return CalibrationResult(
                    success=False,
                    message=(
                        f"Point {idx} ({name}): eyes did not move enough from the "
                        f"previous dot ({shift:.1f}px). Look directly at the white dot."
                    ),
                )

        return None

    def _finalize(self) -> CalibrationResult:
        self._phase = Phase.DONE
        pairs = list(zip(self._completed_iris_means, self.screen_targets))

        gaze_error = validate_calibration_gaze(
            self._completed_iris_means,
            self.screen_targets,
            self.frame_w,
        )
        if gaze_error is not None:
            return CalibrationResult(success=False, message=gaze_error)

        fit = fit_gaze_mapper(
            pairs,
            frame_w=self.frame_w,
            frame_h=self.frame_h,
            max_rms_px=MAX_FIT_RMS_PX,
        )

        if not fit.success or fit.mapper is None:
            return CalibrationResult(success=False, message=fit.message)

        return CalibrationResult(
            success=True,
            message=fit.message,
            mapper=fit.mapper,
            screen_targets=list(self.screen_targets),
            iris_means=list(self._completed_iris_means),
        )

    @staticmethod
    def _format_fit_diagnostics(
        pairs: list,
        mapper: GazeMapper,
        base_message: str,
    ) -> str:
        """Append per-point errors to help diagnose inconsistent mappings."""
        lines = [base_message, "Per-point screen error (pixels):"]
        for i, ((ix, iy), (sx, sy)) in enumerate(pairs):
            mx, my = mapper.map_point(ix, iy)
            err = float(np.hypot(mx - sx, my - sy))
            name = POINT_NAMES[i]
            lines.append(f"  {i + 1} ({name}): {err:.0f}px")
        span_x, span_y = iris_span_across_points([p[0] for p in pairs])
        lines.append(
            f"Iris range in camera: {span_x:.1f}px wide, {span_y:.1f}px tall."
        )
        return "\n".join(lines)
