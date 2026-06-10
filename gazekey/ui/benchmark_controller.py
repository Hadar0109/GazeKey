"""MVP dev benchmark and debug keyboard-accuracy session (T047)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel

from gazekey.evaluation.benchmark_runner import build_benchmark_run, evaluate_benchmark_pass
from gazekey.evaluation.failure_analysis import format_failure_analysis, infer_likely_cause
from gazekey.features import FeatureExtractor
from gazekey.mapping.typing_candidate import CALIBRATION_MODE
from gazekey.ui.env_flags import dev_benchmark_enabled as env_dev_benchmark_enabled

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class BenchmarkController:
    """15-key MVP benchmark and optional debug keyboard-accuracy runs."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._host = host
        self._session: Any = None
        self._mvp_run = False
        self._banner: QLabel | None = None
        self._highlight_btn = None

    @property
    def session(self) -> Any:
        return self._session

    @session.setter
    def session(self, value: Any) -> None:
        self._session = value

    @property
    def mvp_run(self) -> bool:
        return self._mvp_run

    @mvp_run.setter
    def mvp_run(self, value: bool) -> None:
        self._mvp_run = bool(value)

    @property
    def banner(self) -> QLabel | None:
        return self._banner

    def active(self) -> bool:
        return self._session is not None and not self._session.finished

    @staticmethod
    def dev_benchmark_enabled() -> bool:
        return env_dev_benchmark_enabled()

    def update_banner_geometry(self) -> None:
        h = self._host
        if self._banner is not None and hasattr(h, "main_content_widget"):
            self._banner.setGeometry(
                12, 8, max(200, h.main_content_widget.width() - 24), 44
            )

    def maybe_start_dev_benchmark(self) -> None:
        """Developer-only: auto-start MVP benchmark after calibration + preview."""
        h = self._host
        if not self.dev_benchmark_enabled():
            return
        if not h._calibration_usable():
            h._log_verbose("[benchmark] dev auto-start blocked — calibration not usable")
            return
        if h._is_calibrating:
            h._log_verbose("[benchmark] dev auto-start blocked — calibration in progress")
            return
        if self.active():
            h._log_verbose("[benchmark] dev auto-start blocked — another run active")
            return
        if not h._preview_mode:
            h._log_verbose("[benchmark] dev auto-start blocked — preview not ready")
            return
        self.start_mvp_benchmark()

    def start_mvp_benchmark(self) -> None:
        if not self._begin_session(mvp_benchmark=True):
            return
        self._host._log_verbose(
            "[benchmark] started — dev MVP benchmark (15 keys, GAZEKEY_DEV_BENCHMARK=1)"
        )

    def start_keyboard_accuracy_debug(self) -> None:
        from gazekey.debug.keyboard_accuracy import default_key_accuracy_debug_path

        if not self._begin_session(mvp_benchmark=False):
            return
        self._host._log_verbose(
            f"[key_accuracy] started — CSV -> {default_key_accuracy_debug_path()}"
        )

    def process_eye_data(self, eye_data) -> None:
        h = self._host
        session = self._session
        if session is None:
            return
        now_ms = int(time.time() * 1000)
        features = FeatureExtractor.from_eye_data(eye_data, timestamp_ms=now_ms)
        xy = h._preview_mapped_screen_xy(eye_data, now_ms=now_ms)
        if xy is not None:
            px, py = xy
            h._update_gaze_preview_dot(px, py)
        else:
            h._hide_preview_dot()

        completed = session.tick(now_ms, features=features)
        log_tag = "benchmark" if self._mvp_run else "key_accuracy"
        if completed is not None:
            h._log_verbose(
                f"[{log_tag}] {completed.target_key}: "
                f"pred=({completed.predicted_x:.1f},{completed.predicted_y:.1f}) "
                f"key={completed.predicted_key} err={completed.error_px:.1f}px "
                f"correct={completed.is_correct}"
            )

        if session.finished:
            self._finish_session()
            return

        cur = session.current_sample()
        if cur is not None:
            _label, row = cur
            self._highlight_target(row.button)
        banner = session.instruction_text()
        if self._mvp_run:
            banner = banner.replace("Look at key:", "Benchmark — look at:")
            if banner.endswith("complete"):
                banner = "Benchmark complete"
        self._update_banner(banner)

    def _ensure_banner(self) -> None:
        if self._banner is not None:
            return
        h = self._host
        banner = QLabel(h.main_content_widget)
        banner.setObjectName("keyboardAccuracyBanner")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        banner.setStyleSheet(
            """
            QLabel#keyboardAccuracyBanner {
                background-color: rgba(15, 23, 42, 230);
                color: #FBBF24;
                border: 2px solid #FBBF24;
                border-radius: 6px;
                padding: 8px 12px;
            }
            """
        )
        banner.setGeometry(12, 8, max(200, h.main_content_widget.width() - 24), 44)
        banner.raise_()
        self._banner = banner

    def _update_banner(self, text: str) -> None:
        self._ensure_banner()
        if self._banner is not None:
            self._banner.setText(str(text))
            self._banner.show()
            self._banner.raise_()

    def _hide_banner(self) -> None:
        if self._banner is not None:
            self._banner.hide()

    def _clear_highlight(self) -> None:
        h = self._host
        if self._highlight_btn is not None:
            h._set_key_gaze_style(self._highlight_btn, False, 0.0)
        self._highlight_btn = None

    def _highlight_target(self, button) -> None:
        h = self._host
        self._clear_highlight()
        if button is None:
            return
        self._highlight_btn = button
        h._set_key_gaze_style(button, True, 1.0, dwelling=True)

    def _benchmark_session_id(self) -> str:
        h = self._host
        session = h._calibration_v2_session
        base = ""
        if session is not None:
            base = h._calibration_controller.session_id or session.csv.session_id
        if not base:
            base = "unknown"
        return f"{base}-bench{int(time.time())}"

    def _begin_session(self, *, mvp_benchmark: bool) -> bool:
        from gazekey.debug.keyboard_accuracy import KeyboardAccuracyEvalSession, resolve_sample_keys

        h = self._host
        if h._gaze_mapper_v2 is None:
            tag = "benchmark" if mvp_benchmark else "key_accuracy"
            h._log_verbose(f"[{tag}] skipped: no v2 mapper loaded")
            return False
        h._export_keyboard_layout()
        if not h._intent_keys:
            tag = "benchmark" if mvp_benchmark else "key_accuracy"
            h._log_verbose(f"[{tag}] skipped: keyboard layout not ready")
            return False
        if h.current_layout != "letters":
            h._keyboard_layout_builder.switch_layout("letters")
        try:
            resolved = resolve_sample_keys(h._intent_keys)
        except ValueError as e:
            tag = "benchmark" if mvp_benchmark else "key_accuracy"
            h._log_verbose(f"[{tag}] {e}")
            return False

        self._mvp_run = bool(mvp_benchmark)
        h._set_post_calibration_controls(False)
        h._preview_mode = True
        if hasattr(h, "preview_btn"):
            h.preview_btn.setProperty("active", "true")
            h.preview_btn.style().unpolish(h.preview_btn)
            h.preview_btn.style().polish(h.preview_btn)
            h.preview_btn.update()
        h._clear_v2_focus()
        h._gaze_smoother.reset()
        h._feature_smoother.reset()

        self._session = KeyboardAccuracyEvalSession(
            resolved,
            keys_for_hit_test=h._intent_keys,
            predict_screen_xy=h._key_accuracy_predict_screen_xy,
            on_collect_begin=lambda: h._feature_smoother.reset(),
        )
        now_ms = int(time.time() * 1000)
        self._session.begin(now_ms)
        cur = self._session.current_sample()
        if cur is not None:
            _label, row = cur
            self._highlight_target(row.button)
        self._update_banner(self._session.instruction_text())
        return True

    def _finish_mvp_benchmark(self, rows) -> None:
        from gazekey.evaluation.benchmark_diagnostics import (
            build_benchmark_diagnostics,
            write_benchmark_diagnostics,
        )

        h = self._host
        run = build_benchmark_run(rows)
        passed, reason = evaluate_benchmark_pass(run.metrics)
        status = "passed" if passed else "failed"
        likely_cause = infer_likely_cause(rows) if status == "failed" else "none"
        analysis = format_failure_analysis(rows, likely_cause=likely_cause)
        h._log_verbose(analysis)
        session_id = self._benchmark_session_id()
        h._run_summary_writer.write_benchmark_summary(
            session_id=session_id,
            metrics=run.metrics,
            status=status,
            failure_reason=reason or None,
            failure_analysis=analysis,
        )
        try:
            cal_targets = None
            if h._calibration_v2_session is not None:
                cal_targets = h._calibration_v2_session.targets
            feat_alpha = getattr(h._feature_smoother, "alpha", None)
            gaze_alpha = getattr(
                h._gaze_smoother,
                "alpha",
                getattr(h._gaze_smoother, "_default_alpha", None),
            )
            diagnostics = build_benchmark_diagnostics(
                session_id=session_id,
                rows=rows,
                metrics=run.metrics,
                status=status,
                failure_reason=reason,
                likely_cause=likely_cause,
                model=h._gaze_mapper_v2,
                calibration_targets=cal_targets,
                calibration_loocv_rms_px=getattr(h, "_last_calibration_loocv_rms", None),
                feature_smoother_alpha=feat_alpha,
                gaze_smoother_alpha=gaze_alpha,
                gaze_bias_x=float(h._gaze_bias_x),
                gaze_bias_y=float(h._gaze_bias_y),
                active_calibration_mode=str(h._calib2_mode or CALIBRATION_MODE),
            )
            path = write_benchmark_diagnostics(diagnostics, session_id=session_id)
            h._log_verbose(f"[benchmark] diagnostics written -> {path}")
        except Exception as e:
            h._log_verbose(f"[benchmark] diagnostics write failed: {e}")

    def _finish_session(self) -> None:
        from gazekey.debug.keyboard_accuracy import KeyAccuracyDebugCsv, print_accuracy_summary

        h = self._host
        session = self._session
        if session is None:
            return
        rows = session.results
        mvp = bool(self._mvp_run)
        if mvp:
            self._finish_mvp_benchmark(rows)
        else:
            try:
                KeyAccuracyDebugCsv().write(rows, overwrite=True)
                from gazekey.debug.keyboard_accuracy import default_key_accuracy_debug_path

                h._log_verbose(
                    f"[key_accuracy] wrote {len(rows)} rows to {default_key_accuracy_debug_path()}"
                )
            except Exception as e:
                h._log_verbose(f"[key_accuracy] CSV write failed: {e}")
            print_accuracy_summary(rows)
            if session.recorded_gaze and h._last_calib_samples and h._calibration_v2_session is not None:
                self._run_mapper_diagnostics(session)
            if h._keyboard_accuracy_compare and session.recorded_gaze:
                self._run_mapper_compare(session)
        self._mvp_run = False
        self._session = None
        self._clear_highlight()
        self._hide_banner()
        h._reset_preview_overlay()
        h._preview_mode = True
        h._set_post_calibration_controls(True)
        if hasattr(h, "preview_btn"):
            h.preview_btn.setProperty("active", "true")
            h.preview_btn.style().unpolish(h.preview_btn)
            h.preview_btn.style().polish(h.preview_btn)
            h.preview_btn.update()

    def _run_mapper_diagnostics(self, session) -> None:
        from gazekey.debug.keyboard_accuracy_mapper_diag import run_keyboard_accuracy_mapper_diagnostics

        h = self._host
        run_keyboard_accuracy_mapper_diagnostics(
            recorded=session.recorded_gaze,
            keys=h._intent_keys,
            model=h._gaze_mapper_v2,
            calib_samples=h._last_calib_samples,
            calib_targets=h._calibration_v2_session.targets,
            gaze_bias_x=float(h._gaze_bias_x),
            gaze_bias_y=float(h._gaze_bias_y),
            clamp_xy=h._clamp_v2_xy,
            feature_smoother_alpha=float(h._feature_smoother.alpha),
        )

    def _run_mapper_compare(self, session) -> None:
        from gazekey.debug.keyboard_accuracy_compare import (
            compare_mapper_candidates,
            print_compare_leaderboard,
            validate_selected_mapper_matches_debug,
            write_compare_csv,
        )

        h = self._host
        if not h._last_mapper_candidate_reports:
            h._log_verbose("[key_accuracy_compare] skipped: no candidate reports from last fit")
            return
        if h._calibration_v2_session is None:
            return
        recorded = list(session.recorded_gaze)
        if not recorded:
            h._log_verbose("[key_accuracy_compare] skipped: no recorded gaze features")
            return
        runtime_mapper_type = str(getattr(h._gaze_mapper_v2, "mapper_type", "") or "")
        h._log_verbose(
            f"[key_accuracy_compare] replaying {len(recorded)} keys across "
            f"{len(h._last_mapper_candidate_reports)} candidates"
        )
        results = compare_mapper_candidates(
            recorded=recorded,
            keys=h._intent_keys,
            candidates=h._last_mapper_candidate_reports,
            calib_samples=h._last_calib_samples,
            calib_targets=h._calibration_v2_session.targets,
            runtime_model=h._gaze_mapper_v2,
            runtime_mapper_type=runtime_mapper_type,
            gaze_bias_x=float(h._gaze_bias_x),
            gaze_bias_y=float(h._gaze_bias_y),
            clamp_xy=h._clamp_v2_xy,
            min_quality=float(h._rt2_min_quality),
        )
        path = write_compare_csv(results)
        h._log_verbose(f"[key_accuracy_compare] wrote {path}")
        print_compare_leaderboard(results)
        if runtime_mapper_type:
            try:
                validate_selected_mapper_matches_debug(
                    session.results,
                    results,
                    runtime_mapper_type,
                )
                debug_ok = sum(1 for r in session.results if r.is_correct)
                h._log_verbose(
                    f"[key_accuracy_compare] selected mapper {runtime_mapper_type} "
                    f"matches debug CSV ({debug_ok}/{len(session.results)} correct)"
                )
            except AssertionError as e:
                h._log_verbose(f"[key_accuracy_compare] WARNING: debug/compare mismatch: {e}")
