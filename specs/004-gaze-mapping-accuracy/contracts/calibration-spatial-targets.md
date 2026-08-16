# Contract: Spatial Calibration Targets

**Version**: 1.0.0  
**Feature**: `004-gaze-mapping-accuracy`

## Purpose

Define calibration as teaching **gaze representation → screen coordinates**.
Targets are spatial. Keyboard characters are not training labels.

## Target record

```text
CalibrationTarget
  target_id: str
  screen_x: float
  screen_y: float
  label: str              # logging / overlay progress only
  grid_row, grid_col: int # optional spatial grouping
  key_id: str             # optional coincidence; empty if off-key
```

## Fitting contract

```text
fit(samples: list[(GazeRepresentation, screen_x, screen_y)]) -> GazeMapping
```

MUST NOT take key label, key id, or row name as a regression feature unless
an approved experiment record justifies it (FR-030). A unit/contract test
MUST pin `fit(samples: list[(GazeRepresentation, x, y)])` — spatial only.

## Domains

```text
calibration_domain:  AABB containing all targets
prediction_domain:   AABB of Feature 003 letter/editing keys
                     (letters + Shift, Backspace, Space, Enter, Calibrate)
```

- Prediction domain is where mapped-key accuracy is required (research R4).
- Calibration domain is chosen to support that region; it MAY extend beyond
  the keyboard, stay inside it, or (later) differ — **one layout candidate
  per experiment** after baseline (research R4 A/B/C). Further candidates
  MAY follow revert/inconclusive. A failed first candidate MUST NOT prove
  the current 15 is optimal.
- **Suggestion / prediction-bar** keys are outside `prediction_domain`
  acceptance (SC-010 preservation only).
- Baseline / control layout: current product key-centered 15. Not assumed
  optimal. Count is not frozen.

## Overlay vs typing geometry

- Overlay may be fullscreen; dots are drawn at `screen_x/y` converted into
  overlay-local coordinates.
- Taught coordinates MUST remain the same global values used for hit-test
  after the overlay closes.
- Mapper clip bounds MUST cover `prediction_domain`, not the fullscreen
  overlay, unless a later experiment expands the prediction domain.

## Quality grouping

Peer/outlier/row checks that remain MUST group by `grid_row` / `grid_col` or
by screen position — not by parsing `key_q`-style labels for `"top"`/`"left"`.

Those indices themselves MUST be **investigated** (research R5), not assumed
correct: Space and other non-letter controls MUST NOT silently share a
letter-row or coarsened column index if that mixes distinct `screen_y` /
`screen_x` clusters. Confirm tags against coordinates before retagging or
changing region/outlier conclusions.

## Quality / pass-fail gates

Keyboard-mode gates that currently **warn** rather than block (LOOCV px,
train-pixel error, region/row checks) are an investigation (research R10).
Correlate warning-only vs blocking vs clean sessions with held-out
mapped-key and practical typing. Do not harden all warnings into product
blocks, and do not ignore them, without that evidence. LOOCV MUST NOT
become the sole product accept/reject. Gate-policy changes MUST NOT add
on-screen metrics during fixation; pass/fail remains **after** the session
(FR-004, FR-005, SC-009).

## Fixation UI

During fixation: target mark + optional progress (`n / N`) only. No metrics,
sample counts, or debug feature text (FR-004, SC-009).
