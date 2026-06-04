"""Calibration v2 session: keyboard-local 9/13 targets + gating + CSV logging."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from gazekey.calibration2.calibration_csv import (
    CalibrationCsvLogger,
    CalibrationSampleRow,
    CalibrationSummaryRow,
)
from gazekey.calibration2.fixation_gate import FixationGate, FixationGateConfig, FixationState
from gazekey.calibration2.outliers import check_target_mean_outlier
from gazekey.calibration2.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures


@dataclass(frozen=True)
class CalibrationV2Result:
    success: bool
    message: str
    targets: List[CalibrationTarget]
    feature_means: Optional[List[Tuple[float, float]]] = None  # avg_h/avg_v means


class CalibrationV2Session:
    def __init__(
        self,
        *,
        targets: List[CalibrationTarget],
        csv_logger: CalibrationCsvLogger,
        calibration_version: int = 6,
        calibration_mode: str = "default9",
        gate_cfg: Optional[FixationGateConfig] = None,
        max_timeouts_per_target: int = 1,
        max_outlier_retries_per_target: int = 2,
        on_timeout: str = "advance",  # "advance" or "retry"
    ) -> None:
        if not targets:
            raise ValueError("Calibration requires at least one target")
        self.targets = list(targets)
        self.csv = csv_logger
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
        self._sample_index = 0
        # For summary means (avg_h/avg_v only).
        self._accepted_ratios: List[List[Tuple[float, float]]] = [[] for _ in self.targets]
        # Full accepted frames per target (used to build robust per-target mean feature vectors).
        self._accepted_frames: List[List[FrameFeatures]] = [[] for _ in self.targets]
        # For mapper fitting: keep only window-mean features per target (robust, low-noise).
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
    ) -> Optional[CalibrationV2Result]:
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
            # Keep full frames so we can compute a mean feature vector per target (not only avg_h/v).
            self._accepted_frames[self._target_index].append(features)
            # We store per-frame ratios for stats; training features are reduced to per-target means
            # when the target completes (see `_finalize_target_training_feature`).

        self.csv.log_sample(
            CalibrationSampleRow(
                calibration_version=self.calibration_version,
                session_id=self.csv.session_id,
                sample_index=self._sample_index,
                target_id=t.target_id,
                target_key_id=t.key_id,
                target_label=t.label,
                target_screen_x=t.screen_x,
                target_screen_y=t.screen_y,
                timestamp_ms=features.timestamp_ms,
                face_detected=features.face_detected,
                blink=features.blink,
                left_eye_h=features.Lh,
                left_eye_v=features.Lv,
                right_eye_h=features.Rh,
                right_eye_v=features.Rv,
                pca_uL=features.pca_uL,
                pca_vL=features.pca_vL,
                pca_uR=features.pca_uR,
                pca_vR=features.pca_vR,
                avg_h=features.avg_h,
                avg_v=features.avg_v,
                eye_box_w=features.eye_box_w,
                eye_box_h=features.eye_box_h,
                face_x=features.face_x,
                face_y=features.face_y,
                head_stability=None,
                confidence=float(features.confidence),
                fixation_state=str(state.value),
                accepted=accepted,
                rejection_reason="" if accepted else reason,
                quality_score=None,
                window_std_h=None,
                window_std_v=None,
                velocity=None,
                stable_duration_ms=None,
            )
        )
        self._sample_index += 1

        # Timeout handling: prevent getting stuck on a point forever.
        if state == FixationState.TIMEOUT:
            # Requirement: do NOT advance unless the target mean is ready.
            if self.target_mean_ready(self._target_index):
                self._finish_target()
            else:
                # Retry the same target (reset gate + window) until it's ready.
                self._timeouts_for_target[self._target_index] += 1
                self.begin_target()
            # After timeout handling we don't continue to completion checks.
            if self.is_finished:
                means = self._compute_means()
                return CalibrationV2Result(
                    success=True,
                    message="Calibration v2 complete.",
                    targets=self.targets,
                    feature_means=means,
                )
            return None

        # Completion condition: gate in COLLECTING and enough samples and time.
        if not self.is_finished and state == FixationState.COLLECTING:
            # Only advance when the mean is truly ready (uses same gate thresholds).
            if self.target_mean_ready(self._target_index):
                self._finish_target()

        if self.is_finished:
            means = self._compute_means()
            return CalibrationV2Result(
                success=True,
                message="Calibration v2 complete.",
                targets=self.targets,
                feature_means=means,
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
                print(f"[calib2] target outlier: {outlier_msg}")
                if self._outlier_retries[idx] <= self.max_outlier_retries_per_target:
                    print(
                        f"[calib2] recollecting target {self.targets[idx].label} "
                        f"(attempt {self._outlier_retries[idx]}/{self.max_outlier_retries_per_target})"
                    )
                    self._accepted_features[idx].clear()
                    self._accepted_ratios[idx].clear()
                    self._accepted_frames[idx].clear()
                    self.begin_target()
                    return
                print(
                    f"[calib2] outlier retries exhausted for {self.targets[idx].label} — "
                    "calibration will fail at end if quality gates reject fit"
                )
        self._target_index += 1
        if not self.is_finished:
            self.begin_target()

    def _finalize_target_training_feature(self, idx: int) -> None:
        """Compute and store a single mean feature vector for this target."""
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
            m = (values >= lo) & (values <= hi)
            kept = values[m]
            return kept if kept.size else values

        def mean_opt(vals: List[Optional[float]]) -> Optional[float]:
            xs = np.array([v for v in vals if v is not None and np.isfinite(float(v))], dtype=np.float64)
            if xs.size == 0:
                return None
            xs = iqr_filter(xs)
            if xs.size == 0:
                return None
            return float(np.mean(xs))

        # Mean in legacy ratio-space (used by IDW baselines + gating metrics).
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
        """How many accepted per-frame ratio samples were used for this target mean."""
        if idx < 0 or idx >= len(self.targets):
            return 0
        return len(self._accepted_ratios[idx])

    def target_means_count(self) -> int:
        """How many target means have been finalized so far."""
        return sum(1 for frames in self._accepted_features if len(frames) > 0)

    def target_mean_ready(self, idx: int) -> bool:
        """Whether current target has enough stable samples to finalize a mean."""
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
        """Log per-target mean features with horizontal and vertical signals separated."""
        print("[calib2] --- per-target training means (u/v per eye) ---")
        print(
            "[calib2] "
            f"{'id':<4} {'label':<14} {'screen':>12} "
            f"{'uL':>8} {'vL':>8} {'uR':>8} {'vR':>8} {'avg_v':>8}"
        )
        for i, t in enumerate(self.targets):
            frames = self._accepted_features[i]
            if not frames:
                print(f"[calib2] T{i+1:02d} {t.label:<14} (no mean)")
                continue
            f = frames[-1]

            def _f(v: Optional[float]) -> str:
                return f"{float(v):8.4f}" if v is not None else "     n/a"

            print(
                "[calib2] "
                f"T{i+1:02d} {t.label:<14} "
                f"({int(t.screen_x):4d},{int(t.screen_y):4d}) "
                f"{_f(f.pca_uL)} {_f(f.pca_vL)} {_f(f.pca_uR)} {_f(f.pca_vR)} {_f(f.avg_v)}"
            )

    def get_training_samples(self) -> List[Tuple[FrameFeatures, Tuple[float, float]]]:
        """
        Return per-target training pairs suitable for `IDWRatioMapper.fit`.

        Each completed target yields one window-mean feature vector paired with its
        target screen point (global coords).
        """
        out: List[Tuple[FrameFeatures, Tuple[float, float]]] = []
        for t, frames in zip(self.targets, self._accepted_features):
            p = (float(t.screen_x), float(t.screen_y))
            for f in frames:
                out.append((f, p))
        return out

    def write_summary(
        self,
        *,
        mapper_type: str,
        per_target_error_px: Optional[List[Optional[float]]] = None,
        overall_rms_px: Optional[float] = None,
    ) -> None:
        """Write calibration summary after mapper fit (so we can store error metrics)."""
        per_target_error_px = per_target_error_px or [None for _ in self.targets]
        # Per-target rows.
        for i, t in enumerate(self.targets):
            samples = self._accepted_ratios[i]
            err = per_target_error_px[i] if i < len(per_target_error_px) else None
            # A simple quality score: inverse of avg(std_h,std_v) in ratio space.
            if samples:
                xs = np.array([p[0] for p in samples], dtype=np.float64)
                ys = np.array([p[1] for p in samples], dtype=np.float64)
                std = max(float(np.std(xs)), float(np.std(ys)))
                quality = float(1.0 / (1e-6 + std))
            else:
                quality = None

            self.csv.log_summary(
                CalibrationSummaryRow(
                    calibration_version=self.calibration_version,
                    session_id=self.csv.session_id,
                    record_type="target",
                    target_id=t.target_id,
                    target_label=t.label,
                    target_screen_x=t.screen_x,
                    target_screen_y=t.screen_y,
                    n_seen=len(samples),
                    n_accepted=len(samples),
                    n_rejected=0,
                    quality_score=quality,
                    estimated_error_px=err,
                    mapper_type=mapper_type,
                    calibration_mode=self.calibration_mode,
                )
            )

        # Overall row.
        self.csv.log_summary(
            CalibrationSummaryRow(
                calibration_version=self.calibration_version,
                session_id=self.csv.session_id,
                record_type="overall",
                target_id="",
                target_label="",
                target_screen_x=None,
                target_screen_y=None,
                n_seen=sum(len(s) for s in self._accepted_ratios),
                n_accepted=sum(len(s) for s in self._accepted_ratios),
                n_rejected=0,
                quality_score=None,
                estimated_error_px=overall_rms_px,
                mapper_type=mapper_type,
                calibration_mode=self.calibration_mode,
            )
        )
        # Write once at the end.
        self.csv.flush_summary(overwrite=True)

