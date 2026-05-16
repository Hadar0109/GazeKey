"""
Gaze mapping from eye-relative gaze ratios to screen pixels.

Uses inverse-distance interpolation between the five calibration points (same
screen targets as before). Gaze features are horizontal/vertical ratios within
each eye socket (GazeTracking-style), not raw iris pixels.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np

from gazekey.calibration.affine_mapper import AffineGazeMapper

PointPair = Tuple[Tuple[float, float], Tuple[float, float]]

GazeMapper = Union[AffineGazeMapper, "InterpolationGazeMapper"]

FEATURE_GAZE_RATIO = "gaze_ratio"
MIN_GAZE_SPREAD = 0.015
IDW_POWER = 2.0
IDW_EPS = 1e-6


@dataclass
class FitResult:
    success: bool
    message: str
    mapper: Optional[GazeMapper] = None


class InterpolationGazeMapper:
    """
    Map gaze by weighting the five calibration points by inverse distance
    in gaze-ratio space (Shepard interpolation).
    """

    EXTRAPOLATION_WARNING_PX = 50.0

    def __init__(
        self,
        iris_points: List[Tuple[float, float]],
        screen_points: List[Tuple[float, float]],
        flip_x: bool = False,
        frame_w: float = 640.0,
        feature: str = FEATURE_GAZE_RATIO,
    ):
        if len(iris_points) != 5 or len(screen_points) != 5:
            raise ValueError("Expected 5 calibration points")
        self.iris_points = [tuple(p) for p in iris_points]
        self.screen_points = [tuple(p) for p in screen_points]
        self.flip_x = flip_x
        self.frame_w = float(frame_w)
        self.feature = feature
        sx = [p[0] for p in screen_points]
        sy = [p[1] for p in screen_points]
        self.screen_x_min = float(min(sx))
        self.screen_x_max = float(max(sx))
        self.screen_y_min = float(min(sy))
        self.screen_y_max = float(max(sy))
        self._warn_frame_counter = 0

    @property
    def model_type(self) -> str:
        return "interpolation"

    def _gaze_for_lookup(self, gaze_h: float, gaze_v: float) -> Tuple[float, float]:
        gh = gaze_h
        if self.flip_x:
            gh = 1.0 - gh
        return gh, gaze_v

    def map_point(self, gaze_h: float, gaze_v: float) -> Tuple[float, float]:
        gh, gv = self._gaze_for_lookup(gaze_h, gaze_v)
        weights = []
        for i, (px, py) in enumerate(self.iris_points):
            d = np.hypot(gh - px, gv - py)
            if d < IDW_EPS:
                return self.screen_points[i]
            weights.append(1.0 / (d**IDW_POWER))

        w_sum = sum(weights)
        sx_unclipped = sum(
            w * self.screen_points[i][0] for i, w in enumerate(weights)
        ) / w_sum
        sy_unclipped = sum(
            w * self.screen_points[i][1] for i, w in enumerate(weights)
        ) / w_sum
        sx = float(np.clip(sx_unclipped, self.screen_x_min, self.screen_x_max))
        sy = float(np.clip(sy_unclipped, self.screen_y_min, self.screen_y_max))
        dx = abs(sx_unclipped - sx)
        dy = abs(sy_unclipped - sy)
        if (
            dx > self.EXTRAPOLATION_WARNING_PX
            or dy > self.EXTRAPOLATION_WARNING_PX
        ):
            self._warn_frame_counter += 1
            if self._warn_frame_counter >= 60:
                self._warn_frame_counter = 0
                print(
                    f"GazeMapper: gaze extrapolated {dx:.0f}px/{dy:.0f}px "
                    "beyond calibration bounds."
                )
        return sx, sy

    def rms_on_pairs(self, pairs: Sequence[PointPair]) -> float:
        errors = []
        for (gh, gv), (sx, sy) in pairs:
            mx, my = self.map_point(gh, gv)
            errors.append(np.hypot(mx - sx, my - sy))
        return float(np.sqrt(np.mean(np.array(errors) ** 2)))

    @staticmethod
    def _gaze_spread(gaze_points: List[Tuple[float, float]]) -> float:
        xs = [p[0] for p in gaze_points]
        ys = [p[1] for p in gaze_points]
        return max(max(xs) - min(xs), max(ys) - min(ys))

    @classmethod
    def fit_best(
        cls,
        pairs: Sequence[PointPair],
        frame_w: float,
        frame_h: float,
        max_rms_px: float = 80.0,
    ) -> FitResult:
        del frame_h, max_rms_px, frame_w  # ratios: flip via 1-h, not frame width

        if len(pairs) < 5:
            return FitResult(
                success=False,
                message=f"Calibration fit failed: need 5 points, got {len(pairs)}.",
            )

        best_mapper: Optional[InterpolationGazeMapper] = None
        best_rms = float("inf")

        for flip_x in (False, True):
            gaze_pts = []
            screen_pts = []
            for (gh, gv), (sx, sy) in pairs:
                gh_use = (1.0 - gh) if flip_x else gh
                gaze_pts.append((gh_use, gv))
                screen_pts.append((sx, sy))

            spread = cls._gaze_spread(gaze_pts)
            if spread < MIN_GAZE_SPREAD:
                continue

            mapper = cls(
                gaze_pts,
                screen_pts,
                flip_x=flip_x,
                feature=FEATURE_GAZE_RATIO,
            )
            rms = mapper.rms_on_pairs(pairs)
            if rms < best_rms:
                best_rms = rms
                best_mapper = mapper

        if best_mapper is None:
            return FitResult(
                success=False,
                message=(
                    "Calibration failed: gaze barely changed at all five dots. "
                    "Move only your eyes farther toward each corner."
                ),
            )

        return FitResult(
            success=True,
            message="Calibration successful.",
            mapper=best_mapper,
        )

    @classmethod
    def from_dict(cls, data: dict) -> Optional["InterpolationGazeMapper"]:
        model = data.get("model", "")
        feature = data.get("feature", "")
        if feature != FEATURE_GAZE_RATIO:
            return None
        if model not in ("interpolation", "separate_linear", "normalized_affine", "quadratic"):
            if "iris_points" not in data:
                return None
        try:
            iris_points = [tuple(p) for p in data["iris_points"]]
            screen_points = [tuple(p) for p in data["screen_points"]]
            if len(iris_points) != 5 or len(screen_points) != 5:
                return None
            return cls(
                iris_points,
                screen_points,
                flip_x=bool(data.get("flip_x", False)),
                frame_w=float(data.get("frame_w", 640)),
                feature=FEATURE_GAZE_RATIO,
            )
        except (KeyError, TypeError, ValueError):
            return None

    def to_dict(self) -> dict:
        return {
            "model": self.model_type,
            "feature": self.feature,
            "iris_points": [list(p) for p in self.iris_points],
            "screen_points": [list(p) for p in self.screen_points],
            "flip_x": self.flip_x,
            "frame_w": self.frame_w,
        }


# Aliases
SeparateLinearGazeMapper = InterpolationGazeMapper
NormalizedGazeMapper = InterpolationGazeMapper
QuadraticGazeMapper = InterpolationGazeMapper


def fit_gaze_mapper(
    pairs: Sequence[PointPair],
    frame_w: float,
    frame_h: float,
    max_rms_px: float = 80.0,
) -> FitResult:
    return InterpolationGazeMapper.fit_best(
        pairs, frame_w=frame_w, frame_h=frame_h, max_rms_px=max_rms_px
    )
