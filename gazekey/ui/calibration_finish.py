"""Post-session calibration finish: product fit + UI only (artifacts via tools)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from gazekey.calibration.session import CalibrationResult
from gazekey.mapping.config import TYPING_CANDIDATE_ID
from gazekey.mvp_log import mvp_log

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class CalibrationFinishController:
    """Handles calibration session finish after fixation collection."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._host = host

    def on_finished(self, result) -> None:
        h = self._host
        h._is_calibrating = False
        if h._calibration_overlay is not None:
            try:
                h._calibration_overlay.hide()
                h._calibration_overlay.close()
            except Exception:
                pass
        h._calibration_overlay = None
        h._locked_frame_size = None
        h._set_camera_preview_blocked(False)

        if not isinstance(result, CalibrationResult):
            h._log_verbose(f"[calib] unexpected result type: {type(result)}")
            return

        if not result.success:
            h._log_verbose(f"[calib] failed: {result.message}")
            h._devtools.on_calibration_failed_artifacts(h, failure_reason=result.message)
            return

        if h._calibration_session is None:
            h._log_verbose("[calib] missing session at finish")
            h._devtools.on_calibration_failed_artifacts(h, failure_reason="missing_session")
            return

        missing = [
            i
            for i in range(len(h._calibration_session.targets))
            if h._calibration_session.accepted_count_for_target(i) <= 0
        ]
        if missing:
            h._log_verbose(f"[calib] not fitting mapper: missing accepted samples for targets {missing}")
            h._devtools.on_calibration_failed_artifacts(
                h, failure_reason=f"missing_samples targets={missing}"
            )
            return

        try:
            h._calibration_session.print_training_means()
        except Exception as e:
            h._log_verbose(f"[calib] training means print failed: {e}")

        samples = h._calibration_session.get_training_samples()

        try:
            h_vals = [float(s.avg_h) for (s, _p) in samples if s.avg_h is not None]
            v_vals = [float(s.avg_v) for (s, _p) in samples if s.avg_v is not None]
            if h_vals and v_vals:
                span_h = float(max(h_vals) - min(h_vals))
                span_v = float(max(v_vals) - min(v_vals))
                h._log_verbose(f"[diag] avg_h range: {min(h_vals):.3f}-{max(h_vals):.3f} span={span_h:.3f}")
                h._log_verbose(f"[diag] avg_v range: {min(v_vals):.3f}-{max(v_vals):.3f} span={span_v:.3f}")
                h._log_verbose(f"[diag] pca features sample[0]: {samples[0][0]}")
                min_span = 0.06 if str(h._calib_mode).startswith("keyboard") else 0.15
                if span_v < min_span or span_h < min_span:
                    h._log_verbose(
                        f"[diag] WARNING: feature span small (h={span_h:.3f} v={span_v:.3f}) "
                        f"— quality gates may fail"
                    )
        except Exception as e:
            h._log_verbose(f"[diag] pre-fit diagnostics failed: {e}")

        screen_rect_fit = h._mapper_runtime.screen_rect_for_fit()
        outcome = h._mapper_runtime.complete_calibration_fit(
            samples=samples,
            screen_rect_fit=screen_rect_fit,
        )
        ridge_fit = outcome.ridge_fit
        ridge_loocv_detail = outcome.ridge_loocv_detail
        ridge_alpha = outcome.ridge_alpha
        quality = outcome.quality
        fit = ridge_fit

        if outcome.ridge_fit_failed:
            h._log_verbose(f"[calib] ridge fit failed: {outcome.failure_reason}")
            h._preview_mode = False
            h._set_post_calibration_controls(False)
            h._devtools.on_calibration_failed_artifacts(h, failure_reason=outcome.failure_reason)
            h._show_recalibrate_prompt(
                "Calibration could not find a reliable mapper — keep head still, eyes on each dot"
            )
            return

        if outcome.quality_blocked:
            mvp_log(
                "[calib] RECALIBRATE: calibration not usable — mapper not activated",
                always=True,
            )
            for reason in quality.reasons:
                h._log_verbose(f"[calib]   reason: {reason}")
            h._preview_mode = False
            h._set_post_calibration_controls(False)
            h._devtools.on_calibration_failed_artifacts(
                h,
                failure_reason=outcome.failure_reason,
                loocv_rms_px=quality.loocv_rms_px,
                ridge_alpha=ridge_alpha,
                quality_warnings=quality.warnings,
                ridge_fit=ridge_fit,
                loocv_detail=ridge_loocv_detail,
            )
            h._show_recalibrate_prompt(
                "Calibration failed — keep head still, move eyes only, then tap RECALIBRATE"
            )
            try:
                self.print_target_sample_quality()
            except Exception:
                pass
            return

        h._devtools.on_calibration_artifacts(
            h,
            ridge_fit=ridge_fit,
            loocv_detail=ridge_loocv_detail,
            quality=quality,
            ridge_alpha=ridge_alpha,
        )
        h._set_post_calibration_controls(True)
        h._last_v2_pred_x = None
        h._last_v2_pred_y = None
        h._last_v2_pred_t = None

        h._reset_calibrate_button_style()
        status_suffix = " (best-effort)" if getattr(ridge_fit, "best_effort", False) else ""
        h.camera_status_label.setText(f"📷 Calibration saved ✓{status_suffix}")
        h.camera_status_label.setStyleSheet("""
            QLabel {
                color: #10B981;
                padding: 5px;
                font-weight: bold;
            }
        """)
        h._log_verbose(
            f"[calib] complete. Mapper ready ({TYPING_CANDIDATE_ID}: {h._active_mapper})."
        )
        mapper_type = getattr(h._gaze_mapper, "mapper_type", "unknown")
        runtime_line = (
            "[runtime] "
            f"typing_candidate={TYPING_CANDIDATE_ID} "
            f"mapper_mode={h._mapper_mode or h._calib_mode} "
            f"active_mapper={h._active_mapper} "
            f"mapper_type={mapper_type} "
            f"LOOCV_RMS={quality.loocv_rms_px}"
        )
        if quality.screen_y_avg_v_corr is not None:
            runtime_line += f" corr(screen_y,avg_v)={float(quality.screen_y_avg_v_corr):.3f}"
        if quality.warnings:
            runtime_line += f" calibration_warnings={len(quality.warnings)}"
        h._log_verbose(runtime_line)
        for w in quality.warnings:
            h._log_verbose(f"[runtime]   warning: {w}")

        # Product does not require preview mode. Tools entries may opt in.
        if getattr(h, "_tools_auto_preview_after_calib", False):
            enable = getattr(h._devtools, "enable_preview_mode", None)
            if callable(enable):
                enable()
            try:
                if h.is_expanded:
                    h._ensure_camera_preview(show=True)
            except Exception:
                pass
            h._devtools.maybe_start_dev_benchmark()
        else:
            h._preview_mode = False

        try:
            self.print_target_sample_quality()
        except Exception as e:
            h._log_verbose(f"[calib] per-target sample diagnostics failed: {e}")

        del fit  # fit already applied via mapper_runtime

    def write_run_summary(self, **kwargs) -> None:
        """Compatibility shim — delegates to installed tools (no-op on product path)."""
        self._host._devtools.write_calibration_summary(**kwargs)

    def print_target_sample_quality(self) -> None:
        import numpy as np

        h = self._host
        if h._calibration_session is None:
            return
        sess = h._calibration_session

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

        max_std = float(getattr(sess.gate.cfg, "max_std", 0.045))
        for i, t in enumerate(sess.targets):
            ratios = sess._accepted_ratios[i]  # noqa: SLF001
            hs = np.array([p[0] for p in ratios], dtype=np.float64) if ratios else np.array([], dtype=np.float64)
            vs = np.array([p[1] for p in ratios], dtype=np.float64) if ratios else np.array([], dtype=np.float64)
            hs_f = iqr_filter(hs)
            vs_f = iqr_filter(vs)

            raw_n = int(hs.size)
            filt_n = int(min(hs_f.size, vs_f.size))
            if raw_n > 0:
                mu_h = float(np.mean(hs))
                mu_v = float(np.mean(vs))
                sd_h = float(np.std(hs))
                sd_v = float(np.std(vs))
                noisy = bool(max(sd_h, sd_v) > max_std)
            else:
                mu_h = mu_v = sd_h = sd_v = 0.0
                noisy = True

            h._log_verbose(
                "[calib] target samples: "
                f"T{i+1:02d} label={t.label} "
                f"raw_n={raw_n} filt_n={filt_n} "
                f"avg_h(mean={mu_h:.4f} std={sd_h:.4f}) "
                f"avg_v(mean={mu_v:.4f} std={sd_v:.4f}) "
                f"noisy={noisy}"
            )

    # ---- tools-compat stubs (real work lives in tools when installed) ----

    def write_mapper_snapshot(self, *, ridge_fit) -> None:
        arts = getattr(self._host._devtools, "_artifacts", None)
        if arts is not None:
            arts.write_mapper_snapshot(ridge_fit=ridge_fit)

    def write_coverage_diagnostic(self) -> None:
        arts = getattr(self._host._devtools, "_artifacts", None)
        if arts is not None:
            arts.write_coverage_diagnostic()

    def show_geometry_overlay(self, *, samples, model, loocv_detail) -> None:
        arts = getattr(self._host._devtools, "_artifacts", None)
        if arts is not None:
            arts.show_geometry_overlay(samples=samples, model=model, loocv_detail=loocv_detail)

    def reset_debug_csvs(self) -> None:
        arts = getattr(self._host._devtools, "_artifacts", None)
        if arts is not None:
            arts.reset_debug_csvs()

    def write_debug_csv(self, *, ridge_fit, loocv_detail) -> None:
        arts = getattr(self._host._devtools, "_artifacts", None)
        if arts is not None:
            arts.write_debug_csv(ridge_fit=ridge_fit, loocv_detail=loocv_detail)

    def print_row_v_stats_and_export_ratio_space(self) -> None:
        arts = getattr(self._host._devtools, "_artifacts", None)
        if arts is not None:
            arts.print_row_v_stats_and_export_ratio_space()
