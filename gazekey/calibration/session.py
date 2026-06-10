"""Calibration session: keyboard-local targets, fixation gating, per-target means."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from gazekey.calibration.fixation_gate import FixationGate, FixationGateConfig, FixationState
from gazekey.calibration.outliers import check_target_mean_outlier
from gazekey.calibration.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures
from gazekey.mvp_log import mvp_log, mvp_verbose


@dataclass(frozen=True)
class CalibrationResult:
    success: bool
    message: str
    targets: List[CalibrationTarget]
    feature_means: Optional[List[Tuple[float, float]]] = None


class CalibrationSession:
    def __init__(
        self,
        *,
        targets: List[CalibrationTarget],
        session_id: str,
        calibration_version: int = 6,
        calibration_mode: str = "keyboard15",
        gate_cfg: Optional[FixationGateConfig] = None,
        max_timeouts_per_target: int = 1,
        max_outlier_retries_per_target: int = 2,
        on_timeout: str = "advance",
    ) -> None:
        if not targets:
            raise ValueError("Calibration requires at least one target")
        self.targets = list(targets)
        self.session_id = str(session_id)
        self.calibration_version = int(calibration_version)
        self.calibration_mode = calibration_mode
        self.gate = FixationGate(cfg=gate_cfg or FixationGateConfig())
        self.max_timeouts_per_target = int(max(0, max_timeouts_per_target))
        self.max_outlier_retries_per_target = int(max(0, max_outlier_retries_per_target))
        self._outlier_retries: List[int] = [0 for _ in self.targets]
        if on_timeout not in {"advance", "retry"}:
            raise ValueError(f"Unknown on_timeout: {on_timeout}")
        self.on_timeout = on_timeout
        self._target_index = 0
        self._accepted_ratios: List[List[Tuple[float, float]]] = [[] for _ in self.targets]
        self._accepted_frames: List[List[FrameFeatures]] = [[] for _ in self.targets]
        self._accepted_features: List[List[FrameFeatures]] = [[] for _ in self.targets]
        self._timeouts_for_target: List[int] = [0 for _ in self.targets]
        self._last_reject_reason: str = ""
        self._last_fixation_state: FixationState = FixationState.WAIT_LOCK

    @property
    def target_index(self) -> int:
        return self._target_index

    @property
    def last_reject_reason(self) -> str:
        return self._last_reject_reason

    @property
    def last_fixation_state(self) -> FixationState:
        return self._last_fixation_state

    @property
    def is_finished(self) -> bool:
        return self._target_index >= len(self.targets)

    def current_target(self) -> CalibrationTarget:
        return self.targets[self._target_index]

    def begin_target(self) -> None:
        self.gate.reset_point()
        self._last_reject_reason = ""
        self._last_fixation_state = FixationState.WAIT_LOCK

    def process(
        self,
        features: FrameFeatures,
        *,
        dt_ms: float,
    ) -> Optional[CalibrationResult]:
        if self.is_finished:
            return None

        state, accept, reason = self.gate.update(features, dt_ms=float(dt_ms))
        self._last_fixation_state = state
        self._last_reject_reason = "" if accept else reason
        t = self.current_target()

        avg_h = features.avg_h
        avg_v = features.avg_v
        accepted = bool(accept and avg_h is not None and avg_v is not None)
        if accepted:
            self._accepted_ratios[self._target_index].append((float(avg_h), float(avg_v)))
            self._accepted_frames[self._target_index].append(features)

        if state == FixationState.TIMEOUT:
            if self.target_mean_ready(self._target_index):
                self._finish_target()
            else:
                self._timeouts_for_target[self._target_index] += 1
                self.begin_target()
            if self.is_finished:
                return CalibrationResult(
                    success=True,
                    message="Target collection complete.",
                    targets=self.targets,
                    feature_means=self._compute_means(),
                )
            return None

        if not self.is_finished and state == FixationState.COLLECTING:
            if self.target_mean_ready(self._target_index):
                self._finish_target()

        if self.is_finished:
            return CalibrationResult(
                success=True,
                message="Target collection complete.",
                targets=self.targets,
                feature_means=self._compute_means(),
            )
        return None

    def _finish_target(self) -> None:
        idx = self._target_index
        self._finalize_target_training_feature(idx)
        if self._accepted_features[idx]:
            peer_feats: List[Optional[FrameFeatures]] = []
            for j, frames in enumerate(self._accepted_features):
                peer_feats.append(frames[-1] if frames else None)
            outlier_msg = check_target_mean_outlier(
                idx=idx,
                feature=self._accepted_features[idx][-1],
                targets=self.targets,
                peer_features=peer_feats,
            )
            if outlier_msg is not None:
                self._outlier_retries[idx] += 1
                mvp_log(f"[calib] target outlier: {outlier_msg}")
                if self._outlier_retries[idx] <= self.max_outlier_retries_per_target:
                    self._accepted_features[idx].clear()
                    self._accepted_ratios[idx].clear()
                    self._accepted_frames[idx].clear()
                    self.begin_target()
                    return
        self._target_index += 1
        if not self.is_finished:
            self.begin_target()

    def _finalize_target_training_feature(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.targets):
            return
        frames = self._accepted_frames[idx]
        ratios = self._accepted_ratios[idx]
        if not ratios or not frames:
            return

        def iqr_filter(values: np.ndarray) -> np.ndarray:
            values = np.asarray(values, dtype=np.float64)
            values = values[np.isfinite(values)]
            if values.size < 4:
                return values
            q1, q3 = np.percentile(values, [25, 75])
            iqr = float(q3 - q1)
            if iqr <= 1e-12:
                return values
            lo = float(q1 - 1.5 * iqr)
            hi = float(q3 + 1.5 * iqr)
            kept = values[(values >= lo) & (values <= hi)]
            return kept if kept.size else values

        def mean_opt(vals: List[Optional[float]]) -> Optional[float]:
            xs = np.array([v for v in vals if v is not None and np.isfinite(float(v))], dtype=np.float64)
            if xs.size == 0:
                return None
            xs = iqr_filter(xs)
            return float(np.mean(xs)) if xs.size else None

        hs = np.array([p[0] for p in ratios], dtype=np.float64)
        vs = np.array([p[1] for p in ratios], dtype=np.float64)
        hs_f = iqr_filter(hs)
        vs_f = iqr_filter(vs)
        mh = float(np.mean(hs_f)) if hs_f.size else float(np.mean(hs))
        mv = float(np.mean(vs_f)) if vs_f.size else float(np.mean(vs))

        f = FrameFeatures(
            timestamp_ms=0,
            face_detected=True,
            blink=False,
            confidence=1.0,
            Lh=mean_opt([fr.Lh for fr in frames]),
            Lv=mean_opt([fr.Lv for fr in frames]),
            Rh=mean_opt([fr.Rh for fr in frames]),
            Rv=mean_opt([fr.Rv for fr in frames]),
            avg_h=float(mh),
            avg_v=float(mv),
            eye_box_w=mean_opt([fr.eye_box_w for fr in frames]),
            eye_box_h=mean_opt([fr.eye_box_h for fr in frames]),
            face_x=mean_opt([fr.face_x for fr in frames]),
            face_y=mean_opt([fr.face_y for fr in frames]),
            pca_uL=mean_opt([fr.pca_uL for fr in frames]),
            pca_vL=mean_opt([fr.pca_vL for fr in frames]),
            pca_uR=mean_opt([fr.pca_uR for fr in frames]),
            pca_vR=mean_opt([fr.pca_vR for fr in frames]),
        )
        self._accepted_features[idx].append(f)

    def _compute_means(self) -> List[Tuple[float, float]]:
        means: List[Tuple[float, float]] = []
        for s in self._accepted_ratios:
            if not s:
                means.append((0.5, 0.5))
                continue
            xs = np.array([p[0] for p in s], dtype=np.float64)
            ys = np.array([p[1] for p in s], dtype=np.float64)
            means.append((float(np.mean(xs)), float(np.mean(ys))))
        return means

    def accepted_count_for_target(self, idx: int) -> int:
        if idx < 0 or idx >= len(self.targets):
            return 0
        return len(self._accepted_features[idx])

    def samples_used_for_target_mean(self, idx: int) -> int:
        if idx < 0 or idx >= len(self.targets):
            return 0
        return len(self._accepted_ratios[idx])

    def target_means_count(self) -> int:
        return sum(1 for frames in self._accepted_features if len(frames) > 0)

    def target_mean_ready(self, idx: int) -> bool:
        if idx < 0 or idx >= len(self.targets):
            return False
        if self._last_fixation_state != FixationState.COLLECTING:
            return False
        samples = self._accepted_ratios[idx]
        gate_dbg = self.gate.debug_metrics()
        return bool(
            len(samples) >= int(self.gate.cfg.min_samples)
            and float(gate_dbg.get("elapsed_collect_ms", 0.0)) >= float(self.gate.cfg.complete_ms)
        )

    def print_training_means(self) -> None:
        if not mvp_verbose():
            return
        mvp_log("[calib] --- per-target training means (u/v per eye) ---")
        for i, t in enumerate(self.targets):
            frames = self._accepted_features[i]
            if not frames:
                mvp_log(f"[calib] T{i+1:02d} {t.label:<14} (no mean)")
                continue
            f = frames[-1]

            def _f(v: Optional[float]) -> str:
                return f"{float(v):8.4f}" if v is not None else "     n/a"

            mvp_log(
                f"[calib] T{i+1:02d} {t.label:<14} "
                f"({int(t.screen_x):4d},{int(t.screen_y):4d}) "
                f"{_f(f.pca_uL)} {_f(f.pca_vL)} {_f(f.pca_uR)} {_f(f.pca_vR)} {_f(f.avg_v)}"
            )

    def get_training_samples(self) -> List[Tuple[FrameFeatures, Tuple[float, float]]]:
        out: List[Tuple[FrameFeatures, Tuple[float, float]]] = []
        for t, frames in zip(self.targets, self._accepted_features):
            p = (float(t.screen_x), float(t.screen_y))
            for f in frames:
                out.append((f, p))
        return out


# Back-compat aliases for transitional imports.
CalibrationV2Session = CalibrationSession
CalibrationV2Result = CalibrationResult
