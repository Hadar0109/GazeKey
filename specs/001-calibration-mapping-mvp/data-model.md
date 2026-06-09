# Data Model: Calibration & Gaze Mapping MVP

**Date**: 2026-06-09  
**Feature**: `001-calibration-mapping-mvp`

## Overview

Entities support a linear pipeline: collect calibration samples → fit mapping →
preview gaze → run benchmark → write run summary. Calibration targets and
benchmark test keys are **distinct sets**.

## Entities

### CalibrationTarget

A screen position for fixation during calibration.

| Field | Type | Description |
|-------|------|-------------|
| `target_id` | string | Stable id (e.g. `T01`) |
| `label` | string | Internal label (not shown during fixation) |
| `key_id` | string | Associated key if key-aligned; empty for gap points |
| `screen_x`, `screen_y` | float | Global screen coordinates |
| `grid_row`, `grid_col` | int | Optional row/col index for layout (-1 if N/A) |

**Validation**: Coordinates within virtual keyboard typing region; set defined
entirely before session starts.

---

### CalibrationSession

One calibration run from first target through outcome.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | UUID per app launch / calibration attempt |
| `layout_mode` | string | e.g. `keyboard9`, `keyboard13`, `keyboard15` |
| `targets` | list[CalibrationTarget] | Ordered fixation sequence |
| `samples` | list[CalibrationSample] | Per-target accepted feature means |
| `status` | enum | `in_progress` \| `passed` \| `failed` \| `aborted` |
| `failure_reason` | string? | Populated when `failed` |
| `started_at`, `ended_at` | timestamp | Session bounds |

**State transitions**:

```text
in_progress → passed   (all targets collected + sanity checks)
in_progress → failed   (quality/drift/tracking failure)
in_progress → aborted    (user exit or camera loss)
```

**Rules**:

- Partial sessions do not produce a usable `GazeMapping`.
- Pass/fail shown to user only after session ends.

---

### CalibrationSample

Aggregated gaze features for one calibration target.

| Field | Type | Description |
|-------|------|-------------|
| `target_id` | string | Links to CalibrationTarget |
| `frame_features_mean` | FrameFeatures | Mean of accepted frames during fixation |
| `sample_count` | int | Number of accepted frames |
| `accepted` | bool | Whether target met minimum sample threshold |

---

### GazeMapping

Fitted model from calibration samples to screen coordinates.

| Field | Type | Description |
|-------|------|-------------|
| `mapper_id` | string | e.g. `pca4_baseline`, `pca4_baseline+row_bias` |
| `session_id` | string | Source calibration session |
| `layout_mode` | string | Calibration layout used for fit |
| `fit_metrics` | dict | Supplementary (LOOCV RMS, corr, etc.) — not acceptance gate |
| `predict` | fn | `FrameFeatures` → `(screen_x, screen_y)` |

**Rules**:

- Exactly one active `GazeMapping` per successful calibration.
- Wrappers (row bias, local Y) are part of `mapper_id` transparency, not hidden layers.

---

### BenchmarkTestKey

A key used only for validation (not training).

| Field | Type | Description |
|-------|------|-------------|
| `key_id` | string | e.g. `Q`, `Space` |
| `screen_x`, `screen_y` | float | Key center from layout inspector |
| `row_index` | int | Keyboard row for row-accuracy scoring |

**MVP set**: 15 keys per `DEFAULT_SAMPLE_KEYS` (research R-2).

---

### BenchmarkRun

Structured evaluation after calibration.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Links to calibration session |
| `test_keys` | list[BenchmarkTestKey] | Ordered evaluation sequence |
| `results` | list[BenchmarkKeyResult] | Per-key outcomes |
| `key_hit_accuracy` | float | Fraction correct (0–1) |
| `row_accuracy` | float | Fraction correct row (0–1) |
| `median_pixel_error` | float | Median gaze-to-target distance (px) |
| `status` | enum | `passed` \| `failed` (vs success criteria) |
| `started_at`, `ended_at` | timestamp | Run bounds |

---

### BenchmarkKeyResult

| Field | Type | Description |
|-------|------|-------------|
| `key_id` | string | Intended key |
| `predicted_key_id` | string? | Key hit by mapped gaze (null if none) |
| `pixel_error` | float | Distance to intended key center |
| `row_correct` | bool | Predicted row matches intended row |
| `key_correct` | bool | Predicted key matches intended key |

---

### RunSummary

Human-readable outcome for one calibration or benchmark run.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Correlation id |
| `run_type` | enum | `calibration` \| `benchmark` |
| `status` | enum | `passed` \| `failed` |
| `primary_metrics` | dict | Type-specific (see below) |
| `failure_reason` | string? | Brief text when failed |

**Calibration `primary_metrics`**: `targets_completed`, `layout_mode`, optional `loocv_rms`

**Benchmark `primary_metrics`**: `key_hit_accuracy`, `row_accuracy`, `median_pixel_error`, `keys_correct`, `keys_total`

**Rules**:

- Readable in console and/or one file row — no prescribed multi-file bundle.
- Verbose detail optional; not required for acceptance.

---

### FrameFeatures (existing — reuse)

Eye feature vector per frame from `gazekey/features/feature_types.py`. Used
as input to calibration collection, mapping predict, and benchmark averaging.

---

## Relationships

```text
CalibrationSession 1──* CalibrationSample
CalibrationSession 1──1 GazeMapping (on pass)
GazeMapping 1──* BenchmarkRun (benchmark requires mapping)
BenchmarkRun 1──* BenchmarkKeyResult
CalibrationSession 1──1 RunSummary (calibration)
BenchmarkRun 1──1 RunSummary (benchmark)
```

## Configuration (planning-time, not runtime entities)

| Config key | Purpose | MVP values |
|------------|---------|------------|
| `calibration_layout` | Target set for learning | One layout active; adjust from benchmark evidence (C1/C2/C3) |
| `mapper_id` | Mapping stack | **`pca4_baseline`** — fixed direction; no variant matrix |
| `benchmark_keys` | Validation set | Fixed 15 keys (R-2) |
| `success_thresholds` | Pass/fail gates | CQ-1 resolved — initial spec SC-* values |
