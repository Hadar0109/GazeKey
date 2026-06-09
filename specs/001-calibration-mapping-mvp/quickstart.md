# Quickstart: Calibration & Gaze Mapping MVP Validation

**Feature**: `001-calibration-mapping-mvp`  
**Date**: 2026-06-09 (revised)

Manual procedure to validate the MVP after implementation.

## Prerequisites

- Camera working; face visible at normal typing distance
- Single monitor; virtual keyboard on primary screen
- Quiet lighting; minimize head movement between calibration targets

## 1. Launch

```bash
python main.py
```

**Expected (MVP)**:

- App starts; per-session calibration begins
- Terminal shows essential status only
- Fixation overlay: **dot + progress only** — no metrics, no camera preview
- Floating camera preview window **hidden by default** (CQ-4)

## 2. Calibrate

1. Look at each calibration target until it advances.
2. Complete all targets; wait for pass/fail **after** session ends.

**Pass criteria**: All targets collected; run summary records outcome.

## 3. Preview (read-only)

After calibration pass:

1. Gaze preview indicator on keyboard (position only).
2. Confirm tracking across keys.

**Must NOT happen**: Key selection, dwell activation, text buffer changes from gaze.

## 4. Benchmark (developer flag only)

Benchmark is **not** exposed in the normal UI. To run the 15-key validation set during development:

```bash
set GAZEKEY_DEV_BENCHMARK=1
python main.py
```

After calibration pass and preview ready, the benchmark auto-starts. Record from summary: key-hit accuracy, row accuracy, median error, PASS/FAIL.

**Pass thresholds** (CQ-1 — initial, not tightened):

- ≥ 10/15 keys correct (67%)
- Median error ≤ 55 px
- ≥ 80% correct row
- Across 3 sessions: every session ≥ 8/15; spread ≤ 20 percentage points

## 5. Baseline before changes

Before any major calibration, geometry, or PCA4 change:

1. Run full calibrate → preview → benchmark.
2. Save run summary as **baseline** in `runs/`.
3. Only then apply the change and re-benchmark.

## 6. Result-driven iteration

**Prerequisite**: Baseline run (§5) must complete end-to-end. If not, fix blocking
flow issues first — do not start accuracy iterations.

When benchmark fails, use **per-key failure detail** and `plan.md` decision guide:

- Wrong row / large `dy` → PCA4 fit or calibration layout (pick one)
- Wrong column / `dx` → geometry or PCA4 u-fit or layout (pick one)
- Erratic misses → fixation/collection
- Preview OK, benchmark wrong → geometry/hitboxes first

Apply **exactly one** change per iteration (layout, collection, geometry, or
PCA4 fit in `ridge.py` / `typing_candidate.py`). Re-benchmark vs baseline.

**Do not**: Combine multiple fixes in one iteration; re-run mapper variant matrices.

## 7. Geometry check

**Phase 2 (automated)**: `tests/unit/test_layout_geometry.py` + `runs/geometry_check.txt`
on a synthetic keyboard — sufficient for foundational work.

**Before T029 baseline (manual, required)**: On the live `VirtualKeyboard` UI, confirm
calibration dots and benchmark key highlights align with visible key centers; check
`runs/geometry_check.txt` has no mismatches on synthetic fixture. If on-screen keys
look offset, fix geometry before interpreting benchmark scores.

Benchmark hit-test uses the same tight/snap rules as `KeyHitTester` (`hit_test_layout_keys`).

## 8. Repeatability (SC-004)

Repeat steps 2–4 for **3 sessions** (restart app each time).

## 9. Verbose debugging (optional)

```bash
set GAZEKEY_VERBOSE=1
python main.py
```

## Success checklist

- [ ] Fixation UI distraction-free; no camera preview on calibration overlay (SC-006, CQ-4)
- [ ] Preview read-only (SC-007)
- [ ] Benchmark separate from calibration targets
- [ ] PCA4 only in active path — no experimental mapper switching
- [ ] Run summary answers pass/fail without verbose logs (SC-005)
- [ ] Meets SC-001–SC-004 thresholds

## Reference baselines

Archived sessions: key accuracy **20%–60%** (best 9/15). MVP targets meaningful
improvement via calibration + PCA4 tuning, not mapper variant hunts.
