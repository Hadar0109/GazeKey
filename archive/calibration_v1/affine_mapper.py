"""Affine mapping from iris camera pixels to screen pixels."""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

PointPair = Tuple[Tuple[float, float], Tuple[float, float]]


@dataclass
class FitResult:
    success: bool
    message: str
    mapper: Optional["AffineGazeMapper"] = None


class AffineGazeMapper:
    """Maps iris (x, y) in camera pixels to screen (sx, sy)."""

    def __init__(
        self,
        matrix: np.ndarray,
        flip_x: bool = False,
        frame_w: float = 640.0,
    ):
        self._m = matrix.astype(np.float64)
        self.flip_x = flip_x
        self.frame_w = float(frame_w)

    @property
    def matrix(self) -> np.ndarray:
        return self._m.copy()

    def _iris_for_model(self, iris_x: float, iris_y: float) -> Tuple[float, float]:
        if self.flip_x:
            return self.frame_w - iris_x, iris_y
        return iris_x, iris_y

    def map_point(self, iris_x: float, iris_y: float) -> Tuple[float, float]:
        ix, iy = self._iris_for_model(iris_x, iris_y)
        v = np.array([ix, iy, 1.0], dtype=np.float64)
        out = self._m @ v
        return float(out[0]), float(out[1])

    def rms_on_pairs(self, pairs: Sequence[PointPair]) -> float:
        errors = []
        for (ix, iy), (sx, sy) in pairs:
            mx, my = self.map_point(ix, iy)
            errors.append(np.hypot(mx - sx, my - sy))
        return float(np.sqrt(np.mean(np.array(errors) ** 2)))

    @classmethod
    def fit_best(
        cls,
        pairs: Sequence[PointPair],
        frame_w: float,
        max_rms_px: float = 40.0,
    ) -> FitResult:
        """Fit affine transform, trying normal and horizontally mirrored iris X."""
        best_mapper: Optional[AffineGazeMapper] = None
        best_rms = float("inf")

        for flip_x in (False, True):
            if flip_x:
                fit_pairs = [
                    ((frame_w - ix, iy), screen) for (ix, iy), screen in pairs
                ]
            else:
                fit_pairs = list(pairs)

            result = cls.fit(fit_pairs, max_rms_px=max_rms_px * 100)
            if result.mapper is None:
                continue

            mapper = cls(result.mapper.matrix, flip_x=flip_x, frame_w=frame_w)
            rms = mapper.rms_on_pairs(pairs)
            if rms < best_rms:
                best_rms = rms
                best_mapper = mapper

        if best_mapper is None:
            return cls.fit(pairs, max_rms_px=max_rms_px)

        if best_rms <= max_rms_px:
            return FitResult(
                success=True,
                message="Calibration successful.",
                mapper=best_mapper,
            )

        return FitResult(
            success=False,
            message=(
                f"Calibration fit failed: mapping error too high "
                f"({best_rms:.1f} px RMS). Redo calibration in consistent lighting."
            ),
            mapper=best_mapper,
        )

    @classmethod
    def fit(cls, pairs: Sequence[PointPair], max_rms_px: float = 40.0) -> FitResult:
        if len(pairs) < 3:
            return FitResult(
                success=False,
                message=f"Calibration fit failed: need at least 3 points, got {len(pairs)}.",
            )

        iris_pts = np.array([[p[0][0], p[0][1], 1.0] for p in pairs], dtype=np.float64)
        screen_x = np.array([p[1][0] for p in pairs], dtype=np.float64)
        screen_y = np.array([p[1][1] for p in pairs], dtype=np.float64)

        if len(np.unique(iris_pts[:, :2], axis=0)) < 3:
            return FitResult(
                success=False,
                message="Calibration fit failed: degenerate iris samples (collinear).",
            )

        try:
            coeffs_x, _, rank_x, _ = np.linalg.lstsq(iris_pts, screen_x, rcond=None)
            coeffs_y, _, rank_y, _ = np.linalg.lstsq(iris_pts, screen_y, rcond=None)
        except np.linalg.LinAlgError:
            return FitResult(
                success=False,
                message="Calibration fit failed: singular matrix (iris samples too similar).",
            )

        if rank_x < 3 or rank_y < 3:
            return FitResult(
                success=False,
                message="Calibration fit failed: degenerate iris samples (collinear).",
            )

        matrix = np.vstack([coeffs_x, coeffs_y])
        mapper = cls(matrix)

        rms = mapper.rms_on_pairs(pairs)
        if rms > max_rms_px:
            return FitResult(
                success=False,
                message=(
                    f"Calibration fit failed: mapping error too high "
                    f"({rms:.1f} px RMS). Redo calibration in consistent lighting."
                ),
                mapper=mapper,
            )

        return FitResult(success=True, message="Calibration successful.", mapper=mapper)

    @classmethod
    def from_matrix_list(
        cls,
        rows: List[List[float]],
        flip_x: bool = False,
        frame_w: float = 640.0,
    ) -> "AffineGazeMapper":
        return cls(np.array(rows, dtype=np.float64), flip_x=flip_x, frame_w=frame_w)
