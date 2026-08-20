# Feature 004 — active mapping path inventory (T003)

**Date**: 2026-08-16  
**Scope**: Label as-built active vs unused. No deletions. Hypotheses only.

Product typing path (Feature 003 as-built):

`tracking → FeatureExtractor → PcaFeatureSmoother → Pca4BaselineMapper.predict → MapperRuntime.clamp_xy → hit_test_layout_keys → dwell`

Developer evaluation lives under `tools/evaluation/` and MUST NOT be imported by `gazekey.ui` typing enablement.

## `gazekey/calibration/` — ACTIVE on calib sessions

| Module | Role | Notes / hypotheses |
|--------|------|--------------------|
| `session.py` | Collect accepted frames; aggregate target means | Aggregation coherence is a Phase B hypothesis (T018–T019) |
| `fixation_gate.py` | Accept/reject frames during fixation | 4-D vs 2-D lock is a Phase B hypothesis (T016–T017) |
| `targets.py` | `keyboard15` key-centered 15 spatial targets | Coverage vs prediction domain is Phase D, after baseline |
| `quality.py` | `evaluate_calibration_quality`; keyboard blockers vs warnings | Warning-only gates: Phase B (T026–T027). **Do not** change policy in Phase 2 |
| `region_quality.py` | Spatial row/col region checks | Metadata vs Space/non-letters: Phase B (T023–T025) |
| `outliers.py` | Label-based `_row_column_peers` | Possibly dead/misleading: Phase B (T022) |

## `gazekey/mapping/` — ACTIVE mapper is PCA4 ridge

| Module | Role | Notes / hypotheses |
|--------|------|--------------------|
| `ridge.py` | `Pca4BaselineMapper` fit/predict; `_clip_xy` inside `predict` | Clip/clamp investigation is Phase C (T033–T034). **Do not** change `_clip_xy` in Phase 2 |
| `config.py` | `CALIBRATION_MODE=keyboard15`, alpha grid, smoother alphas | Auto-alpha is Phase E only (T040–T041) |
| `base.py` | `Mapper` protocol: `predict(features) → (x,y)` | Fit is spatial only (FR-030 / T055) |
| `row_bias.py` | `MapperWithRowBias` | **Unused on typing**: `APPLY_ROW_Y_BIAS = False` |

## `gazekey/runtime/mapper_runtime.py` — ACTIVE

| Helper | On product typing? | Notes |
|--------|--------------------|--------|
| `key_accuracy_predict_screen_xy` | **Yes** (`GazeLoopController.process_gaze_typing` → `_preview_mapped_screen_xy` → `_predict_screen_xy`) | Feature EMA + `model.predict` + gaze bias + `clamp_xy` |
| `clamp_xy` | **Yes** (after predict) | Diagnostic unclamped path is evaluation-only (T009) |
| `predict_gaze_v2` | Same clamp path as typing | Used by `map_gaze_screen_xy` |
| `map_gaze_screen_xy` | **No** (debug/preview overlay only) | Applies `GazeSmoother` **after** mapped xy |
| `complete_calibration_fit` | Calib only | Calls `evaluate_calibration_quality`; blocking policy unchanged in Phase 2 |

## `gazekey/typing/key_hit_tester.py` — ACTIVE

`hit_test_layout_keys` is the product hit-test (tight rect, then snap). Evaluation must call this same function. **Snap ≠ mapped-key success** (inside tight rect is primary).

## `gazekey/typing/gaze_smoother.py` — NOT on typing

`GazeSmoother` is constructed on `VirtualKeyboard` and used in `MapperRuntime.map_gaze_screen_xy` (debug overlay). Product typing does **not** run `GazeSmoother.filter`. Evaluation should match typing (`key_accuracy_predict_screen_xy`), not the overlay smoother.

## `tools/evaluation/` — developer measurement only

Active: `benchmark_runner.py`, `benchmark_session.py`, `benchmark_controller.py`, `run_summary.py`, `calib_finish_artifacts.py`, `session.py`, `session_paths.py`, `experiment_record.py`.

Supplementary (not a mapping input): `benchmark_diagnostics.py`, `coverage_diagnostics.py`, `failure_analysis.py`.

## Unused / confusing helpers (label only — no deletion in Phase 2)

- `map_gaze_screen_xy` vs typing predict (T050 later)
- `APPLY_ROW_Y_BIAS` wrapper when False
- Label-based outlier peers if T022 finds them dead
