# Data Model: Gaze Mapping Accuracy

**Feature**: `004-gaze-mapping-accuracy`  
**Date**: 2026-08-16  
**Spec**: [spec.md](./spec.md)

## Overview

Entities support: collect spatial calibration samples → fit the existing
simple mapper → live mapped gaze → key hit (focus) → (unchanged) dwell.
Developer evaluation observes that path; it does not feed it.

Calibration targets are **spatial**. Evaluation keys are **keyboard
controls** used to score mapped-key accuracy. They are related by
coordinates, not by character identity in the fit.

## Entities

### CalibrationTarget

A spatial screen coordinate for fixation. Not a keyboard character.

| Field | Type | Description |
|-------|------|-------------|
| `target_id` | string | Stable id (e.g. `T01`) |
| `label` | string | Internal/logging only; not shown during fixation; **not** used in fit |
| `screen_x`, `screen_y` | float | Global screen coordinates (teaching Y) |
| `grid_row`, `grid_col` | int | Optional spatial index for quality grouping (-1 if unused). **Investigate** that tags match `screen_x/y` clusters — Space / non-letter controls MUST NOT be assumed to share a letter-row index |
| `key_id` | string | Optional coincidence with a visible key; empty if off-key; **not** a fit feature |

**Validation**: Coordinates in the chosen **calibration domain**. Set defined
before the session starts. Fit uses only `(gaze representation, screen_x,
screen_y)`.

**Rules**:

- Coincidence with a key center does not make the target that character.
- Changing QWERTY labels must not change taught positions unless coordinates
  changed.

---

### CalibrationDomain / PredictionDomain

| Entity | Meaning |
|--------|---------|
| **Calibration domain** | Axis-aligned screen region containing all `CalibrationTarget`s |
| **Required prediction domain** | Axis-aligned region where live gaze must be accurate for typing — Feature 003 letter/editing keyboard (research R4) |

**Rules**: Domains MAY differ. Target placement is chosen to support the
prediction domain, not to enumerate key characters.

---

### CalibrationObservation

One frame of gaze signals while a target is shown.

| Field | Type | Description |
|-------|------|-------------|
| `target_id` | string | Current target |
| `timestamp_ms` | int | Frame time |
| `gaze_representation` | GazeRepresentation | Full mapping vector (all eyes used by the mapper) |
| `accepted` | bool | Passed the stability gate **on that representation** |
| `reject_reason` | string? | e.g. blink, unstable, jump, head_drift, missing_eye |

**Rules**: Unstable observations in the mapper’s representation MUST NOT be
silently accepted (FR-002).

---

### GazeRepresentation

The defined eye-signal vector for fit and predict (as-built: `pca_uL`,
`pca_uR`, `pca_vL`, `pca_vR`, plus any documented auxiliaries).

| Field | Type | Description |
|-------|------|-------------|
| `u_l`, `v_l`, `u_r`, `v_r` | float? | Per-eye geometric eye-local coords |
| `aux` | optional | Only if the same fields exist at fit and predict |

**Validation**: Left and right components have documented, consistent
semantics (axis direction, missing-value policy) at collection and at
predict (FR-008, FR-011).

---

### TargetSample

Combined teaching sample for one target.

| Field | Type | Description |
|-------|------|-------------|
| `target_id` | string | Links to CalibrationTarget |
| `gaze_representation` | GazeRepresentation | Coherent combination of accepted observations |
| `screen_x`, `screen_y` | float | Copied from the target (spatial) |
| `observation_count` | int | Accepted frames used |
| `aggregation` | enum | Must preserve same-frame relationships (FR-003) |

**Rules**:

- Do not independently filter channels such that the stored vector could not
  arise from any kept frame (unless an experiment **keep**s that after
  evidence).
- Require the same completeness policy as `predict` (typically all four
  components present).

---

### GazeMapping

Fitted spatial mapper (existing PCA4 ridge starting point).

| Field | Type | Description |
|-------|------|-------------|
| `mapper_id` | string | e.g. `pca4_baseline` |
| `session_id` | string | Source calibration |
| `clip_bounds` | (x0,y0,x1,y1)? | Must cover required prediction domain |
| `predict(rep)` | (x, y) | Screen coordinates (as-built: clamped to `clip_bounds`) |
| `alpha_selected` | float? | Documented when Phase E diagnoses auto-alpha (research R11) |

**Rules**: One active mapping after a usable calibration. No evaluation
object in `predict`. Key labels do not enter `predict`. Out-of-domain
clamp is a **geometry investigation** (research R7), not an automatic
remove/expand. Auto-alpha (largest near-best LOOCV) is a **Phase E**
investigation, not a Phase A–D change.

---

### MappedGaze

Live predicted screen position.

| Field | Type | Description |
|-------|------|-------------|
| `x`, `y` | float | Global screen coordinates |
| `valid` | bool | False if representation incomplete / quality reject |
| `source_representation` | GazeRepresentation | Compatible with fit (FR-009) |

---

### MappedKey (focus)

Keyboard control identified from `MappedGaze` via the same hit-test as
product typing, **before dwell**.

| Field | Type | Description |
|-------|------|-------------|
| `key_id` | string | Layout id |
| `key_action` | string | Semantic action (for logging / word checks only) |
| `rect` | screen rect | Tight visible bounds |
| `inside_tight` | bool | Point in `rect` (mapped-key success definition) |

**Rules**: Wrong `MappedKey` is a mapping failure even if dwell never fires
(FR-034).

---

### MappingEvaluationRun

Developer-only measurement. Not a product runtime input.

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Evaluation id (may share calib session prefix) |
| `baseline_ref` | string? | Baseline A and/or B run ids being compared |
| `layout_mode` | string | Active calibration layout name |
| `repeatability_results` | list[LocationResult] | At calibration coordinates |
| `held_out_results` | list[LocationResult] | Held-out **letter** keys |
| `editing_control_results` | list[LocationResult] | Shift, Backspace, Space, Enter, Calibrate (FR-023) |
| `inside_key_rate` | float | Primary mapped-key aggregate (by slice) |
| `focus_stability` | float | Mean per-location frame hit rate |
| `median_error_px` | float | Supplementary |
| `median_dx_over_width` | float | Key-relative |
| `median_dy_over_height` | float | Key-relative |
| `row_accuracy` | float | Supplementary |
| `fidelity_notes` | string | Documented diffs vs live typing path |
| `quality_gate_kind` | enum? | `blocking` \| `warning_only` \| `clean` — correlate with held-out (research R10); diagnostic, not a product input |
| `clamp_hit_rate` | float? | Fraction of frames whose raw predict was outside clip bounds |
| `unclamped_inside_key_rate` | float? | Diagnostic vs clamped primary score (research R7) |
| `status` | enum | vs **reference floors** and/or vs baseline — not auto final 004 accept |

### LocationResult

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Human key name for the tester |
| `intended_rect` | screen rect | Tight key bounds |
| `was_calibration_location` | bool | Slice membership |
| `rep_x`, `rep_y` | float | Representative mapped point |
| `inside_tight` | bool | Primary correctness |
| `focus_stability` | float | Frames on intended key |
| `dx`, `dy`, `error_px` | float | To intended center |
| `dx_over_width`, `dy_over_height` | float | Key-relative |
| `row_correct` | bool | |
| `dwell_activated_id` | string? | Optional; not primary |

---

### CurrentStateBaseline

**Two** `MappingEvaluationRun`s (A and B) captured on the **unchanged**
Feature 003 mapping path after evaluation fidelity is in place, **before**
the first accuracy-related product/mapping change.

**Rules**: Later experiments compare to **both** runs (or the last **keep**
state). Missing either session blocks accuracy code changes (FR-028).
Spread between A and B is session-noise context. Distinct from the
3-session final protocol (SC-004) on the kept stack.

---

### ExperimentRecord

One accuracy iteration.

| Field | Type | Description |
|-------|------|-------------|
| `hypothesis` | string | Failure pattern + expected mechanism |
| `logical_area` | enum | eval, collection, sync, geometry, coverage, mapper. Collection includes warning-only quality gates and spatial row/col metadata. Geometry includes clip/clamp. Mapper includes auto-alpha (Phase E). |
| `change_summary` | string | One focused modification |
| `eval_before` | session ids | Baseline A+B or last keep |
| `eval_after` | session id | |
| `decision` | enum | `keep` \| `revert` \| `inconclusive` |
| `keep_git_sha` | string? | Required when `decision` is `keep` |
| `notes` | string | |

**Rules**: `inconclusive` or unproven ⇒ do not stack; revert to last keep
**commit** before the next mapping change (FR-026). `keep` without
`keep_git_sha` is incomplete.

---

## Relationships

```text
CalibrationTarget (spatial) ──< CalibrationObservation
CalibrationObservation ──> TargetSample (coherent)
TargetSample + CalibrationTarget.screen_* ──> GazeMapping.fit
GazeRepresentation (live) ──> GazeMapping.predict ──> MappedGaze
MappedGaze + layout rects ──> MappedKey (focus)
MappedKey ──> (unchanged) dwell ──> KeyAction   [003 path; consume only]

MappingEvaluationRun observes MappedGaze/MappedKey; never writes GazeMapping
CurrentStateBaseline is a MappingEvaluationRun
ExperimentRecord compares two MappingEvaluationRuns
```

## State: calibration session (unchanged product UX)

```text
in_progress → passed | failed | aborted
```

Pass/fail after session ends. Fixation UI: target + optional progress only.

**Investigate (research R10):** as-built keyboard-mode quality may **warn**
on LOOCV / train-pixel / region checks while still passing. Record
`blocking` vs `warning_only` vs `clean` on evaluation runs; correlate with
held-out mapped-key. Do not change pass/fail policy without that evidence.
Fixation UI stays target + optional progress; pass/fail only after the
session even if gates change.

## State: experiment

```text
planned → running → keep | revert | inconclusive
inconclusive / revert → next experiment starts from last keep
keep → becomes comparison parent for the next experiment
```
