"""Post-calibration mapper fit, store, and runtime predict/clamp (T048)."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

import numpy as np
from PySide6.QtWidgets import QApplication

from gazekey.calibration2.mapper_store import MapperStore
from gazekey.calibration2.quality import assess_fullscreen_feasibility, evaluate_calibration_quality
from gazekey.features import FeatureExtractor
from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping import fit_calibration_mapper
from gazekey.mapping.base import MapperPrediction
from gazekey.mapping.ridge import MapperCandidateReport
from gazekey.mapping.typing_candidate import (
    HALF_KEY_HEIGHT_PX,
    MAX_HEAD_DRIFT_EYE_H,
    MAX_LOOCV_RMS_PX,
    MAX_OFF_SCREEN_LOOCV,
    MAX_SINGLE_TARGET_TRAIN_PX,
    MAX_TARGET_LOOCV_PX,
    MAX_TRAIN_ERROR_PX,
    MAX_VALIDATION_ERROR_PX,
    MIN_ALPHA,
    MIN_AVG_V_ROW_SEPARATION,
    MIN_CATASTROPHIC_SCREEN_Y_AVG_V_CORR,
    MIN_SCREEN_Y_AVG_V_CORR,
)

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


@dataclass
class CalibrationFitOutcome:
    """Result of post-calibration mapper fit (no UI side effects)."""

    ridge_fit: Any
    quality: Any
    ridge_alpha: float
    ridge_loocv_detail: Optional[list]
    per_target_err: Optional[list]
    loocv_rms: Optional[float]
    ridge_fit_failed: bool = False
    quality_blocked: bool = False
    failure_reason: Optional[str] = None
    model_assigned: bool = False


class MapperRuntime:
    """Owns fitted mapper, mapper store, and shared predict/clamp helpers."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._host = host
        self._store = MapperStore()
        self.model: Any = None
        self.last_calib_samples: list = []
        self.last_candidate_reports: tuple[MapperCandidateReport, ...] = ()
        self.last_calibration_loocv_rms: Optional[float] = None

    @property
    def store(self) -> MapperStore:
        return self._store

    def usable(self) -> bool:
        return self.model is not None

    def clear_model(self) -> None:
        self.model = None

    def screen_rect_for_fit(self) -> tuple[float, float, float, float]:
        h = self._host
        clip_rect = getattr(h, "_calib_clip_rect", None)
        if clip_rect is not None:
            h._log_verbose(f"[calib2] mapper clip bounds: keyboard region {clip_rect}")
            return clip_rect
        screen = QApplication.primaryScreen().geometry()
        return (
            float(screen.x()),
            float(screen.y()),
            float(screen.width()),
            float(screen.height()),
        )

    def complete_calibration_fit(
        self,
        *,
        samples: list,
        screen_rect_fit: tuple[float, float, float, float],
    ) -> CalibrationFitOutcome:
        """Fit PCA4 mapper, evaluate quality gates, assign model on success."""
        h = self._host
        h._log_verbose(f"[calib2] fitting mapper with {len(samples)} target-mean samples")

        ridge_fit = fit_calibration_mapper(
            samples=samples,
            targets=h._calibration_v2_session.targets,
            calibration_mode=str(h._calib2_mode),
            screen_rect=screen_rect_fit,
            min_alpha=MIN_ALPHA,
            max_loocv_rms_px=MAX_LOOCV_RMS_PX,
            max_target_loocv_px=MAX_TARGET_LOOCV_PX,
            max_train_error_px=MAX_TRAIN_ERROR_PX,
            half_key_height_px=HALF_KEY_HEIGHT_PX,
        )
        self.last_calib_samples = list(samples)
        self.last_candidate_reports = tuple(
            r for r in (ridge_fit.candidate_reports or ()) if isinstance(r, MapperCandidateReport)
        )
        h._last_mapper_candidate_reports = self.last_candidate_reports
        h._last_calib_samples = self.last_calib_samples

        h._log_verbose(
            f"[calib2] mapper fit: success={ridge_fit.success} rms_px={ridge_fit.rms_px} "
            f"msg={ridge_fit.message}"
        )
        if not ridge_fit.success or ridge_fit.model is None:
            self.clear_model()
            return CalibrationFitOutcome(
                ridge_fit=ridge_fit,
                quality=None,
                ridge_alpha=0.0,
                ridge_loocv_detail=None,
                per_target_err=None,
                loocv_rms=None,
                ridge_fit_failed=True,
                failure_reason=ridge_fit.message,
            )

        ridge_alpha, ridge_loocv_detail, per_target_err, loocv_rms = self._ridge_loocv_diagnostics(
            h, ridge_fit
        )
        self._log_ridge_summary(h, ridge_fit, ridge_alpha, loocv_rms, ridge_loocv_detail)

        selected_type = getattr(ridge_fit.model, "mapper_type", "unknown")
        h._log_verbose(f"[calib2] active_mapper={selected_type}")
        h._active_mapper = str(selected_type)

        quality = evaluate_calibration_quality(
            model=ridge_fit.model,
            samples=samples,
            targets=h._calibration_v2_session.targets,
            screen_rect=screen_rect_fit,
            calibration_mode=str(h._calib2_mode),
            loocv_detail=ridge_loocv_detail,
            max_validation_error_px=MAX_VALIDATION_ERROR_PX,
            max_train_error_px=MAX_TRAIN_ERROR_PX,
            max_loocv_rms_px=MAX_LOOCV_RMS_PX,
            max_target_loocv_px=MAX_TARGET_LOOCV_PX,
            max_off_screen_loocv=MAX_OFF_SCREEN_LOOCV,
            min_screen_y_avg_v_corr=MIN_SCREEN_Y_AVG_V_CORR,
            min_catastrophic_screen_y_avg_v_corr=MIN_CATASTROPHIC_SCREEN_Y_AVG_V_CORR,
            max_single_target_train_px=MAX_SINGLE_TARGET_TRAIN_PX,
            max_head_drift_eye_h=MAX_HEAD_DRIFT_EYE_H,
            min_avg_v_row_separation=MIN_AVG_V_ROW_SEPARATION,
        )
        try:
            assess_fullscreen_feasibility(
                row_stats=quality.row_stats,
                monotonicity=quality.monotonicity,
                loocv_rms_px=quality.loocv_rms_px,
            )
        except Exception as e:
            h._log_verbose(f"[calib2] feasibility assessment failed: {e}")

        if not quality.usable:
            gate_reason = "; ".join(quality.reasons[:3]) if quality.reasons else "calibration_not_usable"
            self.clear_model()
            return CalibrationFitOutcome(
                ridge_fit=ridge_fit,
                quality=quality,
                ridge_alpha=ridge_alpha,
                ridge_loocv_detail=ridge_loocv_detail,
                per_target_err=per_target_err,
                loocv_rms=loocv_rms,
                quality_blocked=True,
                failure_reason=gate_reason,
            )

        self.model = ridge_fit.model
        self.last_calibration_loocv_rms = quality.loocv_rms_px
        h._last_calibration_loocv_rms = self.last_calibration_loocv_rms
        try:
            self._store.save(
                ridge_fit.model,
                calibration_mode=str(h._calib2_mode),
                mapper_mode=str(h._mapper_mode or h._calib2_mode),
            )
        except Exception as e:
            h._log_verbose(f"[calib2] v2 mapper save failed: {e}")

        h._gaze_smoother.reset()
        h._feature_smoother.reset()
        h._gaze_bias_x = 0.0
        h._gaze_bias_y = 0.0

        return CalibrationFitOutcome(
            ridge_fit=ridge_fit,
            quality=quality,
            ridge_alpha=ridge_alpha,
            ridge_loocv_detail=ridge_loocv_detail,
            per_target_err=per_target_err,
            loocv_rms=loocv_rms,
            model_assigned=True,
        )

    @staticmethod
    def _ridge_loocv_diagnostics(host, ridge_fit) -> tuple[float, Optional[list], Optional[list], Optional[float]]:
        ridge_alpha = float(getattr(ridge_fit.model, "alpha", 0.0))
        ridge_per_target_err = None
        ridge_loocv_rms = None
        ridge_loocv_detail = None
        try:
            ridge_loocv_detail = ridge_fit.model.leave_one_out_detail_px()
            ridge_per_target_err = [float(d["err"]) for d in ridge_loocv_detail]
            ridge_loocv_rms = (
                float(np.sqrt(np.mean(np.array(ridge_per_target_err, dtype=np.float64) ** 2)))
                if ridge_per_target_err
                else None
            )
        except Exception as e:
            host._log_verbose(f"[calib2] ridge LOOCV compute failed: {e}")
        return ridge_alpha, ridge_loocv_detail, ridge_per_target_err, ridge_loocv_rms

    @staticmethod
    def _log_ridge_summary(host, ridge_fit, ridge_alpha, loocv_rms, ridge_loocv_detail) -> None:
        try:
            feature_count = int(getattr(ridge_fit.model, "train_X", np.zeros((0, 0))).shape[1])
            sample_count = int(getattr(ridge_fit.model, "train_X", np.zeros((0, 0))).shape[0])
        except Exception:
            feature_count = 0
            sample_count = 0
        ridge_train_rms = float(ridge_fit.rms_px) if ridge_fit.rms_px is not None else None
        host._log_verbose(
            f"[calib2] ridge diag: feature_count={feature_count} sample_count={sample_count} "
            f"alpha={ridge_alpha} training_RMS={ridge_train_rms} LOOCV_RMS={loocv_rms}"
        )
        if loocv_rms is not None:
            host._log_verbose(f"[calib2] pca_ridge: LOOCV_RMS={float(loocv_rms):.1f}px")
        else:
            host._log_verbose("[calib2] pca_ridge: LOOCV_RMS=(unavailable)")
        if ridge_loocv_detail:
            worst = sorted([(float(d["err"]), int(d["i"])) for d in ridge_loocv_detail], reverse=True)[:4]
            ridge_worst_str = ", ".join([f"T{i+1:02d}={e:.1f}px" for e, i in worst])
            host._log_verbose(f"[calib2] pca_ridge: LOOCV worst targets: {ridge_worst_str}")
        try:
            if ridge_loocv_detail is not None and host._calibration_v2_session is not None:
                sess = host._calibration_v2_session
                worst = sorted(ridge_loocv_detail, key=lambda d: float(d["err"]), reverse=True)[:4]
                for d in worst:
                    i = int(d["i"])
                    t = sess.targets[i] if i < len(sess.targets) else None
                    label = t.label if t is not None else "?"
                    tx = float(t.screen_x) if t is not None else float("nan")
                    ty = float(t.screen_y) if t is not None else float("nan")
                    host._log_verbose(
                        "[calib2] loocv worst: "
                        f"T{i+1:02d} label={label} "
                        f"target=({tx:.1f},{ty:.1f}) "
                        f"pred=({float(d['pred_x']):.1f},{float(d['pred_y']):.1f}) "
                        f"err={float(d['err']):.1f}px"
                    )
        except Exception as e:
            host._log_verbose(f"[calib2] loocv worst detail print failed: {e}")

    @staticmethod
    def with_avg(features: FrameFeatures, *, avg_h, avg_v) -> FrameFeatures:
        return type(features)(
            timestamp_ms=features.timestamp_ms,
            face_detected=features.face_detected,
            blink=features.blink,
            confidence=features.confidence,
            Lh=features.Lh,
            Lv=features.Lv,
            Rh=features.Rh,
            Rv=features.Rv,
            avg_h=avg_h,
            avg_v=avg_v,
            eye_box_w=features.eye_box_w,
            eye_box_h=features.eye_box_h,
            face_x=features.face_x,
            face_y=features.face_y,
        )

    def clamp_xy(self, x: float, y: float) -> Tuple[float, float]:
        h = self._host
        bounds = getattr(self.model, "clip_bounds", None) if self.model else None
        if bounds is not None:
            x0, y0, x1, y1 = bounds
            return (
                float(max(x0, min(x1, x))),
                float(max(y0, min(y1, y))),
            )
        if h._rt2_clamp_to_screen:
            screen = QApplication.primaryScreen().geometry()
            return (
                float(max(float(screen.left()), min(float(screen.right()), x))),
                float(max(float(screen.top()), min(float(screen.bottom()), y))),
            )
        return x, y

    def predict_gaze_v2(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        h = self._host
        if self.model is None:
            return None
        smooth = h._feature_smoother.smooth(features)
        pred = self.model.predict(smooth)
        if pred is None:
            return None
        if pred.quality is not None and float(pred.quality) < float(h._rt2_min_quality):
            return None
        px = float(pred.x) + float(h._gaze_bias_x)
        py = float(pred.y) + float(h._gaze_bias_y)
        px, py = self.clamp_xy(px, py)
        return replace(pred, x=px, y=py)

    def key_accuracy_predict_screen_xy(self, raw: FrameFeatures) -> Optional[Tuple[float, float]]:
        """Shared keyboard-accuracy predict path (live session + compare replay)."""
        h = self._host
        if self.model is None:
            return None
        smooth = h._feature_smoother.smooth(raw)
        pred = self.model.predict(smooth)
        if pred is None:
            return None
        if pred.quality is not None and float(pred.quality) < float(h._rt2_min_quality):
            return None
        px = float(pred.x) + float(h._gaze_bias_x)
        py = float(pred.y) + float(h._gaze_bias_y)
        px, py = self.clamp_xy(px, py)
        return px, py

    def map_gaze_screen_xy(
        self, eye_data, *, now_ms: int
    ) -> Tuple[Optional[float], Optional[float], Optional[Tuple[float, float]]]:
        """Predict and smooth gaze; returns (x, y, raw_global) or Nones."""
        h = self._host
        features = FeatureExtractor.from_eye_data(eye_data, timestamp_ms=now_ms)
        mapped_x = mapped_y = None
        if self.model is not None:
            pred = self.predict_gaze_v2(features)
            if pred is not None:
                mapped_x = float(pred.x)
                mapped_y = float(pred.y)
                h._last_raw_mapped_x = mapped_x
                h._last_raw_mapped_y = mapped_y
                h._last_v2_pred_x = mapped_x
                h._last_v2_pred_y = mapped_y
                h._last_v2_pred_t = now_ms
                if h._rt2_debug and h._rt2_debug_pred:
                    h._log_verbose(
                        f"[rt2] pred x={mapped_x:.1f} y={mapped_y:.1f} "
                        f"q={float(pred.quality) if pred.quality is not None else 0:.2f}"
                    )
            else:
                grace_ms = 220
                if (
                    h._last_v2_pred_x is not None
                    and h._last_v2_pred_y is not None
                    and h._last_v2_pred_t is not None
                    and (now_ms - h._last_v2_pred_t) <= grace_ms
                ):
                    mapped_x = float(h._last_v2_pred_x)
                    mapped_y = float(h._last_v2_pred_y)
                else:
                    return None, None, None

        if mapped_x is None or mapped_y is None:
            return None, None, None

        raw_global = None
        if h._last_raw_mapped_x is not None and h._last_raw_mapped_y is not None:
            raw_global = (float(h._last_raw_mapped_x), float(h._last_raw_mapped_y))

        mapped_x, mapped_y = h._gaze_smoother.filter(mapped_x, mapped_y)
        return mapped_x, mapped_y, raw_global
