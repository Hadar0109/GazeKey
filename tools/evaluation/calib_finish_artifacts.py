"""Developer calibration artifact writers (CSV, coverage, geom overlay, mapper snapshot).

Used only when tools install DevTools on a VirtualKeyboard host — not on the
product default path.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import numpy as np

from tools.debug.calibration_geometry_diagnostics import print_geometric_diagnostics
from tools.debug.calibration_geometry_overlay import CalibrationGeometryOverlay
from tools.debug.mapper_store import save_calibration_mapper
from tools.evaluation.coverage_diagnostics import build_coverage_report, write_coverage_diagnostics
from tools.evaluation.session_paths import (
    CALIBRATION_DEBUG_CSV,
    CALIBRATION_RATIO_SPACE_CSV,
    CALIBRATION_V2_FILE,
    KEYBOARD_LAYOUT_FILE,
    ensure_session_dir,
)
from gazekey.layout import inspect_keyboard_layout
from gazekey.mapping.config import CALIBRATION_MODE
from gazekey.ui.env_flags import calib_geom_debug

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class CalibFinishArtifacts:
    """Disk/console developer artifacts after a calibration fit."""

    def __init__(self, host: VirtualKeyboard, *, runs_dir: Any) -> None:
        self._host = host
        self._runs_dir = runs_dir

    def write_run_summary(
        self,
        writer: Any,
        *,
        passed: bool,
        failure_reason: Optional[str] = None,
        loocv_rms_px: Optional[float] = None,
        ridge_alpha: Optional[float] = None,
        quality_warnings: Optional[list[str]] = None,
    ) -> None:
        h = self._host
        session = h._calibration_session
        if session is None or writer is None:
            return
        collected = sum(
            1 for i in range(len(session.targets)) if session.accepted_count_for_target(i) > 0
        )
        writer.write_calibration_summary(
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
                runs_dir=self._runs_dir,
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
                runs_dir=str(self._runs_dir),
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

    def maybe_show_geometry_overlay(self, *, samples, model, loocv_detail) -> None:
        h = self._host
        if not calib_geom_debug(calib_debug_cached=h._calib_debug):
            return
        try:
            self.show_geometry_overlay(samples=samples, model=model, loocv_detail=loocv_detail)
        except Exception as e:
            h._log_verbose(f"[calib] geometry overlay failed: {e}")

    def print_geometric_diagnostics_safe(self, *, ridge_fit, samples, loocv_detail) -> None:
        h = self._host
        try:
            print_geometric_diagnostics(
                model=ridge_fit.model,
                samples=samples,
                targets=h._calibration_session.targets,
                loocv_detail=loocv_detail,
                keys=h._layout_keys or inspect_keyboard_layout(h.keyboard_widget),
            )
        except Exception as e:
            h._log_verbose(f"[calib] geometric diagnostics failed: {e}")

    def _session_artifact_dir(self) -> Path:
        h = self._host
        session_id = h._calibration_controller.session_id
        if not session_id and h._calibration_session is not None:
            session_id = h._calibration_session.session_id
        return ensure_session_dir(session_id or "unknown", runs_dir=self._runs_dir)

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
        session_dir = ensure_session_dir(session_id, runs_dir=self._runs_dir)
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

    def on_success(
        self,
        writer: Any,
        *,
        ridge_fit: Any,
        loocv_detail: Any,
        quality: Any,
        samples: Any,
        ridge_alpha: Any = None,
    ) -> None:
        self.write_run_summary(
            writer,
            passed=True,
            loocv_rms_px=quality.loocv_rms_px,
            ridge_alpha=ridge_alpha,
            quality_warnings=quality.warnings,
        )
        try:
            self.print_row_v_stats_and_export_ratio_space()
        except Exception as e:
            self._host._log_verbose(f"[calib] ratio-space stats/export failed: {e}")
        self.print_geometric_diagnostics_safe(
            ridge_fit=ridge_fit, samples=samples, loocv_detail=loocv_detail
        )
        self.maybe_show_geometry_overlay(
            samples=samples, model=ridge_fit.model, loocv_detail=loocv_detail
        )
        self.write_mapper_snapshot(ridge_fit=ridge_fit)
        self.write_coverage_diagnostic()
        try:
            self.write_debug_csv(ridge_fit=ridge_fit, loocv_detail=loocv_detail)
        except Exception as e:
            self._host._log_verbose(f"[calib] calibration_debug.csv write failed: {e}")

    def on_failure(self, writer: Any, **kwargs: Any) -> None:
        ridge_fit = kwargs.pop("ridge_fit", None)
        loocv_detail = kwargs.pop("loocv_detail", None)
        self.write_run_summary(writer, passed=False, **kwargs)
        if ridge_fit is not None:
            try:
                self.write_mapper_snapshot(ridge_fit=ridge_fit)
                self.write_debug_csv(ridge_fit=ridge_fit, loocv_detail=loocv_detail)
            except Exception:
                pass
