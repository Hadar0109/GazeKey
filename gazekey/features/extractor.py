"""Extract a small, reliable feature set from MediaPipe EyeData.

Phase 0/1 rule: keep features intentionally minimal and stable:
- left/right gaze ratios and averages (eye-relative iris ratios)
- eye box size (width/height of eye contour bbox)
- face center proxy (midpoint of iris centers when both available)
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
import os

from gazekey.features.feature_types import FrameFeatures
from gazekey.tracking.eye_detector import EyeData


def _diag_raw_eye_geometry(
    *,
    tag: str,
    iris: Tuple[float, float] | None,
    eye: List[Tuple[float, float]] | None,
) -> None:
    """Print raw iris + eye landmark geometry before computing ratios."""
    if iris is None or eye is None or len(eye) < 9:
        return
    try:
        a = eye[0]
        b = eye[8]
        pts = np.array(eye, dtype=np.float64)
        xmin = float(np.min(pts[:, 0]))
        xmax = float(np.max(pts[:, 0]))
        ymin = float(np.min(pts[:, 1]))
        ymax = float(np.max(pts[:, 1]))
        print(
            "[diag] extractor raw "
            f"{tag}: iris=({float(iris[0]):.4f},{float(iris[1]):.4f}) "
            f"cornerA=({float(a[0]):.4f},{float(a[1]):.4f}) "
            f"cornerB=({float(b[0]):.4f},{float(b[1]):.4f}) "
            f"bbox=({xmin:.4f},{ymin:.4f})-({xmax:.4f},{ymax:.4f}) n={len(eye)}"
        )
    except Exception:
        return


def _bbox_size(points: List[Tuple[float, float]]) -> Tuple[float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (max(xs) - min(xs), max(ys) - min(ys))


def _eye_uv_one_eye(
    eye_landmarks: List[Tuple[float, float]],
    iris_center: Tuple[float, float],
) -> Optional[Tuple[float, float]]:
    """
    Compute an eye-local (u,v) using deterministic eye geometry.

    Basis:
    - horizontal axis: outer_corner -> inner_corner (stable across frames)
    - vertical axis: perpendicular to horizontal, with sign forced so +v points down

    Normalization (stable, not PCA/RMS-based):
    - u normalized by eye width (corner distance)
    - v normalized by eyelid aperture (upper/lower lid separation along vertical axis),
      falling back to robust contour height along vertical axis if eyelids are unavailable.

    Returns:
    - u, v as *unclamped* normalized coordinates, typically in about [-0.5..0.5].
    """
    if len(eye_landmarks) < 9:
        return None

    # EyeDetector provides contour points in an order where corners are stable:
    # - first point and 9th point correspond to outer/inner corners (indices 0 and 8).
    a = np.array(eye_landmarks[0], dtype=np.float64)
    b = np.array(eye_landmarks[8], dtype=np.float64)
    x_axis = b - a
    eye_w = float(np.linalg.norm(x_axis))
    if eye_w < 1e-6:
        return None
    x_hat = x_axis / eye_w

    # Perpendicular; force +v to point down in image coordinates (y increases down).
    y_hat = np.array([-x_hat[1], x_hat[0]], dtype=np.float64)
    if float(y_hat[1]) < 0.0:
        y_hat = -y_hat

    pts = np.array(eye_landmarks, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        return None

    # Use midpoint of corners as the origin for a symmetric, stable coordinate.
    origin = 0.5 * (a + b)

    iris = np.array(iris_center, dtype=np.float64)
    rel_iris = iris - origin
    u = float(rel_iris @ x_hat)
    v = float(rel_iris @ y_hat)

    # Vertical normalization by eyelid aperture if possible.
    aperture = None
    if len(eye_landmarks) >= 13:
        rel = pts - origin
        proj_y = rel @ y_hat
        upper = proj_y[1:5]
        lower = np.concatenate([proj_y[5:8], proj_y[9:13]])
        if upper.size and lower.size:
            upper_y = float(np.median(upper))
            lower_y = float(np.median(lower))
            aperture = float(abs(lower_y - upper_y))

    if aperture is None or aperture < 1e-6:
        # Fallback: robust contour height along vertical axis.
        rel = pts - origin
        proj_y = rel @ y_hat
        q_lo, q_hi = 0.20, 0.80
        aperture = float(np.quantile(proj_y, q_hi) - np.quantile(proj_y, q_lo))
        if aperture < 1e-6:
            return None

    # Normalize to unitless coordinates.
    # u ~ [-0.5..0.5] when iris stays within corners; v similar for eyelid aperture.
    u_n = float(u / eye_w)
    v_n = float(v / aperture)
    return u_n, v_n


class FeatureExtractor:
    # Enable with env var `GAZEKEY_DIAG_EXTRACTOR=1` (kept off by default to avoid console spam).
    DIAG_RAW: bool = os.environ.get("GAZEKEY_DIAG_EXTRACTOR", "0").strip() == "1"

    @staticmethod
    def from_eye_data(eye_data: EyeData, *, timestamp_ms: int) -> FrameFeatures:
        face_detected = bool(eye_data.face_detected)
        blink = bool(getattr(eye_data, "is_blinking", False))

        # Conservative confidence: 1.0 only when face detected and at least one iris is present.
        left_iris = eye_data.left_iris_center
        right_iris = eye_data.right_iris_center
        left_eye = eye_data.left_eye_landmarks
        right_eye = eye_data.right_eye_landmarks

        iris_ok = (left_iris is not None) or (right_iris is not None)
        confidence = 1.0 if (face_detected and iris_ok and not blink) else 0.0

        Lh = Lv = Rh = Rv = None  # compatibility 0..1 ratios for gating + IDW baselines
        pca_uL = pca_vL = pca_uR = pca_vR = None  # raw eye-local coords for geometric mappers
        if face_detected and not blink:
            if left_iris is not None and left_eye is not None:
                if FeatureExtractor.DIAG_RAW and (int(timestamp_ms) % 500) < 25:
                    _diag_raw_eye_geometry(tag="L", iris=left_iris, eye=left_eye)
                uv = _eye_uv_one_eye(left_eye, left_iris)
                if uv is not None:
                    pca_uL, pca_vL = uv
                    # Legacy ratios: map roughly [-0.5..0.5] -> [0..1] for gating/baselines.
                    Lh = float(max(0.0, min(1.0, 0.5 + float(pca_uL))))
                    Lv = float(max(0.0, min(1.0, 0.5 + float(pca_vL))))
            if right_iris is not None and right_eye is not None:
                if FeatureExtractor.DIAG_RAW and (int(timestamp_ms) % 500) < 25:
                    _diag_raw_eye_geometry(tag="R", iris=right_iris, eye=right_eye)
                uv = _eye_uv_one_eye(right_eye, right_iris)
                if uv is not None:
                    pca_uR, pca_vR = uv
                    Rh = float(max(0.0, min(1.0, 0.5 + float(pca_uR))))
                    Rv = float(max(0.0, min(1.0, 0.5 + float(pca_vR))))

        ratios = [(Lh, Lv), (Rh, Rv)]
        valid = [(h, v) for h, v in ratios if h is not None and v is not None]
        avg_h = avg_v = None
        if valid:
            avg_h = sum(h for h, _ in valid) / len(valid)
            avg_v = sum(v for _, v in valid) / len(valid)

        eye_box_w = eye_box_h = None
        if left_eye is not None and right_eye is not None:
            lw, lh = _bbox_size(left_eye)
            rw, rh = _bbox_size(right_eye)
            eye_box_w = (lw + rw) / 2.0
            eye_box_h = (lh + rh) / 2.0
        elif left_eye is not None:
            eye_box_w, eye_box_h = _bbox_size(left_eye)
        elif right_eye is not None:
            eye_box_w, eye_box_h = _bbox_size(right_eye)

        # Face center proxy: midpoint of iris centers when available, otherwise None.
        face_x = face_y = None
        if left_iris is not None and right_iris is not None:
            face_x = (left_iris[0] + right_iris[0]) / 2.0
            face_y = (left_iris[1] + right_iris[1]) / 2.0
        elif left_iris is not None:
            face_x, face_y = left_iris
        elif right_iris is not None:
            face_x, face_y = right_iris

        return FrameFeatures(
            timestamp_ms=int(timestamp_ms),
            face_detected=face_detected,
            blink=blink,
            confidence=float(confidence),
            Lh=Lh,
            Lv=Lv,
            Rh=Rh,
            Rv=Rv,
            avg_h=avg_h,
            avg_v=avg_v,
            eye_box_w=eye_box_w,
            eye_box_h=eye_box_h,
            face_x=face_x,
            face_y=face_y,
            pca_uL=pca_uL,
            pca_vL=pca_vL,
            pca_uR=pca_uR,
            pca_vR=pca_vR,
        )

