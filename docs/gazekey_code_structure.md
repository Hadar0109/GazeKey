# GazeKey Code Structure (`gazekey/`)

**Last updated:** 2026-06-10 (post-cleanup MVP)

Authoritative runtime narrative: **`CURRENT_PIPELINE.md`**. Frozen mapper config: **`TYPING_CANDIDATE.md`** / **`mapping/config.py`**.

## MVP active path

```text
main.py → VirtualKeyboard (ui/)
  tracking/ → features/ → calibration/ (session collection)
  → mapping/ (PCA4 ridge fit) → runtime/ (fit, predict, gaze loop)
  → ui/ (preview dot, benchmark UI)
  → evaluation/ (scores, summaries, session artifact paths)
  → debug/ (optional inspection exports)
```

Preview is **read-only** — gaze does not activate keys. Mouse clicks still type via `typing/text_buffer.py`. Dwell typing, intent scoring, and selection policy live under **`future/`** (dormant).

Session artifacts are written only under **`runs/<session_id>/`** (see `evaluation/session_paths.py`).

---

## Root (`gazekey/`)

| File | Role |
|------|------|
| `__init__.py` | Package marker (`__version__`). |
| `mvp_log.py` | Quiet-by-default logging (`GAZEKEY_VERBOSE=1`). |

---

## `gazekey/tracking/`

Webcam + MediaPipe eye detection (background thread → Qt main thread).

| File | Role |
|------|------|
| `tracking_bridge.py` | `TrackingBridge` — Qt signal from worker thread. |
| `video_capture.py` | Webcam frame capture thread. |
| `eye_detector.py` | `EyeDetector`, `EyeData` — MediaPipe landmarks. |
| `tracking_manager.py` | Orchestrates capture + detection. |

---

## `gazekey/features/`

| File | Role |
|------|------|
| `feature_types.py` | `FrameFeatures` dataclass. |
| `extractor.py` | `FeatureExtractor` — `EyeData` → `FrameFeatures`. |
| `feature_smoother.py` | `PcaFeatureSmoother` — runtime PCA EMA (`FEATURE_SMOOTHER_ALPHA`). |

Poly features and vertical decoupling were removed from the active path (variants in `archive/mapping_variants/`).

---

## `gazekey/calibration/`

Active calibration (renamed from `calibration2/`). Keyboard-local targets, fixation gating, quality gates.

| File | Role |
|------|------|
| `session.py` | `CalibrationSession`, `CalibrationResult` — per-target sample collection. |
| `targets.py` | Target layouts (`keyboard15` default; override via `GAZEKEY_CALIB_MODE`). |
| `fixation_gate.py` | Fixation stability gating. |
| `quality.py` | Post-fit quality assessment and usability gates. |
| `region_quality.py` | Per-target region LOOCV checks. |
| `outliers.py` | Peer outlier detection among targets. |

**Not on MVP path** (legacy files still in tree, not imported by `calibration/__init__.py`): `affine_mapper.py`, `gaze_mapper.py`, `calibration_store.py`, `calibration_session.py`, etc. Use `archive/calibration_v1/` for v1 reference.

Session IDs: `evaluation/session.new_session_id()`. Console + file summaries: `evaluation/run_summary.py` → `runs/<session_id>/calibration_summary.txt`.

---

## `gazekey/mapping/`

**Active:** PCA4 ridge only.

| File | Role |
|------|------|
| `config.py` | Frozen MVP config (α grid, gates, smoothers, `keyboard15`). |
| `base.py` | `Mapper`, `MapperPrediction`, `MapperFitResult`. |
| `ridge.py` | `Pca4BaselineMapper`, `fit_calibration_mapper`, LOOCV α selection. |
| `row_bias.py` | Post-fit row-Y bias wrapper (`APPLY_ROW_Y_BIAS=True`). |

**Present but inactive** (not called by `fit_calibration_mapper`): `local_y_correction.py`, `row_aware.py`, `idw_ratio.py`, `idw_local.py`. Prefer `archive/mapping_variants/` for experiments.

---

## `gazekey/runtime/`

Non-widget services (moved out of `ui/` during cleanup).

| File | Role |
|------|------|
| `tracking_controller.py` | Camera/tracking lifecycle. |
| `gaze_loop.py` | Eye-data dispatch: calibration vs preview vs benchmark. |
| `mapper_runtime.py` | Post-calibration fit, quality gates, predict/clamp. |

---

## `gazekey/layout/`

| File | Role |
|------|------|
| `layout_inspector.py` | Qt widget → `KeyGeometryRow` list (`inspect_keyboard_layout`). |

Layout CSV export moved to **`debug/layout_csv.py`**.

---

## `gazekey/typing/`

| File | Role |
|------|------|
| `key_hit_tester.py` | Gaze-point hit testing (dev benchmark). |
| `key_semantics.py` | Button label → action. |
| `gaze_ui_mapper.py` | Screen bounds → keyboard region rects. |
| `text_buffer.py` | Text field updates (mouse typing). |
| `gaze_smoother.py` | Screen-coordinate EMA for preview (`GAZE_SMOOTHER_ALPHA`). |
| `dwell_selector.py` | Dwell timing (dormant — used via `future/`). |
| `gaze_typing_controller.py` | Dwell activation UI (dormant). |

---

## `gazekey/evaluation/`

Benchmark scoring, run summaries, and session-scoped artifact paths.

| File | Role |
|------|------|
| `session.py` | `new_session_id()` for calibration/benchmark runs. |
| `session_paths.py` | `runs/<session_id>/` path helpers and filename constants. |
| `benchmark_runner.py` | 15-key scoring, metrics, pass/fail thresholds. |
| `benchmark_session.py` | `BenchmarkEvalSession` — timed settle/collect per key. |
| `run_summary.py` | Console line + `calibration_summary.txt` / `benchmark_summary.txt`. |
| `failure_analysis.py` | Per-key miss explanations for failed benchmarks. |
| `benchmark_diagnostics.py` | `benchmark_diag.json` (dev). |
| `coverage_diagnostics.py` | `coverage.json` after calibration (dev). |

### Typical `runs/<session_id>/` contents

| File | Writer |
|------|--------|
| `calibration_summary.txt` | `run_summary.py` |
| `calibration_v2.json` | `debug/mapper_store.py` |
| `keyboard_layout.csv` | `debug/layout_csv.py` |
| `coverage.json` | `coverage_diagnostics.py` |
| `calibration_debug.csv` | `ui/calibration_finish.py` |
| `calibration_ratio_space.csv` | `ui/calibration_finish.py` |
| `benchmark_summary.txt` | `run_summary.py` |
| `benchmark_diag.json` | `benchmark_diagnostics.py` |

Benchmark run ids (`<calib_id>-bench<ts>`) share the calibration session folder via `folder_session_id()`.

---

## `gazekey/ui/`

| File | Role |
|------|------|
| `virtual_keyboard.py` | Thin orchestrator — wires controllers. |
| `keyboard_layout.py` | Key grid, chrome, responsive geometry, layout export trigger. |
| `calibration_controller.py` | Start calibration session + overlay. |
| `calibration_overlay.py` | Fullscreen fixation UI. |
| `calibration_finish.py` | Post-session fit, summaries, debug exports. |
| `gaze_preview.py` | Read-only gaze dot overlay. |
| `benchmark_controller.py` | 15-key dev benchmark UI (`GAZEKEY_DEV_BENCHMARK=1`). |
| `camera_preview_window.py` | Floating webcam PiP. |
| `env_flags.py` | `GAZEKEY_*` environment flags. |

---

## `gazekey/debug/`

Diagnostics and inspection exports — not required for the default MVP import path.

| File | Role |
|------|------|
| `layout_csv.py` | `KeyboardLayoutCsvExporter` → `keyboard_layout.csv` in session folder. |
| `mapper_store.py` | `save_calibration_mapper` → `calibration_v2.json` (inspection only). |
| `calibration_geometry_diagnostics.py` | Per-target geometric diagnostics after fit. |
| `layout_geometry_check.py` | Inspector vs hit-tester geometry verification (tests). |
| `calibration_geometry_overlay.py` | Post-fit overlay (`GAZEKEY_CALIB_GEOM_DEBUG`). |

**Legacy / unused by MVP** (candidates for deletion): `keyboard_accuracy.py`, `keyboard_accuracy_compare.py`, `keyboard_accuracy_mapper_diag.py`, `runtime_key_confidence_logger.py`.

---

## `gazekey/future/` (dormant)

Re-exports for when gaze interaction is re-enabled. **Not used** by the MVP preview loop.

| File | Re-exports from |
|------|-----------------|
| `intent.py` | `gazekey.intent.scoring` — `score_keys` |
| `selection.py` | `gazekey.selection.policy` — `SelectionPolicy` |
| `typing.py` | `gazekey.typing` — `DwellSelector`, `GazeTypingController` |

Source modules `gazekey/intent/` and `gazekey/selection/` remain in the tree for this re-export layer.

---

## `archive/`

| Path | Role |
|------|------|
| `archive/calibration_v1/` | Legacy v1 calibration, affine/interpolation mappers. |
| `archive/mapping_variants/` | Poly12, local-Y, and other dormant mapper experiments. |
| `archive/tests/` | Offline comparisons against archived artifacts. |

---

## Cleanup reference (was → now)

| Was | Now |
|-----|-----|
| `gazekey/calibration2/` | `gazekey/calibration/` |
| `calibration2/calibration_csv.py` | Removed — no per-frame sample CSVs |
| `calibration2/mapper_store.py` (repo root JSON) | `debug/mapper_store.py` → `runs/<session_id>/calibration_v2.json` |
| `layout/layout_csv.py` (repo root CSV) | `debug/layout_csv.py` → `runs/<session_id>/keyboard_layout.csv` |
| `mapping/typing_candidate.py` | `mapping/config.py` |
| `mapping/local_y_correction.py` (active) | Archived; row bias only on MVP path |
| `features/poly_features.py`, `vertical_decouple.py` | Removed from active imports |
| `ui/mapper_runtime.py`, `gaze_loop.py`, `tracking_controller.py` | `gazekey/runtime/` |
| `debug/keyboard_accuracy*.py` | Replaced by `evaluation/benchmark_*` (legacy files may remain) |
| Loose files under repo root / `runs/*.txt` | `runs/<session_id>/…` via `session_paths.py` |
