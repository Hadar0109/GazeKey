"""Identity / origin / DPR-only geometry (contracts/screen-geometry.md).

HARD STOP: any transform other than identity, origin offset, and/or DPR
scaling is forbidden. No mapper, bias, affine, clip_bounds, camera_position
copy, or hard-coded key tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

TransformKind = Literal["identity", "origin", "origin+dpr"]
ALLOWED_TRANSFORMS: frozenset[str] = frozenset({"identity", "origin", "origin+dpr"})

FORBIDDEN_GEOMETRY_KEYS = frozenset(
    {
        "affine",
        "affine_matrix",
        "bias",
        "bias_x",
        "bias_y",
        "_gaze_bias_x",
        "_gaze_bias_y",
        "clip_bounds",
        "camera_position",
        "mapper",
        "ridge",
        "pca",
        "key_table",
        "generate_points",
    }
)


class GeometryStopError(RuntimeError):
    """T012 HARD STOP: a forbidden geometry transform was requested."""


@dataclass(frozen=True)
class GeometryConfig:
    """Allowed conversion: qt_global = origin_offset + gf_filtered_px / dpr_or_1."""

    transform: TransformKind = "identity"
    origin_offset: tuple[float, float] = (0.0, 0.0)
    dpr: float = 1.0

    def __post_init__(self) -> None:
        if self.transform not in ALLOWED_TRANSFORMS:
            raise GeometryStopError(
                f"Geometry STOP: transform {self.transform!r} is forbidden. "
                "Only identity, origin, and origin+dpr are allowed. "
                "Do not add a mapper, bias, affine correction, or generate_points change."
            )
        if not isinstance(self.dpr, (int, float)) or self.dpr <= 0:
            raise GeometryStopError(
                f"Geometry STOP: dpr must be a positive finite scale, got {self.dpr!r}"
            )


@dataclass(frozen=True)
class GeometryAudit:
    """T011 schema only. Live values are filled at T028, not in Stage A."""

    gf_screen_size: tuple[int, int] | None = None
    pygame_mode: tuple[int, int] | None = None
    qt_geometry: tuple[int, int, int, int] | None = None
    device_pixel_ratio: float | None = None
    monitor_origin: tuple[int, int] | None = None
    keyboard_origin: tuple[int, int] | None = None
    transform: TransformKind = "identity"
    key_rects: Mapping[str, tuple[int, int, int, int]] = field(default_factory=dict)
    suggestion_rects: Mapping[str, tuple[int, int, int, int]] = field(
        default_factory=dict
    )


def choose_allowed_transform(
    *,
    origin_offset: tuple[float, float],
    dpr: float,
) -> TransformKind:
    """Pick identity, origin, or origin+dpr. Never a learned remap."""
    ox, oy = origin_offset
    if abs(float(dpr) - 1.0) > 1e-6:
        return "origin+dpr"
    if abs(float(ox)) > 1e-6 or abs(float(oy)) > 1e-6:
        return "origin"
    return "identity"


def _reject_forbidden_kwargs(kwargs: Mapping[str, Any]) -> None:
    hits = sorted(k for k in kwargs if k in FORBIDDEN_GEOMETRY_KEYS)
    if hits:
        raise GeometryStopError(
            "Geometry STOP: forbidden transform parameter(s) "
            f"{hits}. Only identity/origin/DPR are allowed. "
            "Do not add a mapper, bias, affine, clip_bounds, camera_position, "
            "or generate_points change."
        )
    extra = sorted(k for k in kwargs if k not in FORBIDDEN_GEOMETRY_KEYS)
    if extra:
        raise GeometryStopError(
            f"Geometry STOP: unknown geometry parameter(s) {extra}. "
            "Only identity/origin/DPR are allowed."
        )


def apply_geometry(
    gf_x: float,
    gf_y: float,
    config: GeometryConfig,
    **kwargs: Any,
) -> tuple[float, float]:
    """Convert GazeFollower filtered pixels to Qt global.

    ``qt_global = origin_offset + gf_filtered_px / dpr_or_1`` (or identity).
    """
    _reject_forbidden_kwargs(kwargs)
    if config.transform not in ALLOWED_TRANSFORMS:
        raise GeometryStopError(
            f"Geometry STOP: transform {config.transform!r} is forbidden."
        )
    ox, oy = config.origin_offset
    if config.transform == "identity":
        return float(gf_x), float(gf_y)
    if config.transform == "origin":
        return float(ox) + float(gf_x), float(oy) + float(gf_y)
    dpr = float(config.dpr) if config.dpr else 1.0
    return float(ox) + float(gf_x) / dpr, float(oy) + float(gf_y) / dpr
