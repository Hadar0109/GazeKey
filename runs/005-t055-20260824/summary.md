# T055 session 2 — integrated functional sweep

**Date**: 2026-08-24  
**Session id**: `005-t055-20260824`  
**Status**: **USER-REPORTED PASS** for the control sweep and the extra
functional gates listed below. Distinct from T054 session `005-t054-20260824`.

**Product condition**: chin/head support (Feature 005 requirement).  
**Tree**: `f0f60d5ce37839366bc9efe66fe912f7e51f76c6`

**Path unchanged**: GazeFollower → GazeSample → origin+dpr → live QRects →
dwell → OS. No accuracy investigation, key resize, hit-area change, mapper,
bias, affine, extra smoothing, or `generate_points` change.

This run is **not** a substitute for T056 (SC-001 requires a third distinct
session). It is **not** a `hadar` accuracy evaluation (T057 deferred).

---

## User report (binding)

One integrated run passed:

| Behavior | Gate | Result |
|----------|------|--------|
| Letters | T055 sweep / SC-003 | PASS |
| Editing keys | T055 sweep / SC-004 | PASS |
| Suggestions (reach / display) | T055 sweep / SC-005 | PASS |
| Blink / invalid-gaze: dwell does not complete, no type | T058 / SC-016 validity | PASS |
| OS typing into an external application | T059 / SC-009 | PASS |
| Suggestion acceptance (suffix + Space) | T060 (Feature 005) / SC-011 | PASS |
| Official Preview + Calibration, return to keyboard | SC-012 live reconfirm | **superseded** — later found broken; PASS is T045 |

`hadar` typing was **not** recorded or scored as an accuracy metric. That
evaluation is deferred until after product integration, when the operator
chooses either the 32M-image GazeFollower model or key-size / hit-area
work. T057 stays open. Feature 004 T060 formulas are not used.

Residual gaze error remains accepted from T054. No correction.

## Recalibration (SC-012)

- Stage E implementation: T042–T047 (official Preview + Calibration; Qt
  hidden; `stop_sampling` then pygame; resume sampling only if the new
  model is usable; no previous-SVR fallback).
- This session’s first live recalibrate was later found broken (GREEN
  ring and dwell gone after the second calibration). Do **not** treat
  that attempt as SC-012 PASS.
- Stage F live reconfirm PASS: T045 `runs/005-t045-recalibrate-20260824/summary.md`.

## Provenance

Same pin as T054: GazeFollower 1.0.2 / `553920edcb7998c029828677f50f6d8eb4a16249`,
`base.mnn` SHA-256 `2f96b95275fe6d7b79e98df3237ebb96e15ef5522c96968f08167da7e1954a96`,
cali_mode=13, camera 0/640×480/30, HeuristicFilter look-ahead 3,
CC BY-NC-SA 4.0, geometry `origin+dpr`.

## Replay

No GazeSample JSONL capture for this session. Live session remains valid.

## Quiet summary (SC-024)

- **Pass/fail**: PASS for listed functional gates; SC-012 live PASS is T045, not this session’s first recalibrate. T056 and T057 not closed.
- **Usability**: letters, editing, suggestions, blink-cancel, OS inject,
  suggestion accept. Recalibration resume is T045.
- **Metrics**: not used as cleanup or accuracy gate this session.
- **Next**: T056 distinct session 3. Cleanup hold stays.
