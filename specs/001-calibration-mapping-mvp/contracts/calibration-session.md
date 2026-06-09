# Contract: Calibration Session

**Version**: 1.0.0  
**Feature**: `001-calibration-mapping-mvp`

## Interface (logical)

```text
CalibrationController
  start(layout_mode: str, targets: list[CalibrationTarget]) -> session_id
  process(features: FrameFeatures, dt_ms: float) -> CalibrationUIState
  finish() -> CalibrationSessionResult

CalibrationUIState
  target_screen_x, target_screen_y: float   # current dot position
  progress_current, progress_total: int     # optional progress only
  # MUST NOT include metrics, sample counts, or debug text during fixation

CalibrationSessionResult
  status: passed | failed | aborted
  samples: list[CalibrationSample]
  failure_reason: str | null
  summary: RunSummary
```

## UI constraints (Principle XI)

**During fixation** overlay MAY show:

- Target dot at `(target_screen_x, target_screen_y)`
- Progress indicator (`progress_current` / `progress_total`)

**During fixation** overlay MUST NOT show:

- Instructions, LOOCV, RMS, sample counts, quality scores, rejection reasons

**After session ends** UI MAY show:

- Pass/fail result
- Option to recalibrate

**Camera preview** (CQ-4): During fixation, floating webcam window MUST be
off by default (user may opt in) and MUST NOT appear on top of or interfere with
the fixation overlay. After calibration, camera preview is available/open in
normal UI.

## Pass/fail rules (research R-4)

**Pass**:

- All targets in sequence attempted
- Each target meets minimum accepted sample count
- Head drift / tracking within configured limits
- Face predominantly detected during collection

**Fail**:

- Insufficient samples, excessive drift, or prolonged tracking loss
- User abort

**Not required for pass**:

- LOOCV RMS threshold
- Region gate thresholds
- Benchmark key-hit accuracy (that is benchmark's job)

## Existing implementation mapping

| Contract piece | Current code |
|----------------|--------------|
| `process()` | `CalibrationV2Session.process()` |
| Fixation gate | `fixation_gate.py` |
| Targets | `targets.py` |
| Overlay | `calibration_overlay.py` — **needs debug text stripped** |
| CSV samples | `calibration_csv.py` |

## Side effects

- Append calibration sample rows (existing CSV or session folder)
- Write `RunSummary` on finish via `write_summary()` path
