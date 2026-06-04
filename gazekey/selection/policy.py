"""Key selection policy using intent probabilities + hysteresis + dwell.

This replaces "hit-test rect contains gaze point" with:
1) choose a *candidate key* from intent probabilities
2) apply anti-flicker/hysteresis before switching focus
3) perform lock-on + dwell completion selection
4) suppress switching during high velocity
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from gazekey.typing.dwell_selector import DwellSelector, DwellState


@dataclass(frozen=True)
class SelectionState:
    focused_key_id: Optional[str]
    progress: float
    should_activate: bool


class SelectionPolicy:
    def __init__(
        self,
        *,
        dwell_sec: float = 1.25,
        cooldown_sec: float = 0.25,
        miss_frames_to_reset: int = 5,
        switch_margin: float = 0.12,
        cross_row_switch_margin: float = 0.22,
        min_switch_ms: float = 140.0,
        cross_row_min_switch_ms: float = 280.0,
        velocity_suppress_px_s: float = 1200.0,
        debug_follow_best: bool = False,
    ) -> None:
        self._dwell = DwellSelector(
            dwell_duration_sec=dwell_sec,
            global_cooldown_sec=cooldown_sec,
            miss_frames_to_reset=miss_frames_to_reset,
        )
        self._focused: Optional[str] = None
        self._focus_conf: float = 0.0
        self._candidate_since_ms: Optional[int] = None
        self._switch_margin = float(switch_margin)
        self._cross_row_switch_margin = float(cross_row_switch_margin)
        self._min_switch_ms = float(min_switch_ms)
        self._cross_row_min_switch_ms = float(cross_row_min_switch_ms)
        self._vel_suppress = float(velocity_suppress_px_s)
        self._debug_follow_best = bool(debug_follow_best)
        self._focused_row_index: Optional[int] = None

    def reset(self) -> None:
        self._dwell.reset()
        self._focused = None
        self._focus_conf = 0.0
        self._candidate_since_ms = None
        self._focused_row_index = None

    def update(
        self,
        *,
        timestamp_ms: int,
        best_key_id: Optional[str],
        best_confidence: float,
        second_key_id: Optional[str],
        second_confidence: float,
        velocity_px_s: Optional[float],
        dt_s: float,
        best_row_index: Optional[int] = None,
    ) -> SelectionState:
        # Debug mode: chosen must equal best every frame (no hysteresis / no velocity suppression).
        if self._debug_follow_best:
            if best_key_id is None:
                state = self._dwell.update(None, dt_s)
                if state.target_id is None:
                    self._focused = None
                    self._focus_conf = 0.0
                return SelectionState(self._focused, state.progress, state.should_activate)

            if self._focused != best_key_id:
                self._dwell.reset()
            self._focused = best_key_id
            self._focus_conf = float(best_confidence)
            state = self._dwell.update(hash(self._focused), dt_s)
            return SelectionState(self._focused, state.progress, state.should_activate)

        # Velocity suppression: when saccade-like movement, freeze focus to reduce flicker.
        # (Can be effectively disabled by setting `velocity_suppress_px_s` very high.)
        if velocity_px_s is not None and velocity_px_s >= self._vel_suppress:
            best_key_id = self._focused
            best_confidence = self._focus_conf

        # Focus switching logic (hysteresis)
        if best_key_id is None:
            state = self._dwell.update(None, dt_s)
            if state.target_id is None:
                self._focused = None
                self._focus_conf = 0.0
            return SelectionState(self._focused, state.progress, state.should_activate)

        # Critical anti-sticky behavior: if the model's best key differs from focused,
        # do NOT continue dwelling on the old focused key.
        if self._focused is not None and best_key_id != self._focused:
            self._dwell.reset()

        if self._focused is None:
            self._focused = best_key_id
            self._focus_conf = best_confidence
            self._focused_row_index = best_row_index
            self._candidate_since_ms = None
        elif best_key_id != self._focused:
            cross_row = (
                self._focused_row_index is not None
                and best_row_index is not None
                and int(best_row_index) != int(self._focused_row_index)
            )
            margin = self._cross_row_switch_margin if cross_row else self._switch_margin
            min_ms = self._cross_row_min_switch_ms if cross_row else self._min_switch_ms
            margin_ok = (best_confidence - self._focus_conf) >= margin
            if margin_ok:
                if self._candidate_since_ms is None:
                    self._candidate_since_ms = timestamp_ms
                if (timestamp_ms - self._candidate_since_ms) >= min_ms:
                    self._focused = best_key_id
                    self._focus_conf = best_confidence
                    self._focused_row_index = best_row_index
                    self._candidate_since_ms = None
            else:
                self._candidate_since_ms = None
        else:
            self._focus_conf = best_confidence
            if best_row_index is not None:
                self._focused_row_index = best_row_index
            self._candidate_since_ms = None

        state = self._dwell.update(hash(self._focused) if self._focused is not None else None, dt_s)
        return SelectionState(self._focused, state.progress, state.should_activate)

