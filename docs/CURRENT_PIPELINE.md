## CURRENT_PIPELINE

Authoritative description of the **active MVP runtime** after the post-cleanup refactor (2026-06).

### Entry point

```
main.py
  → QApplication
  → VirtualKeyboard.show()
  → VirtualKeyboard.on_app_started()
       → schedule layout inspect (in memory)
       → start calibration if no usable mapper
```

### High-level diagram

```
Camera → EyeData → FeatureExtractor
       → [calibrating] CalibrationSession + CalibrationOverlay
       → [after fit]  MapperRuntime (PCA4 ridge + row bias)
       → GazeLoop → read-only GazePreview (dot)
       → [dev] BenchmarkEvalSession (15-key scoring)
```

Mouse clicks on keys still route through the normal Qt button handlers and `TextBufferController`. Gaze **does not** activate keys on the MVP path.

---

### Active packages

#### Always on

| Area | Files | Role |
|------|-------|------|
| UI shell | `gazekey/ui/virtual_keyboard.py` | Thin orchestrator; wires controllers |
| Layout | `gazekey/ui/keyboard_layout.py`, `gazekey/layout/layout_inspector.py` | Keyboard chrome + key geometry snapshot |
| Tracking | `gazekey/tracking/tracking_manager.py`, `eye_detector.py` | Background capture → `EyeData` |
| Bridge | `gazekey/tracking/tracking_bridge.py` | Worker thread → Qt main thread |
| Features | `gazekey/features/extractor.py`, `feature_smoother.py` | `FrameFeatures` + runtime PCA EMA |
| Runtime | `gazekey/runtime/tracking_controller.py`, `gaze_loop.py`, `mapper_runtime.py` | Lifecycle, per-frame dispatch, fit/predict |

#### Calibration (every launch)

| File | Role |
|------|------|
| `gazekey/ui/calibration_controller.py` | Start session, overlay, `new_session_id()` |
| `gazekey/ui/calibration_overlay.py` | Fullscreen fixation dots |
| `gazekey/calibration/session.py` | `CalibrationSession` — gate, per-target means |
| `gazekey/calibration/fixation_gate.py` | Fixation stability |
| `gazekey/calibration/targets.py` | `keyboard_geometry_targets` (default `keyboard15`) |
| `gazekey/calibration/outliers.py` | Peer outlier checks |
| `gazekey/ui/calibration_finish.py` | Fit orchestration, summaries, debug exports |

#### Mapping (PCA4 only)

| File | Role |
|------|------|
| `gazekey/mapping/config.py` | Frozen MVP constants (α grid, gates, smoothers) |
| `gazekey/mapping/ridge.py` | `fit_calibration_mapper` → `Pca4BaselineMapper` |
| `gazekey/mapping/row_bias.py` | Optional post-fit row-Y bias (`APPLY_ROW_Y_BIAS`) |

`fit_calibration_mapper` fits **only** `pca4_baseline`. Poly12, decoupled, local-Y, and multi-candidate ranking are **not** on the active path (variants live under `archive/`).

#### Quality gates

| File | Role |
|------|------|
| `gazekey/runtime/mapper_runtime.py` | Calls fit + `evaluate_calibration_quality` |
| `gazekey/calibration/quality.py` | Usability decision (preview/benchmark allowed?) |
| `gazekey/calibration/region_quality.py` | Per-target region LOOCV checks |

On failure: mapper cleared, RECALIBRATE prompt; debug artifacts still written when possible.

#### Preview (read-only)

| File | Role |
|------|------|
| `gazekey/ui/gaze_preview.py` | Gaze dot overlay |
| `gazekey/runtime/gaze_loop.py` | Routes eye data: calibrate / preview / benchmark |

Preview uses the same predict path as the dev benchmark (`MapperRuntime.predict_gaze_v2` → `GazeSmoother`).

#### Dev benchmark

| File | Role |
|------|------|
| `gazekey/ui/benchmark_controller.py` | UI for 15-key timed benchmark |
| `gazekey/evaluation/benchmark_session.py` | Per-key settle/collect |
| `gazekey/evaluation/benchmark_runner.py` | Scoring + pass thresholds |
| `gazekey/evaluation/run_summary.py` | Console + file summaries |
| `gazekey/evaluation/benchmark_diagnostics.py` | JSON diagnostics |

Triggered when `GAZEKEY_DEV_BENCHMARK=1` after successful calibration.

#### Debug / inspection (not on default import path)

| File | Role |
|------|------|
| `gazekey/debug/layout_csv.py` | `keyboard_layout.csv` export |
| `gazekey/debug/mapper_store.py` | `calibration_v2.json` snapshot |
| `gazekey/debug/calibration_geometry_diagnostics.py` | Per-target geometric printout |
| `gazekey/debug/calibration_geometry_overlay.py` | Visual overlay (`GAZEKEY_CALIB_GEOM_DEBUG`) |

---

### Mapper selection

- **When**: `CalibrationFinishController.on_finished` → `MapperRuntime.complete_calibration_fit`
- **What**: `pca4_baseline` ridge + optional `MapperWithRowBias`
- **Load on startup**: **disabled** — mapper snapshots are write-only for inspection
- **Runtime handle**: `MapperRuntime.model` (exposed on `VirtualKeyboard` as `_gaze_mapper`)

Console after successful calibration (example):

```
[calibration] PASS session=… layout=keyboard15 targets=15/15 …
[runtime] typing_candidate=pca4_baseline_v1 mapper_mode=keyboard15 active_mapper=pca4_baseline …
[preview] Gaze dot tracks mapped position; keys are not activated (MVP).
```

---

### Calibration modes

| Mode | How | Points |
|------|-----|--------|
| `keyboard15` | Default (`mapping/config.py`) | 15 on real key centers + row structure |
| Other layouts | `GAZEKEY_CALIB_MODE` or `calibration_controller` | See `gazekey/calibration/targets.py` |

Clip bounds for predict: letter-keys region (`_calib_clip_rect`) in keyboard mode.

---

### Step-by-step runtime flow

#### Tracking → main thread

1. `TrackingManager` captures frame → `EyeDetector.detect` → `EyeData`
2. `TrackingBridge.forward` → `GazeLoopController.process_eye_data`

#### During calibration

3. `_start_calibration_if_needed` → `CalibrationController.start` → assigns `session_id`, binds `runs/<session_id>/`
4. `CalibrationOverlay` feeds features to `CalibrationSession.process`
5. Per target: fixation lock → accepted samples → advance
6. `_on_calibration_finished` → `MapperRuntime.complete_calibration_fit`
7. Quality gates → summaries + debug exports → preview mode on success

#### After calibration (preview)

8. `GazeLoop` → `FeatureExtractor` → `PcaFeatureSmoother` → `MapperRuntime.predict_gaze_v2`
9. `GazeSmoother` on screen coords → `GazePreviewController` draws dot
10. No intent scoring, selection policy, or dwell activation on this path

#### Dev benchmark (optional)

11. `BenchmarkController` highlights keys sequentially
12. Hit test via `gazekey/typing/key_hit_tester.py` + `evaluation/benchmark_runner.py`
13. Write `benchmark_summary.txt` + `benchmark_diag.json` under same session folder

---

### Session artifacts (`runs/<session_id>/`)

| File | When |
|------|------|
| `keyboard_layout.csv` | After session id is bound (calibration start + exports) |
| `calibration_v2.json` | After ridge fit (inspection snapshot) |
| `calibration_summary.txt` | Calibration finish |
| `coverage.json` | Calibration finish |
| `calibration_debug.csv` | Calibration finish (fit succeeded) |
| `calibration_ratio_space.csv` | Calibration finish |
| `benchmark_summary.txt` | Dev benchmark finish |
| `benchmark_diag.json` | Dev benchmark finish |

Path helpers: `gazekey/evaluation/session_paths.py`.

Nothing new is written to the repository root.

---

### Environment variables

| Variable | Effect |
|----------|--------|
| `GAZEKEY_VERBOSE=1` | Verbose calibration/runtime logs |
| `GAZEKEY_DEV_BENCHMARK=1` | Auto 15-key benchmark after calibration |
| `GAZEKEY_CALIB_MODE` | Override calibration target layout |
| `GAZEKEY_CALIB_DEBUG=1` | Verbose overlay + geometry overlay |
| `GAZEKEY_CALIB_GEOM_DEBUG=1` | Post-fit geometry overlay |
| `GAZEKEY_GAZE_DEBUG=1` | Extra gaze predict logs |
| `GAZEKEY_GAZE_DEBUG_PRED=1` | Per-frame mapper predict logs |
| `GAZEKEY_GAZE_DEBUG_SELECTION=1` | Selection debug (dormant typing path only) |
| `GAZEKEY_SELECTION_DEBUG=1` | Disable selection hysteresis (dormant path) |

---

### Not on the active path

| Was / exists | Status |
|--------------|--------|
| `gazekey/calibration2/` | Renamed → `gazekey/calibration/` |
| `calibration_csv.py`, per-frame sample CSVs | Removed |
| `mapping/local_y_correction.py`, poly12, decoupled | Archived / not fitted |
| `gazekey/future/` intent + dwell typing | Dormant; preview is read-only |
| `gazekey/debug/runtime_key_confidence_logger.py` | Deleted |
| `archive/calibration_v1/` | Legacy reference only |

---

### Quick checklist

- Calibrate every launch: **`CalibrationSession`** + **`keyboard15`**
- Fit: **`pca4_baseline`** + **row Y bias** (no local-Y on active path)
- Config: **`gazekey/mapping/config.py`** + **`TYPING_CANDIDATE.md`**
- Persist: **`runs/<session_id>/calibration_v2.json`** via **`debug/mapper_store.py`**
- Runtime: **smoothed PCA features** → **ridge mapper** → **read-only preview dot**
- Typing: **mouse click**; gaze dwell typing **off** until `gazekey/future/` is reconnected
