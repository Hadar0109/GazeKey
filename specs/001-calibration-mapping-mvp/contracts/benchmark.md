# Contract: Benchmark

**Version**: 1.1.0  
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

Fixed 15 keys — `DEFAULT_SAMPLE_KEYS` in `gazekey/evaluation/benchmark_runner.py`:

`Q, E, T, U, P, A, D, G, J, L, Z, C, B, M, Space`

Keys are resolved to screen centers via `layout_inspector` at runtime.

## Per-key procedure

1. Prompt user to look at the indicated key (highlight acceptable; no fixation-dot calibration UI).
2. Settle period (~1.2 s), then collect frames (~2.5 s) — `SETTLE_MS` / `COLLECT_MS` in `benchmark_runner.py`.
3. Mean smoothed features → `mapper.predict()` → compare to intended key hit box and row.
4. Record `BenchmarkKeyResult` with `dx`, `dy`, `error_px`, `row_correct`.

## Scoring

| Metric | Definition |
|--------|------------|
| `key_hit_accuracy` | `count(key_correct) / count(test_keys)` |
| `row_accuracy` | `count(row_correct) / count(test_keys)` |
| `median_pixel_error` | median distance from predicted point to intended key center |

## Pass/fail

Compare aggregates to success criteria **SC-001–SC-003** per run (CQ-1). **SC-004**
repeatability is assessed across sessions (manual or future evaluator).

**SC-001**: on the 15-key set, **≥10 correct keys** passes (display ~67%).

Scoring hit-test MUST use the same tight/snap geometry as the active keyboard path
(`hit_test_layout_keys` on layout inspector rects).

LOOCV or calibration gate metrics MUST NOT override benchmark fail.

## Failure analysis inputs

Each benchmark run SHOULD feed iteration decisions with:

- Per-key `dx` / `dy` and miss list (`failure_analysis.py`)
- Row error count
- Optional `benchmark_diag.json` (extended per-key detail)
- Calibration `coverage.json` from the same session folder

## UI integration (CQ-3)

- Benchmark auto-starts after preview when `GAZEKEY_DEV_BENCHMARK=1`.
- **No** normal user-facing benchmark button or menu in MVP.
- Requires successful calibration + usable mapper.
- Does not activate keys or modify text buffer.

## Baseline and iteration comparison

- **Active reference**: T061 two-run set (`runs/t061_baseline_comparison.md`).
- **T061A/T061B**: identical config; artifacts in separate `runs/<session_id>/` folders.
- **T062+**: each iteration compares vs T061; document one change per cycle.
- T029 and pre-restart iteration artifacts are historical only.

## Existing implementation mapping

| Piece | Current code |
|-------|--------------|
| Scoring + thresholds | `gazekey/evaluation/benchmark_runner.py` |
| Timed session | `gazekey/evaluation/benchmark_session.py` |
| UI | `gazekey/ui/benchmark_controller.py` |
| Summary | `gazekey/evaluation/run_summary.py` → `runs/<session_id>/benchmark_summary.txt` |
| Diagnostics | `gazekey/evaluation/benchmark_diagnostics.py` → `benchmark_diag.json` |

## Separation from calibration

| | Calibration | Benchmark |
|---|-------------|-----------|
| Points | Layout evaluation (9/13/15 via `targets.py`) | Fixed 15 keys |
| Purpose | Fit mapping | Test mapping |
| UI | Fixation dots | Key highlight / prompt sequence |
