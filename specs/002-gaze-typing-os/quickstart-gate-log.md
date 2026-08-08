# Post-cleanup behavior gate log (T023–T028)

**Feature**: `002-gaze-typing-os`  
**Date**: 2026-08-08  
**Branch**: `002-gaze-typing-os`  
**Scope**: quickstart.md §A only — verify cleaned repo without changing
calibration/mapping logic, thresholds, UI geometry, flags, or typing.

**Overall**: **PASS** (T023–T028)

---

## Gate results

| Task | Check | Result | Evidence |
|------|-------|--------|----------|
| T023 | `python main.py` launches | **PASS** | Smoke launch: `main` import + `VirtualKeyboard` show; prints startup banner; exits cleanly via timer. Product modules have **no** `tools.*` imports; default host uses `NullDevTools`. |
| T024 | Fullscreen calibration completes (layout unchanged) | **PASS** | `CalibrationOverlay._setup_window` still uses `primaryScreen().geometry()` (fullscreen). Live camera calib still completes on tools entries (see manual). Product finish path with `NullDevTools` completes without TypeError. |
| T025 | Existing PCA4 fit still produces mapped gaze | **PASS** | Product finish simulation assigns `mapper_type=pca4_baseline` and `predict` returns mapped screen coords; preview remains off on product path. Live: `python -m tools.preview` after calib logged `[calibration] PASSED` + usable mapper (session `14fe126cb238`, ridge_alpha=1). |
| T026 | Keyboard returns to current top-half geometry | **PASS** | `full_keyboard_size()` = full width × `0.62` height; `position_at_top()`. Measured after apply: `(0,0)` `1280×416` on available `1280×672`; lower region free below y=416. Unchanged after product calib finish. |
| T027 | Relocated developer benchmark runs independently | **PASS** | `python -m tools.evaluation` entry imports; with `GAZEKEY_DEV_BENCHMARK=1` live run started 15-key benchmark after calib (session `702386ab2ea4`). Benchmark accuracy FAIL is **expected** and **must not** gate product (confirmed: `GAZEKEY_DEV_BENCHMARK=1` does not activate benchmark on product `NullDevTools` path). |
| T028 | Record gate results | **PASS** | This file. |

---

## Commands used

### Product

```text
python main.py
```

Smoke (automated, no interactive calib):

```text
python -c "<QApplication + VirtualKeyboard show; QTimer quit>"
```

### Developer preview (independent)

```text
python -m tools.preview
```

### Developer benchmark / evaluation (independent)

```text
$env:GAZEKEY_DEV_BENCHMARK="1"
python -m tools.evaluation
```

Unset after tools runs when returning to product checks:

```text
Remove-Item Env:GAZEKEY_DEV_BENCHMARK -ErrorAction SilentlyContinue
```

---

## Automated checks

```text
python -m pytest tests/unit/test_devtools_api.py tests/unit/test_preview_readonly.py tests/unit/test_benchmark_mvp.py tests/integration/test_mvp_pipeline.py tests/unit/test_layout_geometry.py tests/test_keyboard_geometry_targets.py -q --tb=short
```

**Result**: `26 passed in 4.11s`

Additional inline gate script (product no-tools imports, overlay fullscreen,
top-half geometry, product PCA4 finish + predict, tools entrypoints,
`DEV_BENCHMARK` does not arm product path): **PASS**

---

## Manual / live camera notes

From the same feature branch / local session (webcam):

1. **`python -m tools.preview`**: fullscreen calib completed;
   `[calibration] PASSED session=14fe126cb238 … ridge_alpha=1 loocv_rms=55.6px`;
   mapped-gaze preview path operational after calib.
2. **`GAZEKEY_DEV_BENCHMARK=1` + `python -m tools.evaluation`**: calib passed
   (`702386ab2ea4`), then independent tools benchmark ran and reported
   `[benchmark] FAILED` on 001 key-hit thresholds — **mapping accuracy only**;
   does not block mapper availability or product typing (typing not started yet).

---

## Regressions found

| Issue | Status |
|-------|--------|
| Mid-cleanup product finish: `NullDevTools.on_calibration_artifacts()` rejected `ridge_alpha` (`TypeError`) | **Fixed in current tree** — `devtools_api.NullDevTools` accepts `ridge_alpha`; `tests/unit/test_devtools_api.py` + product finish simulation **PASS**. Not reproduced on current HEAD. |
| Tools benchmark key-hit FAIL under live webcam | **Not a gate failure** — developer experiment / 001 accuracy path only; must not gate calib/mapper/product. |

No product geometry, mapper-fit, or flag regressions introduced by this gate
(verification-only; no product behavior changes in T023–T028).

---

## Decision

**Continue**: post-cleanup gate **PASS**.  
**Stop before**: T029 (KeyAction / inject skeleton) and all later tasks.
