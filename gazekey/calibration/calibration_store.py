"""Persist and load calibration data."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

from gazekey.calibration.affine_mapper import AffineGazeMapper
from gazekey.calibration.gaze_mapper import GazeMapper, InterpolationGazeMapper

CALIBRATION_VERSION = 5
DEFAULT_CALIBRATION_PATH = Path(__file__).resolve().parents[2] / "calibration_data.json"


@dataclass
class StoredCalibration:
    mapper: GazeMapper
    screen_targets: List[Tuple[float, float]]
    iris_means: List[Tuple[float, float]]
    path: Path


def _load_mapper(data: dict) -> Optional[GazeMapper]:
    model = data.get("model", "affine")

    if model in ("quadratic", "normalized_affine", "separate_linear"):
        print(f"Saved calibration uses legacy model '{model}'. Please recalibrate.")
        return None

    if model == "interpolation" or "iris_points" in data:
        loaded = InterpolationGazeMapper.from_dict(data)
        if loaded is not None:
            return loaded

    matrix = data.get("matrix")
    if matrix and len(matrix) == 2 and len(matrix[0]) == 3:
        return AffineGazeMapper.from_matrix_list(
            matrix,
            flip_x=bool(data.get("flip_x", False)),
            frame_w=float(data.get("frame_w", 640)),
        )
    return None


class CalibrationStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or DEFAULT_CALIBRATION_PATH

    def exists(self) -> bool:
        return self.path.is_file()

    def load(self) -> Optional[StoredCalibration]:
        if not self.exists():
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Failed to load calibration: {e}")
            return None

        version = data.get("version", 1)
        if version not in (1, 2, 3, 4, 5):
            print("Calibration file version mismatch.")
            return None

        model = data.get("model", "affine")
        if (
            version < CALIBRATION_VERSION
            and (model == "interpolation" or "iris_points" in data)
        ):
            print(
                "Saved calibration uses an outdated gaze model. Please recalibrate."
            )
            return None

        screen_targets = [tuple(p) for p in data.get("screen_targets", [])]
        iris_means = [tuple(p) for p in data.get("iris_means", [])]
        if len(screen_targets) != 5 or len(iris_means) != 5:
            print("Invalid calibration point count.")
            return None

        mapper = _load_mapper(data)
        if mapper is None:
            print("Invalid calibration model data.")
            return None

        return StoredCalibration(
            mapper=mapper,
            screen_targets=screen_targets,
            iris_means=iris_means,
            path=self.path,
        )

    def save(
        self,
        mapper: GazeMapper,
        screen_targets: List[Tuple[float, float]],
        iris_means: List[Tuple[float, float]],
    ) -> bool:
        payload: dict[str, Any] = {
            "version": CALIBRATION_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "screen_targets": [list(p) for p in screen_targets],
            "iris_means": [list(p) for p in iris_means],
        }

        if isinstance(mapper, InterpolationGazeMapper):
            payload.update(mapper.to_dict())
        elif isinstance(mapper, AffineGazeMapper):
            payload["model"] = "affine"
            payload["matrix"] = mapper.matrix.tolist()
            payload["flip_x"] = mapper.flip_x
            payload["frame_w"] = mapper.frame_w
        else:
            print("Unknown mapper type.")
            return False

        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            return True
        except OSError as e:
            print(f"Failed to save calibration: {e}")
            return False

    def clear(self) -> None:
        if self.path.is_file():
            try:
                self.path.unlink()
            except OSError as e:
                print(f"Failed to remove calibration file: {e}")
