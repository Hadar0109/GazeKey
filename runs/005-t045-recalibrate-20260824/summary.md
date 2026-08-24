# T045 recalibration — live USER GATE

**Date**: 2026-08-24  
**Session id**: `005-t045-recalibrate-20260824`  
**Status**: **USER-REPORTED PASS**

**Product condition**: chin/head support (Feature 005 requirement).  
**Tree**: `f0f60d5ce37839366bc9efe66fe912f7e51f76c6` plus the uncommitted
recalibration lifecycle fix (fresh second calibration; Qt consumers and
OS inject resume only when the new model is usable; no previous-SVR
fallback).

**Path unchanged**: GazeFollower → GazeSample → origin+dpr → live QRects →
dwell → OS. No HeuristicFilter, origin+dpr, dwell timing, mapping, or
key-geometry change.

This record is the SC-012 live reconfirm after the post-T055 resume bug
(GREEN ring and dwell gone after a second calibration). It does **not**
count as T056 / SC-001 session 3.

---

## User report (binding)

After a second **fresh** official Preview + 13-point Calibration:

| Behavior | Result |
|----------|--------|
| GREEN gaze ring returned and tracked | PASS |
| Dwell resumed | PASS |
| OS typing resumed | PASS |
| Previous calibration used as fallback | **no** (as required) |

---

## Notes

- Recalibration is a true new calibration. A rejected/failed/unusable
  new fit must fail closed (typing stays off; CALIBRATE again). That
  fail-closed path was not the subject of this live PASS.
- Residual pointing error remains accepted from T054. No accuracy work.

## Replay

No GazeSample JSONL capture. Live session remains valid.

## Quiet summary (SC-024)

- **Pass/fail**: PASS for live recalibration resume (SC-012).
- **Next**: T056 third distinct chin/head-support control sweep.
  Cleanup hold stays.
