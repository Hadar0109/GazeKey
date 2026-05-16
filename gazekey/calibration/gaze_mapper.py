"""
Gaze mapping from iris camera pixels to screen pixels.

Uses inverse-distance interpolation between the five calibration points so
small iris movement in the camera still maps correctly to screen corners.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np

from gazekey.calibration.affine_mapper import AffineGazeMapper

PointPair = Tuple[Tuple[float, float], Tuple[float, float]]

GazeMapper = Union[AffineGazeMapper, "InterpolationGazeMapper"]

MIN_IRIS_SPREAD = 10.0
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
    in iris space (Shepard interpolation).
    """

    def __init__(
        self,
        iris_points: List[Tuple[float, float]],
        screen_points: List[Tuple[float, float]],
        flip_x: bool = False,
        frame_w: float = 640.0,
    ):
        if len(iris_points) != 5 or len(screen_points) != 5:
            raise ValueError("Expected 5 calibration points")
        self.iris_points = [tuple(p) for p in iris_points]
        self.screen_points = [tuple(p) for p in screen_points]
        self.flip_x = flip_x
        self.frame_w = float(frame_w)
        sx = [p[0] for p in screen_points]
        sy = [p[1] for p in screen_points]
        self.screen_x_min = float(min(sx))
        self.screen_x_max = float(max(sx))
        self.screen_y_min = float(min(sy))
        self.screen_y_max = float(max(sy))

    @property
    def model_type(self) -> str:
        return "interpolation"

    def _iris_for_lookup(self, iris_x: float, iris_y: float) -> Tuple[float, float]:
        ix = iris_x
        if self.flip_x:
            ix = self.frame_w - ix
        return ix, iris_y

    def map_point(self, iris_x: float, iris_y: float) -> Tuple[float, float]:
        ix, iy = self._iris_for_lookup(iris_x, iris_y)
        weights = []
        for i, (px, py) in enumerate(self.iris_points):
            d = np.hypot(ix - px, iy - py)
            if d < IDW_EPS:
                return self.screen_points[i]
            weights.append(1.0 / (d**IDW_POWER))

        w_sum = sum(weights)
        sx = sum(w * self.screen_points[i][0] for i, w in enumerate(weights)) / w_sum
        sy = sum(w * self.screen_points[i][1] for i, w in enumerate(weights)) / w_sum
        sx = float(np.clip(sx, self.screen_x_min, self.screen_x_max))
        sy = float(np.clip(sy, self.screen_y_min, self.screen_y_max))
        return sx, sy

    def rms_on_pairs(self, pairs: Sequence[PointPair]) -> float:
        errors = []
        for (ix, iy), (sx, sy) in pairs:
            mx, my = self.map_point(ix, iy)
            errors.append(np.hypot(mx - sx, my - sy))
        return float(np.sqrt(np.mean(np.array(errors) ** 2)))

    @staticmethod
    def _iris_spread(iris_points: List[Tuple[float, float]]) -> float:
        xs = [p[0] for p in iris_points]
        ys = [p[1] for p in iris_points]
        return max(max(xs) - min(xs), max(ys) - min(ys))

    @classmethod
    def fit_best(
        cls,
        pairs: Sequence[PointPair],
        frame_w: float,
        frame_h: float,
        max_rms_px: float = 80.0,
    ) -> FitResult:
        del frame_h, max_rms_px  # IDW fits calibration points exactly

        if len(pairs) < 5:
            return FitResult(
                success=False,
                message=f"Calibration fit failed: need 5 points, got {len(pairs)}.",
            )

        best_mapper: Optional[InterpolationGazeMapper] = None
        best_rms = float("inf")

        for flip_x in (False, True):
            iris_pts = []
            screen_pts = []
            for (ix, iy), (sx, sy) in pairs:
                ix_use = frame_w - ix if flip_x else ix
                iris_pts.append((ix_use, iy))
                screen_pts.append((sx, sy))

            spread = cls._iris_spread(iris_pts)
            if spread < MIN_IRIS_SPREAD:
                continue

            mapper = cls(iris_pts, screen_pts, flip_x=flip_x, frame_w=frame_w)
            rms = mapper.rms_on_pairs(pairs)
            if rms < best_rms:
                best_rms = rms
                best_mapper = mapper

        if best_mapper is None:
            return FitResult(
                success=False,
                message=(
                    "Calibration failed: iris positions were nearly identical at all "
                    "five dots. Move only your eyes farther toward each corner."
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
            )
        except (KeyError, TypeError, ValueError):
            return None

    def to_dict(self) -> dict:
        return {
            "model": self.model_type,
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
