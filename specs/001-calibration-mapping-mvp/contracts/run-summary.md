# Contract: Run Summary

**Version**: 1.0.0  
**Feature**: `001-calibration-mapping-mvp`

## Purpose

Answer: **what happened, and did calibration/mapping pass or fail?** (Constitution VII)

## Interface (logical)

```text
RunSummaryWriter
  write(summary: RunSummary) -> None
  format_console(summary: RunSummary) -> str

RunSummary
  session_id: str
  run_type: calibration | benchmark
  status: passed | failed
  primary_metrics: dict
  failure_reason: str | null
  timestamp: ISO-8601
```

## Console format (minimum)

**Calibration**:

```text
[calibration] PASS session=<id> layout=keyboard13 targets=13/13
[calibration] FAIL session=<id> reason=head_drift_exceeded
```

**Benchmark**:

```text
[benchmark] FAIL session=<id> keys=8/15 (53%) row=12/15 median_err=62px
[benchmark] PASS session=<id> keys=11/15 (73%) row=13/15 median_err=48px
```

## Persisted format (minimum)

One record per run — either:

- Append row to CSV sharing `session_id` column (extend `calibration_summary.csv` pattern), or
- Write `runs/<session_id>/summary.txt` with the same fields as console block

**Not required**: JSON dashboards, per-frame logs, multiple parallel files per run.

## Verbose mode

When `GAZEKEY_VERBOSE=1` (single flag to consolidate debug env vars):

- Per-target calibration detail
- Per-key benchmark detail

Default **off** — normal runs stay quiet.

## Existing implementation mapping

| Piece | Current code |
|-------|--------------|
| Calibration CSV | `gazekey/calibration2/calibration_csv.py` |
| Session write | `CalibrationV2Session.write_summary()` |
| Benchmark print | `print_accuracy_summary()` in `keyboard_accuracy.py` |

## Acceptance (SC-005)

A tester can state pass/fail and primary metrics from console output or one
saved record without reading verbose logs.
