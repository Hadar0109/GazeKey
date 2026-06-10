# Cleanup Inventory — Phase 10A (T042)

**Feature**: `001-calibration-mapping-mvp`  
**Date**: 2026-06-10  
**MVP entry**: `main.py` → `gazekey.ui.virtual_keyboard.VirtualKeyboard`  
**Active flow**: calibrate (calibration2) → PCA4 ridge fit → read-only preview → dev-flag benchmark (`GAZEKEY_DEV_BENCHMARK=1`)

## Classification legend

| Class | Meaning |
|-------|---------|
| **active-mvp** | Required (directly or transitively) for the active user flow above |
| **future-interaction** | Dwell / intent / selection / gaze typing — preserve, isolate from active path |
| **debug-offline** | Developer tooling; not in normal user flow |
| **legacy-replaced** | Superseded code; archive/delete candidate after plan approval |
| **docs-artifacts** | Documentation, run outputs, specs — not runtime code |
| **investigate** | Uncertain — resolved in T043 section below |

**Recommendation**: `keep` | `disconnect` | `archive` | `delete` | `refactor` | `investigate`

---

## Repository root

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `main.py` | active-mvp | App entry; launches `VirtualKeyboard` | yes | `tests/integration/test_mvp_pipeline.py` (indirect) | keep | App won't start |
| `requirements.txt` | docs-artifacts | Python dependencies | n/a | n/a | keep | Build/env break |
| `README.md` | docs-artifacts | Project overview (may drift from MVP) | no | no | keep; update in cleanup if needed | Onboarding confusion only |
| `CURRENT_PIPELINE.md` | docs-artifacts | As-built pipeline notes (pre-MVP) | no | no | keep; mark superseded by spec/plan | Planning confusion |
| `TYPING_CANDIDATE.md` | docs-artifacts | Mapper config rationale | no | no | keep | Loss of tuning history |
| `key_accuracy_debug.csv` | docs-artifacts | Legacy debug export at repo root | no | no | disconnect / delete (root clutter) | None if copies exist in `runs/` |
| `key_accuracy_compare.csv` | docs-artifacts | Legacy compare export at repo root | no | no | disconnect / delete (root clutter) | None if copies exist in `runs/` |
| `.gitignore` | docs-artifacts | Git ignore rules | n/a | n/a | keep | — |
| `runs/` | docs-artifacts | Per-session summaries, baselines, diagnostics JSON | no (output) | some tests write here | keep | Loss of benchmark history |
| `specs/` | docs-artifacts | Spec Kit source of truth | no | no | keep | — |
| `docs/` | docs-artifacts | PDF spec, status notes, images | no | no | keep | — |
| `.specify/` | docs-artifacts | Spec Kit tooling | no | no | keep | — |
| `.cursor/` | docs-artifacts | Cursor rules/skills | no | no | keep | — |

---

## `scripts/` (debug-offline)

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `scripts/analyze_pca_vs_poly12.py` | debug-offline | Offline mapper comparison analysis | no | no | keep | Loss of offline analysis |
| `scripts/analyze_correction_layers.py` | debug-offline | Correction-layer analysis | no | no | keep | — |
| `scripts/analyze_calib_artifacts.py` | debug-offline | Calibration artifact analysis | no | no | keep | — |
| `scripts/camera_*.py`, `eye_landmarker_demo.py` | debug-offline | Camera/MediaPipe demos | no | no | keep | — |

---

## `gazekey/` packages

### `gazekey/tracking/` — active-mvp

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `tracking/eye_detector.py` | active-mvp | MediaPipe landmarks → `EyeData` | yes (via features + lazy manager) | `test_calibration.py` (mock) | keep | No gaze input |
| `tracking/video_capture.py` | active-mvp | Webcam capture thread | yes (lazy) | no | keep | No camera frames |
| `tracking/tracking_manager.py` | active-mvp | Orchestrates capture + detector | yes (lazy from VK) | no | keep | Tracking won't start |

### `gazekey/features/` — active-mvp

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `features/extractor.py` | active-mvp | `EyeData` → `FrameFeatures` | yes | many mapping/calib tests | keep | No features for mapper |
| `features/feature_types.py` | active-mvp | `FrameFeatures`, `EyeData` types | yes | many | keep | — |
| `features/feature_smoother.py` | active-mvp | PCA u/v smoothing at runtime | yes | `test_feature_smoother.py` | keep | Mapping jitter |
| `features/poly_features.py` | active-mvp | Poly basis (used in ridge fit path) | yes (transitive via ridge) | `test_poly12_calibration_comparison.py` | keep | Ridge fit may break |
| `features/vertical_decouple.py` | active-mvp | Vertical residualization in fit | yes (transitive) | `test_vertical_decouple.py` | keep | Fit quality change |

### `gazekey/layout/` — active-mvp (partial)

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `layout/layout_inspector.py` | active-mvp | Key centers, rows, hitboxes from Qt widgets | yes | `test_layout_geometry.py`, `test_keyboard_geometry_targets.py`, integration | keep | Geometry/hit tests break |
| `layout/layout_csv.py` | active-mvp | Export keyboard layout CSV | yes (VK layout export) | no | keep | — |
| `layout/geometry_check.py` | debug-offline | Synthetic geometry verification helper | **no** (test-only) | `tests/unit/test_layout_geometry.py` | keep | T003 geometry test breaks |

### `gazekey/calibration/` (v1) — legacy-replaced (partial import)

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `calibration/tracking_bridge.py` | active-mvp | Qt signal bridge for eye data | yes | `test_calibration.py` | keep (or move to `tracking/`) | VK loses eye-data bridge |
| `calibration/calibration_session.py` | legacy-replaced | v1 calibration session | **yes** (overlay imports types) | `test_calibration.py` | disconnect → archive after overlay decoupled | Overlay import break until refactor |
| `calibration/gaze_mapper.py` | legacy-replaced | v1 affine/IDW gaze mapper | transitive via overlay/session | `test_calibration.py` | archive | v1 tests break |
| `calibration/affine_mapper.py` | legacy-replaced | v1 affine fit | transitive | `test_calibration.py` | archive | — |
| `calibration/gaze_features.py` | legacy-replaced | v1 ratio features | transitive | `test_calibration.py` | archive | — |
| `calibration/calibration_validation.py` | legacy-replaced | v1 validation | transitive | `test_calibration.py` | archive | — |
| `calibration/calibration_store.py` | legacy-replaced | v1 JSON persistence | **no** (not loaded CQ-2) | `test_calibration.py` | archive | v1 store test only |
| `calibration/README.md` | docs-artifacts | v1 design doc | no | no | archive with package | — |
| `calibration/__init__.py` | legacy-replaced | Re-exports v1 API | partial (`TrackingBridge` only needed) | `test_calibration.py` | refactor | — |

**Note**: MVP uses calibration2 exclusively for collection/fit; v1 remains coupled through `calibration_overlay.py` imports.

### `gazekey/calibration2/` — active-mvp

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `calibration2/session.py` | active-mvp | v2 calibration session | yes | many unit/integration tests | keep | No calibration |
| `calibration2/targets.py` | active-mvp | Target layouts (keyboard15 default; full9/wide9 behind env) | yes | `test_candidate_layouts.py`, `test_keyboard_geometry_targets.py` | keep | Layout/benchmark misalign |
| `calibration2/fixation_gate.py` | active-mvp | Fixation gating during collection | yes | `test_fixation_head_gate.py` | keep | Collection quality |
| `calibration2/quality.py` | active-mvp | Post-session quality assessment | yes | `test_calibration2_quality.py` | keep | — |
| `calibration2/region_quality.py` | active-mvp | Region LOOCV gates | yes | `test_region_quality.py` | keep | Ridge fit gates |
| `calibration2/mapper_store.py` | active-mvp | In-memory fitted mapper | yes | no | keep | No runtime mapper |
| `calibration2/calibration_csv.py` | active-mvp | Per-session CSV + session id | yes | `test_calibration_us1.py` | keep | — |
| `calibration2/geometry_diagnostics.py` | debug-offline | Print geometric diagnostics (verbose/debug) | yes (VK finish path) | no | disconnect from default path | Verbose-only loss |
| `calibration2/outliers.py` | active-mvp | Target mean outlier check | yes | `test_calibration2_outliers.py` | keep | — |

### `gazekey/mapping/` — active-mvp (with dormant variants)

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `mapping/ridge.py` | active-mvp | PCA4 ridge fit/predict; LOOCV α selection | yes | many tests | keep | Core mapper gone |
| `mapping/typing_candidate.py` | active-mvp | Frozen MVP config (α grid, row bias flag, layouts) | yes | `test_typing_candidate.py` | keep | Config drift |
| `mapping/base.py` | active-mvp | `Mapper`, `MapperPrediction` types | yes | preview tests | keep | — |
| `mapping/row_bias.py` | active-mvp | Row-Y bias layer (`APPLY_ROW_Y_BIAS=True`) | yes (active post-fit) | `test_row_y_bias_path.py` | keep | **Accuracy change** if removed |
| `mapping/local_y_correction.py` | active-mvp | Local-Y correction (currently **off**) | yes (imported; dormant) | `test_local_y_correction.py` | keep dormant | Phase 8 may enable |
| `mapping/idw_local.py` | legacy-replaced | IDW mapper variant | via `mapping.__init__` only | mapper selection tests | disconnect / archive dead paths | Compare tests |
| `mapping/idw_ratio.py` | legacy-replaced | IDW ratio mapper | via `__init__` | compare tests | disconnect / archive | — |
| `mapping/row_aware.py` | legacy-replaced | Row-aware mapper variant | via `__init__` | ridge selection tests | disconnect / archive | — |
| `mapping/__init__.py` | active-mvp | Public mapping API; exports dormant mappers | yes | many | refactor (export PCA4 only) | Import breaks in tests |

### `gazekey/evaluation/` — active-mvp + debug

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `evaluation/benchmark_runner.py` | active-mvp | 15-key benchmark scoring | yes | `test_benchmark_mvp.py`, integration | keep | No MVP benchmark |
| `evaluation/run_summary.py` | active-mvp | Console + file summaries | yes | `test_evaluation_summary.py` | keep | — |
| `evaluation/failure_analysis.py` | active-mvp | Per-key miss formatting | yes | `test_evaluation_summary.py` | keep | — |
| `evaluation/benchmark_diagnostics.py` | debug-offline | JSON benchmark diagnostics | yes (VK dev path) | `test_benchmark_diagnostics.py` | disconnect from default import chain | Dev diagnostics only |
| `evaluation/coverage_diagnostics.py` | debug-offline | Calibration coverage JSON | yes (VK post-calib) | `test_coverage_diagnostics.py` | disconnect from default import chain | Dev diagnostics only |

### `gazekey/ui/` — active-mvp (refactor target)

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `ui/virtual_keyboard.py` | active-mvp | **Mixed orchestrator** (~2960 lines) | yes | integration, preview, benchmark tests | **refactor** (T046–T051) | Entire app |
| `ui/calibration_controller.py` | active-mvp | Calibration v2 lifecycle boundary | yes | `test_calibration_us1.py` | keep | — |
| `ui/calibration_overlay.py` | active-mvp | Fixation overlay (v2 + legacy v1 types) | yes | `test_calibration_us1.py` | refactor (drop v1 coupling) | Overlay break if rushed |
| `ui/gaze_preview.py` | active-mvp | Read-only gaze dot | yes | `test_preview_readonly.py` | keep | — |
| `ui/camera_preview_window.py` | active-mvp | Floating camera preview (post-calib) | yes | integration | keep | CQ-4 preview |
| `ui/calibration_geometry_overlay.py` | debug-offline | Post-fit geometry overlay (`GAZEKEY_CALIB_GEOM_DEBUG`) | yes (env-gated) | no | keep behind env flag | Debug-only |

### `gazekey/intent/` — future-interaction

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `intent/scoring.py` | future-interaction | Gaussian key intent scoring | yes (imported; MVP gaze loop disabled) | **none** | move-aside / isolate | Future typing path |
| `intent/__init__.py` | future-interaction | Package export | yes | none | move-aside | — |

### `gazekey/selection/` — future-interaction

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `selection/policy.py` | future-interaction | Hysteresis + dwell selection | yes (imported; disabled in MVP loop) | **none** | move-aside / isolate | Future typing path |
| `selection/__init__.py` | future-interaction | Package export | yes | none | move-aside | — |

### `gazekey/typing/` — mixed (active + future)

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `typing/key_hit_tester.py` | active-mvp | Gaze point vs key hitbox | yes (benchmark + layout) | `test_keyboard_accuracy.py` | keep | Benchmark broken |
| `typing/key_semantics.py` | active-mvp | Key semantic rows | yes (transitive) | geometry tests | keep | Row scoring break |
| `typing/gaze_ui_mapper.py` | active-mvp | Letter region rects | yes | layout/integration tests | keep | Region clipping |
| `typing/text_buffer.py` | active-mvp | Text buffer (mouse typing active) | yes | `test_preview_readonly.py` | keep | Mouse typing |
| `typing/gaze_typing_controller.py` | future-interaction | Dwell gaze typing | yes (dormant path in VK) | `test_gaze_typing.py` | move-aside | Future interaction |
| `typing/dwell_selector.py` | future-interaction | Dwell timing | yes (via selection) | `test_gaze_typing.py` | move-aside | — |
| `typing/gaze_smoother.py` | future-interaction | Gaze position smoothing for typing | yes (preview may share) | no | keep; clarify ownership in refactor | Preview smoothing |
| `typing/__init__.py` | mixed | Re-exports typing modules | yes | several | refactor exports | — |

### `gazekey/debug/` — debug-offline (imported by VK)

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `debug/keyboard_accuracy.py` | debug-offline | Original 15-key eval (source for evaluation/) | yes (VK dev benchmark UI) | `test_keyboard_accuracy.py` | keep; disconnect from active chain after T047 | Dev benchmark UI |
| `debug/keyboard_accuracy_mapper_diag.py` | debug-offline | Multi-mapper diagnostics | yes (env-gated) | `test_keyboard_accuracy_mapper_diag.py` | disconnect | Experimental compare |
| `debug/keyboard_accuracy_compare.py` | debug-offline | Mapper compare CSV | yes (env-gated) | `test_keyboard_accuracy_compare_consistency.py` | disconnect | — |
| `debug/runtime_key_confidence_logger.py` | debug-offline | Runtime CSV logging | yes (env-gated) | no | disconnect | Debug logs only |

### Other `gazekey/`

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `gazekey/mvp_log.py` | active-mvp | Quiet default logging | yes | `test_mvp_logging.py` | keep | Log behavior |
| `gazekey/__init__.py` | active-mvp | Package marker | partial | no | keep | — |

---

## `tests/`

| path | class | purpose | mvp_imported | tests_depend | recommendation | removal_risk |
|------|-------|---------|--------------|--------------|----------------|--------------|
| `tests/unit/` | active-mvp | MVP contract unit tests | n/a | n/a | keep | Regression coverage |
| `tests/integration/test_mvp_pipeline.py` | active-mvp | End-to-end MVP flow test | n/a | n/a | keep | No automated gate |
| `tests/test_calibration.py` | legacy-replaced | v1 calibration tests | n/a | v1 package | keep until v1 archived; then archive | — |
| `tests/test_*` (mapper compare, poly12, ridge selection) | debug-offline | Historical mapper variant tests | n/a | mapping variants | keep for dormant code; archive with variants | — |

---

## T043 — Resolved investigations

Items initially marked uncertain; findings below. **No remaining `investigate` items block Phase 10B.**

| path | finding | resolved class | recommendation |
|------|---------|----------------|----------------|
| `calibration/calibration_store.py` | Not imported by MVP path; CQ-2 forbids load on startup | legacy-replaced | archive with v1 package |
| `layout/geometry_check.py` | Test/offline helper only; writes `runs/geometry_check.txt` | debug-offline | keep |
| `calibration_overlay.py` v1 imports | Types for dual-path overlay; runtime uses v2 only via `CalibrationController` | legacy-replaced (coupling) | refactor overlay to v2-only types |
| `mapping/idw_*`, `row_aware.py` | Exported in `mapping.__init__`; blocked at runtime (T038) | legacy-replaced | disconnect exports; archive after tests updated |
| `mapping/local_y_correction.py` | Imported by ridge; `APPLY_LOCAL_Y_CORRECTION=False` | active-mvp (dormant) | keep |
| `evaluation/benchmark_diagnostics.py`, `coverage_diagnostics.py` | Written on dev runs; not user-facing | debug-offline | disconnect from VK default imports (T047) |
| `root *.csv` | Stale exports duplicated under `runs/` | docs-artifacts | delete root copies in approved cleanup |
| `CURRENT_PIPELINE.md` vs spec | Pre-MVP doc; partially outdated | docs-artifacts | keep; add pointer to spec/plan |
| `intent/`, `selection/` no tests | Imported but gaze loop disabled (T018) | future-interaction | move-aside (T052); add tests when interaction resumes |
| `keyboard_full9`, `keyboard_wide9` in `targets.py` | Behind `GAZEKEY_CALIB_MODE`; not default | active-mvp (gated) | keep per plan |

---

## Summary counts (major runtime code)

| class | count (packages/modules) | action in Phase 10 |
|-------|--------------------------|-------------------|
| active-mvp | ~45 modules | keep; refactor VK split |
| future-interaction | 6 modules | isolate (T052), do not delete |
| debug-offline | ~15 modules | keep; disconnect from active import chain |
| legacy-replaced | ~12 modules | archive after overlay/mapping decouple |
| docs-artifacts | specs, runs, scripts, md | keep |

**Next step (T044)**: Produce `cleanup-plan.md` with one task per approved archive/delete/disconnect.

---

## Test suite notes (Phase 10C)

| Test file | T048 exclusion | Status |
|-----------|----------------|--------|
| `tests/test_typing_candidate.py` | Excluded during T048 full-suite run (`pytest tests/ --ignore=tests/test_typing_candidate.py`) | **Not a known failure** — 3 tests pass (~1.3s). Exclusion was precautionary (lives under `tests/` root, exercises frozen `typing_candidate` / `fit_calibration_mapper` identity). Include in full suite from T049 onward.
