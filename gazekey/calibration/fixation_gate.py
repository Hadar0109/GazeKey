"""Fixation gating for calibration samples.

Stability is checked on legacy ratio features (avg_h/avg_v) and on the same
4-D PCA representation the mapper consumes (pca_uL, pca_vL, pca_uR, pca_vR).
Averaging left/right into 2-D mean u,v is not sufficient: opposing-eye motion
can cancel in that mean while still polluting the PCA4 fit.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Optional, Tuple

import numpy as np

from gazekey.features.feature_types import FrameFeatures


class FixationState(str, Enum):
    WAIT_LOCK = "WAIT_LOCK"
    COLLECTING = "LOCKED_COLLECTING"
    RESET_JUMP = "RESET_JUMP"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class FixationGateConfig:
    lock_on_ms: float = 420.0
    complete_ms: float = 1400.0
    point_timeout_ms: float = 12000.0
    min_samples: int = 28

    max_std_ratio: float = 0.040
    max_std_pca: float = 0.035
    min_stability_window: int = 12
    jump_threshold_ratio: float = 0.07
    jump_threshold_pca: float = 0.10
    enable_jump_reset: bool = True

    enable_head_drift_gate: bool = True
    max_head_drift_face_xy: float = 0.008
    max_head_drift_eye_h: float = 0.003


def _pca4(features: FrameFeatures) -> Optional[Tuple[float, float, float, float]]:
    """Mapper PCA4 vector: (uL, vL, uR, vR). None if any channel is missing."""
    if (
        features.pca_uL is None
        or features.pca_vL is None
        or features.pca_uR is None
        or features.pca_vR is None
    ):
        return None
    return (
        float(features.pca_uL),
        float(features.pca_vL),
        float(features.pca_uR),
        float(features.pca_vR),
    )


@dataclass
class FixationGate:
    cfg: FixationGateConfig

    _state: FixationState = FixationState.WAIT_LOCK
    _elapsed_point_ms: float = 0.0
    _elapsed_collect_ms: float = 0.0
    _ratio_window: Deque[Tuple[float, float]] = field(default_factory=deque)
    _pca_window: Deque[Tuple[float, float, float, float]] = field(default_factory=deque)
    _window_ms: float = 0.0
    _head_baseline: Optional[dict[str, float]] = None

    def reset_point(self) -> None:
        self._state = FixationState.WAIT_LOCK
        self._elapsed_point_ms = 0.0
        self._elapsed_collect_ms = 0.0
        self._ratio_window.clear()
        self._pca_window.clear()
        self._window_ms = 0.0
        self._head_baseline = None

    def _capture_head_baseline(self, features: FrameFeatures) -> None:
        baseline: dict[str, float] = {}
        for attr in ("face_x", "face_y", "eye_box_w", "eye_box_h"):
            v = getattr(features, attr, None)
            if v is not None and np.isfinite(float(v)):
                baseline[attr] = float(v)
        self._head_baseline = baseline if baseline else None

    def _head_drift_exceeded(self, features: FrameFeatures) -> bool:
        if not self.cfg.enable_head_drift_gate or self._head_baseline is None:
            return False
        thr_xy = float(self.cfg.max_head_drift_face_xy)
        thr_h = float(self.cfg.max_head_drift_eye_h)
        for attr, thr in (("face_x", thr_xy), ("face_y", thr_xy), ("eye_box_w", thr_xy), ("eye_box_h", thr_h)):
            base = self._head_baseline.get(attr)
            cur = getattr(features, attr, None)
            if base is None or cur is None:
                continue
            if abs(float(cur) - float(base)) > thr:
                return True
        return False

    @property
    def state(self) -> FixationState:
        return self._state

    def update(
        self,
        features: FrameFeatures,
        *,
        dt_ms: float,
    ) -> Tuple[FixationState, bool, str]:
        """Returns (state, accept_sample, reason_if_rejected)."""
        dt_ms_f = float(max(0.0, dt_ms))
        self._elapsed_point_ms += dt_ms_f
        if self._elapsed_point_ms > self.cfg.point_timeout_ms:
            self._state = FixationState.TIMEOUT
            return self._state, False, "timeout"

        if not features.face_detected:
            return self._state, False, "face_missing"
        if features.blink:
            return self._state, False, "blink"
        if features.avg_h is None or features.avg_v is None:
            return self._state, False, "missing_ratios"

        ratio = (float(features.avg_h), float(features.avg_v))
        pca4 = _pca4(features)

        if self.cfg.enable_jump_reset and self._ratio_window:
            mx = float(np.mean([p[0] for p in self._ratio_window]))
            my = float(np.mean([p[1] for p in self._ratio_window]))
            shift = float(np.hypot(ratio[0] - mx, ratio[1] - my))
            if shift > self.cfg.jump_threshold_ratio:
                self.reset_point()
                return FixationState.RESET_JUMP, False, "jump_ratio"
        if self.cfg.enable_jump_reset and pca4 is not None and self._pca_window:
            mu = np.mean(np.array(self._pca_window, dtype=np.float64), axis=0)
            jump_l = float(np.hypot(pca4[0] - mu[0], pca4[1] - mu[1]))
            jump_r = float(np.hypot(pca4[2] - mu[2], pca4[3] - mu[3]))
            if max(jump_l, jump_r) > self.cfg.jump_threshold_pca:
                self.reset_point()
                return FixationState.RESET_JUMP, False, "jump_pca"

        if self._state == FixationState.WAIT_LOCK:
            self._push_windows(ratio, pca4, dt_ms=dt_ms_f)
            stable = self._is_stable()
            if self._window_ms >= self.cfg.lock_on_ms and stable:
                self._state = FixationState.COLLECTING
                self._elapsed_collect_ms = 0.0
                self._capture_head_baseline(features)
            reason = self._locking_reason(stable=stable)
            return self._state, False, reason

        if self._state == FixationState.RESET_JUMP:
            self.reset_point()
            return FixationState.RESET_JUMP, False, "jump"

        self._elapsed_collect_ms += dt_ms_f
        self._push_windows(ratio, pca4, dt_ms=dt_ms_f)
        if not self._is_stable():
            self.reset_point()
            return FixationState.WAIT_LOCK, False, "unstable"
        if self._head_drift_exceeded(features):
            self.reset_point()
            return FixationState.WAIT_LOCK, False, "head_drift"

        return self._state, True, ""

    def _push_windows(
        self,
        ratio: Tuple[float, float],
        pca4: Optional[Tuple[float, float, float, float]],
        *,
        dt_ms: float,
    ) -> None:
        self._ratio_window.append(ratio)
        if pca4 is not None:
            self._pca_window.append(pca4)
        self._window_ms += dt_ms
        while len(self._ratio_window) > 180:
            self._ratio_window.popleft()
        while len(self._pca_window) > 180:
            self._pca_window.popleft()

    def _std_window(self, window: Deque[Tuple[float, float]]) -> Tuple[float, float]:
        if len(window) < int(self.cfg.min_stability_window):
            return 0.0, 0.0
        xs = np.array([p[0] for p in window], dtype=np.float64)
        ys = np.array([p[1] for p in window], dtype=np.float64)
        return float(np.std(xs)), float(np.std(ys))

    def _pca4_channel_stds(self) -> Tuple[float, float, float, float]:
        if len(self._pca_window) < int(self.cfg.min_stability_window):
            return 0.0, 0.0, 0.0, 0.0
        arr = np.array(self._pca_window, dtype=np.float64)
        stds = np.std(arr, axis=0)
        return float(stds[0]), float(stds[1]), float(stds[2]), float(stds[3])

    def _is_stable(self) -> bool:
        std_h, std_v = self._std_window(self._ratio_window)
        if max(std_h, std_v) > self.cfg.max_std_ratio:
            return False
        if len(self._pca_window) >= int(self.cfg.min_stability_window):
            if max(self._pca4_channel_stds()) > self.cfg.max_std_pca:
                return False
        return True

    def _locking_reason(self, *, stable: bool) -> str:
        if self._window_ms < self.cfg.lock_on_ms:
            return "locking:time"
        if not stable:
            return "locking:unstable"
        return "locking"

    def debug_metrics(self) -> dict[str, Any]:
        std_h, std_v = self._std_window(self._ratio_window)
        std_ul, std_vl, std_ur, std_vr = self._pca4_channel_stds()
        return {
            "state": str(self._state.value),
            "elapsed_point_ms": float(self._elapsed_point_ms),
            "elapsed_collect_ms": float(self._elapsed_collect_ms),
            "window_len": int(len(self._ratio_window)),
            "window_ms": float(self._window_ms),
            "std_h": float(std_h),
            "std_v": float(std_v),
            "std_pca_uL": float(std_ul),
            "std_pca_vL": float(std_vl),
            "std_pca_uR": float(std_ur),
            "std_pca_vR": float(std_vr),
            "std_pca_u": float(max(std_ul, std_ur)),
            "std_pca_v": float(max(std_vl, std_vr)),
            "max_std_ratio": float(self.cfg.max_std_ratio),
            "max_std_pca": float(self.cfg.max_std_pca),
            "lock_on_ms": float(self.cfg.lock_on_ms),
            "complete_ms": float(self.cfg.complete_ms),
            "min_samples": int(self.cfg.min_samples),
            "min_stability_window": int(self.cfg.min_stability_window),
            "enable_jump_reset": bool(self.cfg.enable_jump_reset),
        }
