# Quickstart: Calibration & Gaze Mapping MVP Validation

**Feature**: `001-calibration-mapping-mvp`  
**Date**: 2026-06-10 (revised 6 — T061 two-run baseline)

Manual procedure to validate the MVP and run accuracy iterations.

## Prerequisites

- Camera working; face visible at normal typing distance
- Single monitor; virtual keyboard on primary screen
- Quiet lighting; minimize head movement between calibration targets
- Phase 10 cleanup complete; **`runs/` cleaned** for Phase 8 fresh start
- Active path: `gazekey/calibration/`, `gazekey/mapping/config.py`

## Historical vs active evidence

| Evidence | Status |
|----------|--------|
| T029 / `baseline_pca4_summary.txt` | **Historical only** |
| Pre-restart `iteration_01–04_*` | **Historical only** |
| Pre-restart tuning (row-Y, alpha, layout, local-Y experiments) | **Historical only** — do not assume active |
| **T061 two-run baseline** | **Active tuning reference** |
| New sessions | `runs/<session_id>/` only |

## 1. Launch

```bash
python main.py
```

**Expected (MVP)**:

- App starts; per-session calibration begins
- Fixation overlay: **dot + progress only** — no camera preview by default (CQ-4)

## 2. Calibrate

1. Look at each calibration target until it advances.
2. Complete all targets; wait for pass/fail **after** session ends.

**Artifacts**: `runs/<session_id>/calibration_summary.txt`, `coverage.json`

## 3. Preview (read-only)

After calibration pass: gaze dot tracks keys. No key activation or text changes from gaze.

## 4. Benchmark (developer flag — CQ-3)

Benchmark is **not** in the normal UI. Validation uses:

```bash
set GAZEKEY_DEV_BENCHMARK=1
python main.py
```

After calibration pass, benchmark **auto-starts** after preview. Record key-hit, row
accuracy, median error, PASS/FAIL.

**Artifacts**: `runs/<session_id>/benchmark_summary.txt`, `benchmark_diag.json`

**Pass thresholds** (CQ-1): ≥ 10/15 keys; median ≤ 55 px; ≥ 80% row; SC-004 across 3 sessions later.

## 5. T061 — Two-run baseline (before any tuning)

**No tuning** until T061A–T061D complete. **No code/config changes** during T061A–T061C.

### T061A — Baseline run 1

1. `GAZEKEY_DEV_BENCHMARK=1`, `python main.py`
2. Full flow: calibrate → preview → benchmark
3. Note `session_id_A` and `runs/<session_id_A>/` artifacts

### T061B — Baseline run 2

1. **Same env** — restart app, new session
2. Same flow; **no** parameter or code changes
3. Note `session_id_B` and `runs/<session_id_B>/`

### T061C — Comparison + AR triage

Write `runs/t061_baseline_comparison.md` comparing both runs:

| Input | Source |
|-------|--------|
| Key-hit, row, median_err | Both `benchmark_summary.txt` |
| Failed keys, dx/dy | Failure analysis / `benchmark_diag.json` |
| Coverage | Both `coverage.json` |
| Geometry | Live UI sanity (AR-5 dots, AR-6 key centers/hitboxes) |
| Variance | Spread between run A and run B (AR-7) |
| Regional bias | Left/right/top/bottom dx/dy patterns (AR-2) |
| AR-8 | Recommend whether SC-004 evaluator needed before acceptance |

**Conditional notes** (if baselines noisy/unstable): AR-3 fixation gate, AR-4 mean/outliers.

**Defer AR-1** (feature sufficiency) unless both runs show unexplained persistent mapping bias after geometry/layout/collection review.

### T061D — Choose first lever

From T061C, record in `t061_baseline_comparison.md` which **one** lever T062 will use:

- T032 layout · T033 collection · T034 geometry · T035 PCA4 fit/smoothing/row bias

## 6. T062 — First tuning iteration

1. Implement **only** the lever from T061D (one module area).
2. Re-run full flow (`GAZEKEY_DEV_BENCHMARK=1`).
3. Document in `runs/iteration_01_<lever>.txt` vs **T061 baseline set** (T036).

## 7. Further Phase 8 cycles

Each cycle: pick **one** of T032–T035 from latest failure analysis → re-benchmark →
`runs/iteration_NN_<change>.txt` vs T061. Never combine multiple changes.

## 8. Geometry check

Automated: `tests/unit/test_layout_geometry.py`, `runs/geometry_check.txt` (synthetic).

Manual: confirm calibration dots and benchmark highlights match visible keys (AR-5, AR-6).

## 9. Repeatability (SC-004) — T063

Three sessions after tuning stabilizes; record `runs/acceptance_3session.md`.

## 10. Debug env vars

| Variable | Purpose |
|----------|---------|
| `GAZEKEY_DEV_BENCHMARK=1` | Auto benchmark after preview (CQ-3) |
| `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB=1` | Show standard camera preview during calibration (default off) |
| `GAZEKEY_VERBOSE=1` | Extra logging |
| `GAZEKEY_CALIB_MODE` | Layout override (experiments) |

**T061 with camera during calibration:**

```powershell
$env:GAZEKEY_DEV_BENCHMARK = "1"
$env:GAZEKEY_CAMERA_PREVIEW_DURING_CALIB = "1"
python main.py
```

## Success checklist

- [ ] T061A + T061B complete; `t061_baseline_comparison.md` written
- [ ] T061D lever chosen; T062 not started before T061D
- [ ] Each iteration: exactly one change, compared vs T061
- [ ] Artifacts under `runs/<session_id>/`
- [ ] SC-001–SC-004 (acceptance phase)
