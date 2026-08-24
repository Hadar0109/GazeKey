"""MVP dev benchmark session (15-key scoring via evaluation/)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel

from tools.evaluation.benchmark_runner import (
    build_benchmark_run,
    calibration_labels_from_targets,
    evaluate_benchmark_pass,
    unique_evaluation_labels,
)
from tools.evaluation.benchmark_session import resolve_sample_keys
from tools.evaluation.gazesample_scoring import GazeSampleEvalSession
from tools.evaluation.experiment_record import (
    ExperimentRecord,
    write_experiment_record,
    write_hadar_wrong_focus,
)
from tools.evaluation.failure_analysis import format_failure_analysis, infer_likely_cause
from tools.evaluation.session import format_location_results
from tools.evaluation.session_paths import folder_session_id
from tools.flags import dev_benchmark_enabled as env_dev_benchmark_enabled

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class BenchmarkController:
    """15-key MVP benchmark after calibration."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._host = host
        self._session: Any = None
        self._banner: QLabel | None = None
        self._highlight_btn = None

    @property
    def session(self) -> Any:
        return self._session

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
        if not self._begin_session():
            return
        self._host._log_verbose(
            "[benchmark] started — tools evaluation (repeatability + held-out letters + editing/control)"
        )

    def process_gaze_sample(self, sample) -> None:
        h = self._host
        session = self._session
        if session is None or not hasattr(session, "tick_sample"):
            return
        now_ms = int(time.time() * 1000)
        if bool(getattr(sample, "valid", False)):
            h._update_gaze_preview_dot(float(sample.x), float(sample.y))
        else:
            h._hide_preview_dot()
        completed = session.tick_sample(now_ms, sample)
        if completed is not None:
            h._log_verbose(
                f"[benchmark] {completed.target_key}: "
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
        banner = session.instruction_text().replace("Look at key:", "Benchmark — look at:")
        self._update_banner(banner)

    def process_eye_data(self, eye_data) -> None:
        del eye_data
        return

    def _ensure_banner(self) -> None:
        if self._banner is not None:
            return
        h = self._host
        banner = QLabel(h.main_content_widget)
        banner.setObjectName("benchmarkBanner")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        banner.setStyleSheet(
            """
            QLabel#benchmarkBanner {
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
        return f"gf-bench{int(time.time())}"

    def _begin_session(self) -> bool:
        h = self._host
        gf_path = bool(getattr(h, "_official_gaze_ready", False))
        if not gf_path:
            h._log_verbose("[benchmark] skipped: official GazeFollower calibration not ready")
            return False
        h._export_keyboard_layout()
        if not h._layout_keys:
            h._log_verbose("[benchmark] skipped: keyboard layout not ready")
            return False
        if h.current_layout != "letters":
            h._keyboard_layout_builder.switch_layout("letters")
        try:
            calib_labels = calibration_labels_from_targets(None)
            labels = unique_evaluation_labels(
                calibration_labels=calib_labels,
                layout_mode="official",
                keys=h._layout_keys,
            )
            resolved = resolve_sample_keys(h._layout_keys, labels)
        except ValueError as e:
            h._log_verbose(f"[benchmark] {e}")
            return False

        h._set_post_calibration_controls(False)
        h._preview_mode = True
        self._eval_calib_labels = calib_labels
        self._gf_eval = True
        self._session = GazeSampleEvalSession(
            resolved,
            keys_for_hit_test=h._layout_keys,
            calibration_labels=calib_labels,
        )
        now_ms = int(time.time() * 1000)
        self._session.begin(now_ms)
        cur = self._session.current_sample()
        if cur is not None:
            _label, row = cur
            self._highlight_target(row.button)
        self._update_banner(self._session.instruction_text())
        return True

    def _finish_session(self) -> None:
        from gazekey.backend.provenance import provenance_record
        from tools.evaluation.run_summary import (
            FEATURE_004_EVAL_BEFORE,
            GF_EVAL_FIDELITY_NOTES,
        )

        h = self._host
        session = self._session
        if session is None:
            return
        rows = session.results
        run = build_benchmark_run(rows)
        passed, reason = evaluate_benchmark_pass(run.metrics)
        status = "passed" if passed else "failed"
        likely_cause = infer_likely_cause(rows) if status == "failed" else "none"
        analysis = format_failure_analysis(rows, likely_cause=likely_cause)
        h._log_verbose(analysis)
        session_id = self._benchmark_session_id()
        gate = getattr(h, "_last_quality_gate_kind", None)
        h._run_summary_writer.write_benchmark_summary(
            session_id=session_id,
            metrics=run.metrics,
            status=status,
            failure_reason=reason or None,
            failure_analysis=analysis,
            location_results_text=format_location_results(rows),
            quality_gate_kind=gate,
            fidelity_notes=GF_EVAL_FIDELITY_NOTES,
        )
        try:
            write_experiment_record(
                session_id,
                ExperimentRecord(
                    hypothesis="GazeFollower integrated evaluation (Feature 005).",
                    logical_area="eval",
                    change="GazeSample + live QRects; no FeatureExtractor/Ridge predict",
                    eval_before=FEATURE_004_EVAL_BEFORE,
                    eval_after=folder_session_id(session_id),
                    decision="pending",
                    notes=f"{GF_EVAL_FIDELITY_NOTES}; provenance={provenance_record()}",
                ),
                runs_dir=h._run_summary_writer.runs_dir,
            )
            write_hadar_wrong_focus(session_id, runs_dir=h._run_summary_writer.runs_dir)
        except Exception as e:
            h._log_verbose(f"[benchmark] experiment_record write failed: {e}")
        self._session = None
        self._clear_highlight()
        self._hide_banner()
        h._reset_preview_overlay()
        h._preview_mode = True
        h._set_post_calibration_controls(True)
