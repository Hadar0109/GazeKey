# T054 session 1 — live integrated keyboard

**Date**: 2026-08-24  
**Session id**: `005-t054-20260824`  
**Status**: **USER-REPORTED PASS** for the live integrated keyboard. Remaining
gaze error is small and **accepted**. Do **not** reopen the accuracy
investigation, resize keys, or add gaze correction.

**Product condition**: chin/head support (Feature 005 requirement).  
**Tree**: `f0f60d5ce37839366bc9efe66fe912f7e51f76c6`  
(`feat(feature005): reconnect GazeFollower typing and official recalibrate`)

**Path**: official GazeFollower → `GazeSample` → `origin+dpr` → live QRect
hit-test → existing dwell → ActionDispatcher / OS. No post-GF mapper, bias,
affine, extra smoothing, or `generate_points` change.

---

## User report (binding)

The live integrated keyboard test passed successfully. Residual pointing error
is accepted for this stage. Accuracy work stays closed.

This session does **not** by itself authorize Stage G cleanup. SC-001 later
required T056 as a third distinct session (now PASS). T057 `hadar` is
deferred and is not an accuracy metric.

## Sweep (as reported)

| Item | Result |
|------|--------|
| Integrated product on live Qt keyboard | PASS (user) |
| GazeFollower production path preserved | yes |
| Residual spatial error | small; accepted; no correction |
| Full letter / editing / suggestion checklist enumerated | not itemized in this report; user accepted the live keyboard as passing |
| Numeric mapped-key / pixel-error benchmark | not captured this session (SC-013 evidence, not a cleanup formula) |
| Stage E live recalibration reconfirm (official Preview + Calibration, return to keyboard) | **not in this session**; SC-012 live PASS is T045 `005-t045-recalibrate-20260824` |

## Provenance (FR-022 / FR-041)

| Field | Value |
|-------|--------|
| upstream | https://github.com/GanchengZhu/GazeFollower |
| commit | `553920edcb7998c029828677f50f6d8eb4a16249` |
| version | 1.0.2 |
| model | `base.mnn` SHA-256 `2f96b95275fe6d7b79e98df3237ebb96e15ef5522c96968f08167da7e1954a96` |
| cali_mode | 13 |
| camera | webcam 0, 640×480, 30 FPS |
| filter | HeuristicFilter(look_ahead=3) |
| license | CC BY-NC-SA 4.0 |
| geometry | `origin+dpr` (see `runs/_feature005/geometry_audit.json`, `pygame_qt_dpi_probe.json`) |
| eval_before | Feature 004 A/B `14938da0bdf0`, `34fb259ccdfd`; Feature 004 T060 `689c8a8ce90c`, `4f665467b260` (reference only) |

## Replay (T053)

Full GazeSample JSONL replay was **not** written for this live session
(`write_gaze_replay` exists as a tools helper and is not wired into the
product keyboard). Live Stage F sessions remain valid. T062 must restate
this incompleteness.

## Quiet summary (SC-024)

- **Pass/fail**: PASS (user-reported integrated keyboard).
- **Usability**: residual 0–1 key-class error accepted; no layout or mapper change.
- **Metrics**: qualitative only this session.
- **Next**: T055 distinct session 2. Do not start Stage G.
