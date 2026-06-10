# Contract: Evaluation Module (minimal)

**Version**: 1.2.0  
**Feature**: `001-calibration-mapping-mvp`

## Purpose

Thin module for benchmark execution, pass/fail scoring, and failure detail in run
summaries. **Not** a diagnostics framework.

## In scope

```text
gazekey/evaluation/
  benchmark_runner.py       # 15-key scoring; DEFAULT_SAMPLE_KEYS; SC-001–SC-003
  benchmark_session.py      # Timed per-key settle/collect
  run_summary.py            # Console + runs/<session_id>/ records
  failure_analysis.py       # Per-key misses, dx/dy, likely_cause
  coverage_diagnostics.py   # coverage.json at calibration finish
  session_paths.py          # runs/<session_id>/ path helpers
  benchmark_diagnostics.py  # benchmark_diag.json (optional)
```

## Out of scope

- Multi-mapper comparison (deleted legacy tooling)
- Dashboards, replay UI, automated AR tooling (until approved)

## T061 baseline discipline (Phase 11)

| Step | Requirement |
|------|-------------|
| T061A | Run 1 → `runs/<session_id_A>/` |
| T061B | Run 2, same config → `runs/<session_id_B>/` |
| T061C | Aggregate → `runs/t061_baseline_comparison.md` |
| T061D | Record first lever choice (no code change) |
| T062+ | Compare all iterations vs T061 two-run set |

**Historical only**: T029, pre-restart `iteration_*`, deleted run folders.

## One-change iteration discipline

1. T061 complete before any tuning
2. Each cycle: layout OR collection OR geometry OR PCA4 fit/smoothing/row bias
3. Failure inputs: dx/dy, row errors, failed keys, coverage.json, geometry
4. T036 documents vs T061 baseline set

## Acceptance

Tester can run benchmark, read pass/fail + per-key failures from
`runs/<session_id>/benchmark_summary.txt`, and compare sessions using
`runs/t061_baseline_comparison.md` as the active reference.
