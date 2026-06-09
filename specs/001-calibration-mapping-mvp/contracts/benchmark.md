# Contract: Benchmark

**Version**: 1.0.0  
**Feature**: `001-calibration-mapping-mvp`

## Purpose

Validate `GazeMapping` on held-out keys **independent** of calibration targets.

## Interface (logical)

```text
BenchmarkRunner
  run(mapper: GazeMapper, test_keys: list[BenchmarkTestKey]) -> BenchmarkRun

BenchmarkRun
  results: list[BenchmarkKeyResult]
  key_hit_accuracy: float
  row_accuracy: float
  median_pixel_error: float
  status: passed | failed    # vs success criteria (CQ-1)
  summary: RunSummary
```

## Test key set (MVP)

Fixed 15 keys — `DEFAULT_SAMPLE_KEYS` from `gazekey/debug/keyboard_accuracy.py`:

`Q, E, T, U, P, A, D, G, J, L, Z, C, B, M, Space`

Keys are resolved to screen centers via `layout_inspector` at runtime.

## Per-key procedure

1. Prompt user to look at the indicated key (highlight acceptable; no fixation-dot calibration UI).
2. Settle period (~1.2 s), then collect frames (~2.5 s) — reuse existing timings unless UX testing changes them.
3. Mean smoothed features → `mapper.predict()` → compare to intended key hit box and row.
4. Record `BenchmarkKeyResult`.

## Scoring

| Metric | Definition |
|--------|------------|
| `key_hit_accuracy` | `count(key_correct) / count(test_keys)` |
| `row_accuracy` | `count(row_correct) / count(test_keys)` |
| `median_pixel_error` | median distance from predicted point to intended key center |

## Pass/fail

Compare aggregates to success criteria **SC-001–SC-004** (CQ-1 resolved: initial
spec thresholds, not tightened). **SC-001**: on the 15-key set, **≥10 correct keys**
passes (display ~67%; not strict fractional `>= 0.67`).

Scoring hit-test MUST use the same tight/snap geometry as the active keyboard path
(`KeyHitTester` / `hit_test_layout_keys` on `layout_inspector` rects).

LOOCV or calibration gate metrics MUST NOT override benchmark fail.

## UI integration

- Benchmark is **user-initiated** after calibration (CQ-3 resolved).
- Requires `CalibrationSession.status == passed`.
- Does not activate keys or modify text buffer.

## Existing implementation mapping

| Piece | Current code |
|-------|--------------|
| Core logic | `gazekey/debug/keyboard_accuracy.py` |
| Console summary | `print_accuracy_summary()` |
| UI trigger | Opt-in via `GAZEKEY_KEYBOARD_ACCURACY_DEBUG=1` — **promote to first-class MVP action** |

## Separation from calibration

| | Calibration | Benchmark |
|---|-------------|-----------|
| Points | Layout evaluation C1/C2/C3 | Fixed 15 keys |
| Purpose | Fit mapping | Test mapping |
| UI | Fixation dots | Key highlight / prompt sequence |
