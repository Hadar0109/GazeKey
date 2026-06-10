"""Dormant gaze-typing focus, runtime CSV logging, row-aware helpers (T051; preserved for T052)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QRect

from gazekey.features import FeatureExtractor
from gazekey.future import score_keys
from gazekey.mapping.typing_candidate import (
    INTENT_CROSS_ROW_PENALTY,
    INTENT_ROW_STICKINESS,
    INTENT_SIGMA_PX,
    INTENT_SIGMA_Y_PX,
)

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class GazeTypingSupport:
    """Focus styling and debug logging for the dormant gaze-typing path."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._host = host
        self._runtime_logger = None

    def _logger(self):
        if self._runtime_logger is None:
            from gazekey.debug.runtime_key_confidence_logger import RuntimeKeyConfidenceLogger

            self._runtime_logger = RuntimeKeyConfidenceLogger(enabled=self._host._verbose)
        return self._runtime_logger

    def clear_v2_focus(self) -> None:
        h = self._host
        if h._last_v2_focused_key_id is not None:
            row = h._keys_by_id.get(h._last_v2_focused_key_id)
            if row is not None:
                h._set_key_gaze_style(row.button, False, 0.0)
        h._last_v2_focused_key_id = None

    def apply_v2_focus(self, key_id: str | None, *, progress: float) -> None:
        h = self._host
        if key_id is None:
            self.clear_v2_focus()
            return
        row = h._keys_by_id.get(key_id)
        if row is None:
            self.clear_v2_focus()
            return
        if h._last_v2_focused_key_id is not None and h._last_v2_focused_key_id != key_id:
            prev = h._keys_by_id.get(h._last_v2_focused_key_id)
            if prev is not None:
                h._set_key_gaze_style(prev.button, False, 0.0)
        h._last_v2_focused_key_id = key_id
        dwelling = progress >= 0.7
        focused = progress > 0.0
        h._set_key_gaze_style(row.button, focused, progress, dwelling=dwelling)

    def log_runtime_row(
        self,
        eye_data,
        *,
        mapped_x: float | None,
        mapped_y: float | None,
        row_name: str = "",
        row_confidence: float | None = None,
    ) -> None:
        from gazekey.debug.runtime_key_confidence_logger import RuntimeLogRow

        h = self._host
        now_ms = int(time.time() * 1000)
        if now_ms - h._last_runtime_log_ms < 100:
            return
        h._last_runtime_log_ms = now_ms

        features = FeatureExtractor.from_eye_data(eye_data, timestamp_ms=now_ms)

        velocity_px_s = None
        if mapped_x is not None and mapped_y is not None:
            if h._last_mapped_x is not None and h._last_mapped_y is not None and h._last_mapped_t is not None:
                dt_s = max(1e-6, (now_ms - h._last_mapped_t) / 1000.0)
                dx = float(mapped_x - h._last_mapped_x)
                dy = float(mapped_y - h._last_mapped_y)
                velocity_px_s = (dx * dx + dy * dy) ** 0.5 / dt_s
            h._last_mapped_x = float(mapped_x)
            h._last_mapped_y = float(mapped_y)
            h._last_mapped_t = now_ms

        focused = h._gaze_focused_button
        focused_key_id = ""
        focused_key_label = ""
        if focused is not None:
            focused_key_label = focused.text()
            focused_key_id = focused_key_label

        best_id = None
        best_conf = 0.0
        second_id = None
        second_conf = 0.0
        if mapped_x is not None and mapped_y is not None and h._intent_keys:
            scored = score_keys(
                keys=h._intent_keys,
                gaze_x=mapped_x,
                gaze_y=mapped_y,
                sigma_px=INTENT_SIGMA_PX,
                sigma_y_px=INTENT_SIGMA_Y_PX,
                focused_key_id=h._selection_policy._focused,
                row_stickiness=INTENT_ROW_STICKINESS,
                cross_row_penalty=INTENT_CROSS_ROW_PENALTY,
            )
            if scored:
                best_id = scored[0].key_id
                best_conf = float(scored[0].probability)
            if len(scored) >= 2:
                second_id = scored[1].key_id
                second_conf = float(scored[1].probability)

        self._logger().log(
            RuntimeLogRow(
                timestamp_ms=now_ms,
                layout_version=h._layout_version,
                calibration_version=6,
                mapper_type=getattr(h._gaze_mapper_v2, "mapper_type", "none"),
                blink=features.blink,
                confidence=float(features.confidence),
                Lh=features.Lh,
                Lv=features.Lv,
                Rh=features.Rh,
                Rv=features.Rv,
                avg_h=features.avg_h,
                avg_v=features.avg_v,
                eye_box_w=features.eye_box_w,
                eye_box_h=features.eye_box_h,
                face_x=features.face_x,
                face_y=features.face_y,
                mapped_x=mapped_x,
                mapped_y=mapped_y,
                mapped_quality=None,
                row_name=str(row_name or ""),
                row_confidence=row_confidence,
                focused_key_id=focused_key_id,
                focused_key_label=focused_key_label,
                focused_confidence=1.0 if focused is not None else 0.0,
                challenger_key_id=second_id or "",
                challenger_confidence=float(second_conf),
                switch_allowed=True,
                fixation_state="dwell_v1",
                dwell_progress=float(focused.property("dwellProgress") or 0.0) if focused is not None else 0.0,
                activated_key_id="",
                velocity_px_s=velocity_px_s,
                stability_score=None,
            )
        )

    def derive_semantic_row_rects(self):
        """Return (row_rects, row_centers_y) for the 6 semantic regions (dormant)."""
        h = self._host
        if not h._intent_keys:
            return {}, {}
        keys = list(h._intent_keys)
        phys = {}
        for k in keys:
            ys = phys.setdefault(
                k.row_index,
                {"ys": [], "x0": k.rect.left(), "x1": k.rect.right(), "y0": k.rect.top(), "y1": k.rect.bottom()},
            )
            ys["ys"].append(float(k.center[1]))
            ys["x0"] = min(ys["x0"], k.rect.left())
            ys["x1"] = max(ys["x1"], k.rect.right())
            ys["y0"] = min(ys["y0"], k.rect.top())
            ys["y1"] = max(ys["y1"], k.rect.bottom())

        phys_rows = []
        for ridx, d in phys.items():
            cy = float(sum(d["ys"]) / max(1, len(d["ys"])))
            phys_rows.append((cy, ridx, d))
        phys_rows.sort(key=lambda t: t[0])

        sem_rects = {n: QRect() for n in h._row_aware_row_names}
        sem_centers_y = {}

        def sem_for_rank(rank: int) -> str:
            if len(phys_rows) <= len(h._row_aware_row_names):
                return h._row_aware_row_names[min(rank, len(h._row_aware_row_names) - 1)]
            q = int(round((rank / max(1, len(phys_rows) - 1)) * (len(h._row_aware_row_names) - 1)))
            return h._row_aware_row_names[max(0, min(len(h._row_aware_row_names) - 1, q))]

        for rank, (cy, _ridx, d) in enumerate(phys_rows):
            sem = sem_for_rank(rank)
            r = QRect(int(d["x0"]), int(d["y0"]), int(d["x1"] - d["x0"]), int(d["y1"] - d["y0"]))
            if sem_rects[sem].isNull():
                sem_rects[sem] = r
            else:
                sem_rects[sem] = sem_rects[sem].united(r)
            sem_centers_y.setdefault(sem, []).append(float(cy))

        sem_centers_y = {k: float(sum(v) / len(v)) for k, v in sem_centers_y.items() if v}
        return sem_rects, sem_centers_y

    def row_adjacent(self, row_name: str) -> list[str]:
        h = self._host
        names = list(h._row_aware_row_names)
        if row_name not in names:
            return []
        i = names.index(row_name)
        out = []
        if i - 1 >= 0:
            out.append(names[i - 1])
        if i + 1 < len(names):
            out.append(names[i + 1])
        return out

    def score_keys_row_weighted(self, *, gaze_x: float, gaze_y: float, row_weight: dict[str, float]):
        from math import exp

        h = self._host
        p = QPoint(int(gaze_x), int(gaze_y))
        sigma_px = 52.0
        hitbox_bonus = 1.35

        scored = []
        for k in h._intent_keys:
            sem = h._key_semantic_row.get(k.key_id, "letters2")
            rw = float(row_weight.get(sem, 0.0))
            if rw <= 0.0:
                continue
            cx, cy = k.center
            dx = float(gaze_x - cx)
            dy = float(gaze_y - cy)
            d = (dx * dx + dy * dy) ** 0.5
            s = exp(-0.5 * (d / sigma_px) ** 2) * float(k.weight) * rw
            if k.hitbox.contains(p):
                s *= hitbox_bonus
            scored.append((k, float(s)))

        total = sum(s for _, s in scored)
        if total <= 1e-12:
            return []
        out = [(k, s / total) for k, s in scored]
        out.sort(key=lambda t: t[1], reverse=True)
        return out
