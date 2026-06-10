"""Post-session calibration finish: fit orchestration, summaries, debug exports (T051)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import numpy as np
from PySide6.QtCore import QTimer

from gazekey.debug.calibration_geometry_diagnostics import print_geometric_diagnostics
from gazekey.calibration.session import CalibrationResult
from gazekey.evaluation.coverage_diagnostics import build_coverage_report, write_coverage_diagnostics
from gazekey.debug.mapper_store import save_calibration_mapper
from gazekey.evaluation.session_paths import (
    CALIBRATION_DEBUG_CSV,
    CALIBRATION_RATIO_SPACE_CSV,
    CALIBRATION_V2_FILE,
    KEYBOARD_LAYOUT_FILE,
    ensure_session_dir,
)
from gazekey.layout import inspect_keyboard_layout
from gazekey.mapping.config import CALIBRATION_MODE, TYPING_CANDIDATE_ID
from gazekey.mvp_log import mvp_log
from gazekey.debug.calibration_geometry_overlay import CalibrationGeometryOverlay
from gazekey.ui.env_flags import calib_geom_debug

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
            self.write_run_summary(passed=False, failure_reason=result.message)
            return

        if h._calibration_session is None:
            h._log_verbose("[calib] missing session at finish")
            self.write_run_summary(passed=False, failure_reason="missing_session")
            return

        missing = [
            i
            for i in range(len(h._calibration_session.targets))
            if h._calibration_session.accepted_count_for_target(i) <= 0
        ]
        if missing:
            h._log_verbose(f"[calib] not fitting mapper: missing accepted samples for targets {missing}")
            self.write_run_summary(
                passed=False,
                failure_reason=f"missing_samples targets={missing}",
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
        per_target_err = outcome.per_target_err
        loocv_rms = outcome.loocv_rms
        fit = ridge_fit

        if outcome.ridge_fit_failed:
            h._log_verbose(f"[calib] ridge fit failed: {outcome.failure_reason}")
            h._preview_mode = False
            h._set_post_calibration_controls(False)
            self.write_run_summary(passed=False, failure_reason=outcome.failure_reason)
            h._show_recalibrate_prompt(
                "Calibration could not find a reliable mapper — keep head still, eyes on each dot"
            )
            return

        try:
            self.print_row_v_stats_and_export_ratio_space()
        except Exception as e:
            h._log_verbose(f"[calib] ratio-space stats/export failed: {e}")

        quality = outcome.quality
        try:
            print_geometric_diagnostics(
                model=ridge_fit.model,
                samples=samples,
                targets=h._calibration_session.targets,
                loocv_detail=ridge_loocv_detail,
                keys=h._layout_keys or inspect_keyboard_layout(h.keyboard_widget),
            )
        except Exception as e:
            h._log_verbose(f"[calib] geometric diagnostics failed: {e}")

        if calib_geom_debug(calib_debug_cached=h._calib_debug):
            try:
                self.show_geometry_overlay(
                    samples=samples,
                    model=ridge_fit.model,
                    loocv_detail=ridge_loocv_detail,
                )
            except Exception as e:
                h._log_verbose(f"[calib] geometry overlay failed: {e}")

        if outcome.quality_blocked:
            mvp_log(
                "[calib] RECALIBRATE: calibration not usable — preview/benchmark blocked",
                always=True,
            )
            for reason in quality.reasons:
                h._log_verbose(f"[calib]   reason: {reason}")
            h._preview_mode = False
            h._set_post_calibration_controls(False)
            self.write_run_summary(
                passed=False,
                failure_reason=outcome.failure_reason,
                loocv_rms_px=quality.loocv_rms_px,
                ridge_alpha=ridge_alpha,
                quality_warnings=quality.warnings,
            )
            h._show_recalibrate_prompt(
                "Calibration failed — keep head still, move eyes only, then tap RECALIBRATE"
            )
            try:
                self.write_mapper_snapshot(ridge_fit=ridge_fit)
                self.write_debug_csv(ridge_fit=ridge_fit, loocv_detail=ridge_loocv_detail)
                self.print_target_sample_quality()
            except Exception:
                pass
            return

        self.write_run_summary(
            passed=True,
            loocv_rms_px=quality.loocv_rms_px,
            ridge_alpha=ridge_alpha,
            quality_warnings=quality.warnings,
        )
        self.write_mapper_snapshot(ridge_fit=ridge_fit)
        h._set_post_calibration_controls(True)
        self.write_coverage_diagnostic()
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
            f"[calib] complete. Read-only gaze preview enabled ({TYPING_CANDIDATE_ID}: "
            f"{h._active_mapper})."
        )
        h._log_verbose("[preview] Gaze dot tracks mapped position; keys are not activated (MVP).")
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
        h._preview_mode = True
        if hasattr(h, "preview_btn"):
            h.preview_btn.setProperty("active", "true")
            h.preview_btn.style().unpolish(h.preview_btn)
            h.preview_btn.style().polish(h.preview_btn)
            h.preview_btn.update()
        try:
            if h.is_expanded:
                h._ensure_camera_preview(show=True)
        except Exception:
            pass

        if h._dev_benchmark_enabled():
            QTimer.singleShot(150, h._maybe_start_dev_benchmark)

        try:
            self.write_debug_csv(ridge_fit=ridge_fit, loocv_detail=ridge_loocv_detail)
        except Exception as e:
            h._log_verbose(f"[calib] calibration_debug.csv write failed: {e}")

        try:
            self.print_target_sample_quality()
        except Exception as e:
            h._log_verbose(f"[calib] per-target sample diagnostics failed: {e}")

    def write_run_summary(
        self,
        *,
        passed: bool,
        failure_reason: Optional[str] = None,
        loocv_rms_px: Optional[float] = None,
        ridge_alpha: Optional[float] = None,
        quality_warnings: Optional[list[str]] = None,
    ) -> None:
        h = self._host
        session = h._calibration_session
        if session is None:
            return
        collected = sum(
            1 for i in range(len(session.targets)) if session.accepted_count_for_target(i) > 0
        )
        h._run_summary_writer.write_calibration_summary(
            session_id=h._calibration_controller.session_id or session.session_id,
            status="passed" if passed else "failed",
            layout=str(h._calib_mode or CALIBRATION_MODE),
            targets_collected=collected,
            targets_total=len(session.targets),
            failure_reason=failure_reason,
            loocv_rms_px=loocv_rms_px,
            ridge_alpha=ridge_alpha,
            quality_warnings=quality_warnings,
        )

    def write_mapper_snapshot(self, *, ridge_fit) -> None:
        h = self._host
        if ridge_fit is None or ridge_fit.model is None:
            return
        session_id = h._calibration_controller.session_id
        if not session_id and h._calibration_session is not None:
            session_id = h._calibration_session.session_id
        if not session_id:
            return
        try:
            path = save_calibration_mapper(
                ridge_fit.model,
                session_id=session_id,
                calibration_mode=str(h._calib_mode or CALIBRATION_MODE),
                mapper_mode=str(h._mapper_mode or h._calib_mode or CALIBRATION_MODE),
                runs_dir=h._run_summary_writer.runs_dir,
            )
            h._log_verbose(f"[calib] wrote {path.name} under runs/{session_id}/")
        except Exception as e:
            h._log_verbose(f"[calib] mapper snapshot write failed: {e}")

    def write_coverage_diagnostic(self) -> None:
        h = self._host
        try:
            session = h._calibration_session
            if session is None or not session.targets:
                return
            anchors = [(float(t.screen_x), float(t.screen_y)) for t in session.targets]
            layout_keys = h._layout_keys or inspect_keyboard_layout(h.keyboard_widget)
            keys = [
                {
                    "key_label": str(k.key_label),
                    "key_action": str(k.key_action),
                    "x": float(k.center[0]),
                    "y": float(k.center[1]),
                    "row_index": int(k.row_index),
                    "is_special": bool(k.is_special_key),
                }
                for k in layout_keys
            ]
            if not keys:
                return
            session_id = h._calibration_controller.session_id or session.session_id
            report = build_coverage_report(
                anchors=anchors,
                keys=keys,
                calibration_mode=str(h._calib_mode or CALIBRATION_MODE),
                session_id=str(session_id),
            )
            path = write_coverage_diagnostics(
                report,
                session_id=str(session_id),
                runs_dir=str(h._run_summary_writer.runs_dir),
            )
            cov = report["overall"]
            h._log_verbose(
                f"[calib] coverage diag -> {path} "
                f"({cov['n_inside_hull']}/{cov['n_keys']} keys inside hull)"
            )
        except Exception as e:
            h._log_verbose(f"[calib] coverage diagnostic failed: {e}")

    def show_geometry_overlay(self, *, samples, model, loocv_detail) -> None:
        h = self._host
        if h._calibration_session is None:
            return
        targets = h._calibration_session.targets
        expected = [(float(t.screen_x), float(t.screen_y)) for t in targets]
        labels = [str(t.label) for t in targets]
        train_pred: list = []
        loocv_pred: list = []
        loocv_by_i = {int(d["i"]): d for d in (loocv_detail or [])}
        for i, (feat, _xy) in enumerate(samples):
            pred = model.predict(feat)
            train_pred.append((float(pred.x), float(pred.y)) if pred is not None else None)
            d = loocv_by_i.get(i)
            if d is not None:
                loocv_pred.append((float(d["pred_x"]), float(d["pred_y"])))
            else:
                loocv_pred.append(None)
        ov = CalibrationGeometryOverlay(
            expected=expected,
            train_pred=train_pred,
            loocv_pred=loocv_pred,
            labels=labels,
        )
        ov.show()
        ov.raise_()
        h._log_verbose("[calib] geometry overlay shown (green=target blue=train orange=LOOCV)")

    def _session_artifact_dir(self) -> Path:
        h = self._host
        session_id = h._calibration_controller.session_id
        if not session_id and h._calibration_session is not None:
            session_id = h._calibration_session.session_id
        return ensure_session_dir(session_id or "unknown", runs_dir=h._run_summary_writer.runs_dir)

    def reset_debug_csvs(self) -> None:
        h = self._host
        root = Path(__file__).resolve().parents[2]
        legacy_names = (
            CALIBRATION_DEBUG_CSV,
            CALIBRATION_RATIO_SPACE_CSV,
            KEYBOARD_LAYOUT_FILE,
            CALIBRATION_V2_FILE,
        )
        for name in legacy_names:
            path = root / name
            try:
                if path.is_file():
                    path.unlink()
            except OSError as e:
                h._log_verbose(f"[calib] could not reset legacy {name}: {e}")
        session_id = h._calibration_controller.session_id
        if not session_id:
            return
        session_dir = ensure_session_dir(session_id, runs_dir=h._run_summary_writer.runs_dir)
        for name in legacy_names:
            path = session_dir / name
            try:
                if path.is_file():
                    path.unlink()
            except OSError as e:
                h._log_verbose(f"[calib] could not reset {name}: {e}")

    def write_debug_csv(self, *, ridge_fit, loocv_detail) -> None:
        h = self._host
        if h._calibration_session is None or ridge_fit is None or ridge_fit.model is None:
            return
        sess = h._calibration_session
        model = ridge_fit.model

        loocv_by_i = {}
        if loocv_detail:
            for d in loocv_detail:
                loocv_by_i[int(d["i"])] = d

        out_path = self._session_artifact_dir() / CALIBRATION_DEBUG_CSV
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "target_index",
                    "label",
                    "target_x",
                    "target_y",
                    "mean_avg_h",
                    "mean_avg_v",
                    "mean_pca_vL",
                    "mean_pca_vR",
                    "mean_face_y",
                    "mean_eye_box_h",
                    "predicted_x",
                    "predicted_y",
                    "train_error_px",
                    "loocv_error_px",
                    "sample_count",
                ]
            )

            pairs = sess.get_training_samples()
            for i, ((feat, (tx, ty))) in enumerate(pairs):
                pred = model.predict(feat)
                if pred is None:
                    px = py = None
                    train_err = None
                else:
                    px = float(pred.x)
                    py = float(pred.y)
                    train_err = float(np.hypot(px - float(tx), py - float(ty)))

                loocv_err = None
                if i in loocv_by_i:
                    loocv_err = float(loocv_by_i[i]["err"])

                n_raw = sess.samples_used_for_target_mean(i)

                w.writerow(
                    [
                        int(i + 1),
                        sess.targets[i].label if i < len(sess.targets) else "",
                        float(tx),
                        float(ty),
                        float(feat.avg_h) if feat.avg_h is not None else "",
                        float(feat.avg_v) if feat.avg_v is not None else "",
                        float(feat.pca_vL) if feat.pca_vL is not None else "",
                        float(feat.pca_vR) if feat.pca_vR is not None else "",
                        float(feat.face_y) if feat.face_y is not None else "",
                        float(feat.eye_box_h) if feat.eye_box_h is not None else "",
                        "" if px is None else float(px),
                        "" if py is None else float(py),
                        "" if train_err is None else float(train_err),
                        "" if loocv_err is None else float(loocv_err),
                        int(n_raw),
                    ]
                )
        h._log_verbose(f"[calib] wrote calibration debug CSV: {out_path}")

    def print_target_sample_quality(self) -> None:
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

    def print_row_v_stats_and_export_ratio_space(self) -> None:
        h = self._host
        if h._calibration_session is None:
            return
        sess = h._calibration_session
        rows = []
        for i, t in enumerate(sess.targets):
            n = sess.samples_used_for_target_mean(i)
            if n <= 0:
                continue
            ratios = sess._accepted_ratios[i]  # noqa: SLF001
            hs = [p[0] for p in ratios]
            vs = [p[1] for p in ratios]
            mh = float(sum(hs) / len(hs))
            mv = float(sum(vs) / len(vs))
            rows.append((t.target_id, t.label, float(t.screen_x), float(t.screen_y), n, mh, mv))

        if not rows:
            return

        top = [r for r in rows if "top" in r[1]]
        mid = [r for r in rows if r[1] in {"left", "center", "right"} or ("middle" in r[1])]
        bot = [r for r in rows if "bottom" in r[1]]

        def stats(name: str, rs):
            if not rs:
                h._log_verbose(f"[calib] avg_v row {name}: (no targets)")
                return None
            vs = np.array([r[6] for r in rs], dtype=np.float64)
            mu = float(np.mean(vs))
            sd = float(np.std(vs))
            h._log_verbose(f"[calib] avg_v row {name}: mean={mu:.4f} std={sd:.4f} n_targets={len(rs)}")
            return mu

        mu_top = stats("top", top)
        mu_mid = stats("mid", mid)
        mu_bot = stats("bottom", bot)
        if mu_top is not None and mu_mid is not None:
            h._log_verbose(f"[calib] avg_v separation top-mid: {abs(mu_top - mu_mid):.4f}")
        if mu_mid is not None and mu_bot is not None:
            h._log_verbose(f"[calib] avg_v separation mid-bottom: {abs(mu_mid - mu_bot):.4f}")

        out_path = self._session_artifact_dir() / CALIBRATION_RATIO_SPACE_CSV
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                ["session_id", "target_id", "label", "screen_x", "screen_y", "n_samples", "mean_avg_h", "mean_avg_v"]
            )
            for (tid, label, sx, sy, n, mh, mv) in rows:
                w.writerow([sess.session_id, tid, label, sx, sy, n, mh, mv])
        h._log_verbose(f"[calib] wrote ratio-space scatter CSV: {out_path}")
