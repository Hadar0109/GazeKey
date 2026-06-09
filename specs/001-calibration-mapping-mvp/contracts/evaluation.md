# Contract: Evaluation Module (minimal)

**Version**: 1.0.0  
**Feature**: `001-calibration-mapping-mvp`

## Purpose

Thin module for benchmark execution, pass/fail scoring, and failure detail in run
summaries. **Not** a diagnostics framework.

## In scope

```text
gazekey/evaluation/
  benchmark_runner.py    # Run 15-key test; produce BenchmarkRun
  run_summary.py         # Write console + lightweight file record
  failure_analysis.py    # Format per-key misses, dx/dy, row errors into summary
```

## Out of scope

- Multi-mapper comparison or replay (`keyboard_accuracy_compare.py`, mapper_diag)
- Dashboards, HTML reports, session diff UI
- LOOCV-primary gating or geometry debug overlays
- Framework for pluggable analysis plugins

## Dependencies

- `gazekey/layout/layout_inspector.py` — key centers and hitboxes (must be verified)
- `gazekey/typing/key_hit_tester.py` — hit test for benchmark scoring
- `gazekey/mapping/ridge.py` — `pca4_baseline` predict only
- Extract from `gazekey/debug/keyboard_accuracy.py` — do not fork compare tooling

## Task discipline

1. **Baseline run** — record summary before major changes
2. **Failure analysis** — document key/row failure patterns after each benchmark
3. **Compare** — label re-runs as improved / unchanged / regressed vs baseline

## Acceptance

Module is acceptable when a tester can run benchmark, read pass/fail + per-key
failures from one summary, and compare two sessions — without additional tools.
