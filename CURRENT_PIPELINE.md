## CURRENT_PIPELINE (exact runtime flow as of now)

This file documents the **actual** execution flow in the repo today (calibration + runtime typing), based on the current entrypoint and code paths.

### Entry point (what runs when you start the app)

- **Entrypoint**: `main.py`
  - Creates a `QApplication`
  - Instantiates `gazekey/ui/virtual_keyboard.py::VirtualKeyboard`
  - Calls `keyboard.show()` then `keyboard.on_app_started()`

### Simple diagram

```
Camera -> EyeData -> FeatureExtractor -> PcaFeatureSmoother (runtime)
       -> CalibrationV2Session (during calib)
       -> fit_calibration_mapper (LOOCV + region gates + row/local Y correction)
       -> _gaze_mapper_v2 -> Preview / Intent scoring -> SelectionPolicy -> Typing
```

### 1) Which files are actually active (calibration + runtime)

#### Always active in the main app

- **UI orchestrator**: `gazekey/ui/virtual_keyboard.py`
  - Owns tracking lifecycle, calibration lifecycle, mapper fit/load, preview mode, typing, runtime logging.
- **Calibration UI**: `gazekey/ui/calibration_overlay.py`
  - Fullscreen dot overlay; v2 path delegates gating/advancement to `CalibrationV2Session`.
- **Tracking thread**: `gazekey/tracking/tracking_manager.py`
  - Background capture loop → `EyeDetector.detect(...)` → `EyeData`.
- **Eye landmark detector**: `gazekey/tracking/eye_detector.py`
  - MediaPipe FaceLandmarker → iris centers, eye contours, blink.
- **Thread boundary bridge**: `gazekey/calibration/tracking_bridge.py`
  - `TrackingBridge.forward(eye_data)` → Qt signal → main thread.
- **Feature extraction**: `gazekey/features/extractor.py`
  - `EyeData` → `FrameFeatures` (ratio `avg_h/avg_v` + PCA eye-local `pca_uL/vL/uR/vR`).
- **Runtime feature smoothing**: `gazekey/features/feature_smoother.py`
  - `PcaFeatureSmoother` applied in `_process_gaze_typing` before mapper predict.
- **Layout geometry**: `gazekey/layout/layout_inspector.py`
  - `inspect_keyboard_layout()` snapshots key centers/rows for calibration targets and intent scoring.

#### Active during calibration (default path)

- **Calibration v2 session**: `gazekey/calibration2/session.py`
  - `CalibrationV2Session.process(features, dt_ms)` — fixation gate, per-target means, CSV samples.
- **Fixation gating**: `gazekey/calibration2/fixation_gate.py`
- **Calibration targets**: `gazekey/calibration2/targets.py`
  - **Default (keyboard)**: `keyboard_geometry_targets(..., mode="keyboard15")` in `_start_calibration()`.
    - 15 points: 9 letter-key centers (3 rows × left/center/right) + 2 row-gap points + 4 in-row quarter anchors.
    - Training coordinates are **real key centers** (`key_id` set); `grid_row` / `grid_col` for region gates.
  - **Optional**: `GAZEKEY_CALIB_FULLSCREEN=1` → 9-point fullscreen grid (`fullscreen9`).
  - **Legacy grids** (still in code, not default): `default9`, `precision13` via `keyboard_local_targets()`.
- **Calibration CSV**: `gazekey/calibration2/calibration_csv.py` → `calibration_samples.csv`, `calibration_summary.csv`.
- **Outliers / quality helpers**: `gazekey/calibration2/outliers.py`, `quality.py`, `region_quality.py`.

#### Active at calibration finish (fit + gates + persist)

- **Mapper fit + LOOCV selection**: `gazekey/mapping/ridge.py::fit_calibration_mapper()`
  - Candidates: `pca4_baseline`, `pca4_decoupled_split`, `poly12_ridge`, `poly12_ridge_split` (+ decoupled Y variant).
  - Auto alpha grid; LOOCV refit per fold; **region gates** primary for keyboard modes.
  - Post-fit wrappers (keyboard mode):
    1. **Row Y bias** — `gazekey/mapping/row_bias.py` (3 global row offsets).
    2. **Local Y correction** — `gazekey/mapping/local_y_correction.py` (X-interpolated residual; fixes u–v row tilt).
  - **u–v coupling**: if `|corr(v_mean, u_mean)| >= 0.55`, prefer poly12 candidates in ranking.
- **Vertical decoupling (fit-time)**: `gazekey/features/vertical_decouple.py` — residualize v on `[1,uL,uR]` for decoupled mappers.
- **Polynomial features**: `gazekey/features/poly_features.py` — 12D poly features for poly12 mappers.
- **Quality evaluation**: `gazekey/calibration2/quality.py::evaluate_calibration_quality()` — pixel + monotonicity + LOOCV gates before typing enabled.
- **Geometric diagnostics**: `gazekey/calibration2/geometry_diagnostics.py::print_geometric_diagnostics()` — per-target row/col, nearest key, dx/dy (train + LOOCV).
- **Geometry overlay (debug)**: `gazekey/ui/calibration_geometry_overlay.py` — green/blue/orange points + error lines when `GAZEKEY_CALIB_GEOM_DEBUG=1` or `GAZEKEY_CALIB_DEBUG=1`.
- **Persistence**: `gazekey/calibration2/mapper_store.py` → `calibration_v2.json` (version 7; includes row bias + local Y correction).

#### Active during runtime typing/preview

- **Mapper predict**: `VirtualKeyboard._process_gaze_typing()`
  - `PcaFeatureSmoother.smooth(features)` → `_gaze_mapper_v2.predict(features)` → `GazeSmoother` on screen coords.
- **Intent scoring**: `gazekey/intent/scoring.py::score_keys()`
  - Anisotropic Gaussian (wider vertical sigma), row stickiness, cross-row penalty when a key is focused.
- **Selection policy**: `gazekey/selection/policy.py::SelectionPolicy`
  - Hysteresis + dwell; **stronger margin/time to switch across rows** (default on; `GAZEKEY_SELECTION_DEBUG=1` disables hysteresis).
- **Typing controller**: `gazekey/typing/gaze_typing_controller.py` — dwell UI + activation.
- **Runtime debug CSV**: `gazekey/debug/runtime_key_confidence_logger.py` → `runtime_key_confidence.csv`.

### 2) Which mapper is selected and where

#### Where selection happens

- **Fit**: `VirtualKeyboard._on_calibration_finished()` → `fit_calibration_mapper(...)` in `gazekey/mapping/ridge.py`.
- **Load on startup**: disabled — `calibration_v2.json` is write-only (inspection); calibrate every launch.

#### What is fitted

`fit_calibration_mapper` fits **only** the frozen typing candidate (`pca4_baseline`; see `TYPING_CANDIDATE.md` and `gazekey/mapping/typing_candidate.py`). Multi-candidate LOOCV ranking (poly12, decoupled, etc.) is disabled on the active path.

Then attaches **row Y bias** and **local X-interpolated Y correction** on the fitted model.

Typical metrics on passing keyboard15 runs: LOOCV RMS ~45–67 px, corr(screen_y, avg_v) ~0.63–0.82.

#### What is NOT used in the default v2 path

- `gazekey/mapping/row_aware.py::RowAwareMapper` — present but not selected by `fit_calibration_mapper` today.
- `gazekey/mapping/idw_ratio.py`, `idw_local.py` — not wired in `VirtualKeyboard`.

#### Runtime storage

- `VirtualKeyboard._gaze_mapper_v2` — active model (may be wrapped: `MapperWithLocalYCorrection` → `MapperWithRowBias` → core ridge).
- `VirtualKeyboard._calib2_mode` / `_mapper_mode` — e.g. `keyboard15`.
- `VirtualKeyboard._active_mapper` — `mapper_type` string from the fitted core (e.g. `pca4_baseline`).

#### Console line after calibration

```
[runtime] typing_candidate=pca4_baseline_v1 mapper_mode=keyboard15 active_mapper=pca4_baseline ...
[typing] Look at keys and dwell to type. Click Preview to show gaze dot without activation.
```

- **mapper_mode**: calibration target set used (`keyboard15`, `fullscreen9`, etc.).
- **active_mapper** / **mapper_type**: implementation id from the fitted model (wrappers report inner type).

### 3) Calibration modes (summary)

| Mode | Trigger | Points | Training Y/X |
|------|---------|--------|----------------|
| `keyboard15` | Default `_start_calibration()` | 15 | Key centers + gaps/extras in letter region |
| `keyboard13` | `keyboard_geometry_targets(..., mode="keyboard13")` | 13 | Same, fewer extras |
| `fullscreen9` | `GAZEKEY_CALIB_FULLSCREEN=1` | 9 | Abstract screen 3×3 |
| `default9` / `precision13` | `keyboard_local_targets()` only | 9 / 13 | Abstract grid in typing rect |

Clip bounds for ridge predict: letter-keys region rect (`_calib_clip_rect`) in keyboard mode.

### 4) Quality gates (calibration must pass to enable typing)

**Mapper candidate gates** (`ridge.py` + `region_quality.py`):

- Keyboard mode: **region accuracy is primary** (wrong 3×3 row/col cell fails even if RMS is moderate).
- Pixel thresholds (keyboard): LOOCV/train errors are often warnings; region failures are hard fails.
- Default limits in `_on_calibration_finished`: `max_loocv_rms_px=95`, `max_target_loocv_px=110`, `max_train_error_px=60`.

**Final acceptance** (`evaluate_calibration_quality`):

- Additional checks (monotonicity, off-screen LOOCV, per-target train caps, etc.).
- **Keyboard** `corr(screen_y, avg_v)`: hard fail if `r < 0.15` (catastrophic); `0.15 ≤ r < 0.55` is a **warning only** (typing still enabled if other gates pass). **Fullscreen** still hard-fails below `0.15`.
- On failure: `_gaze_mapper_v2` cleared, recalibrate prompt; `calibration_debug.csv` written.

### 5) Known geometric issue (and mitigations)

**Problem**: Eye-local `v` correlates with horizontal gaze (`corr(v_mean, u_mean)` often 0.55–0.85). Same screen row (e.g. bottom-left vs bottom-right) can show different `avg_v`, so Y mappers tilt rows.

**Mitigations in pipeline**:

1. Dense **keyboard15** targets on real keys (more constraints than 3×3).
2. **poly12** models + prefer poly12 when coupling ≥ 0.55.
3. **pca4_decoupled_split** / **poly12 decoupled Y** — residualize v on u at fit and LOOCV folds.
4. **Row Y bias** — per-row mean residual correction.
5. **Local Y correction** — interpolate `dy` along screen X from calibration residuals (fixes within-row tilt).
6. **Runtime**: row-aware intent scoring + cross-row selection hysteresis (separate from mapper).

### 6) Environment variables (debug / overrides)

| Variable | Effect |
|----------|--------|
| `GAZEKEY_CALIB_FULLSCREEN=1` | 9-point fullscreen calibration instead of keyboard15 |
| `GAZEKEY_CALIB_DEBUG=1` | Verbose calibration overlay status + geometry overlay after fit |
| `GAZEKEY_CALIB_GEOM_DEBUG=1` | Show calibration geometry overlay (target/train/LOOCV) |
| `GAZEKEY_GAZE_DEBUG=1` | Preview dot shows raw + smoothed gaze (default on in code) |
| `GAZEKEY_GAZE_DEBUG_PRED=1` | Per-frame mapper predict logs |
| `GAZEKEY_GAZE_DEBUG_SELECTION=1` | Per-frame best/chosen key logs |
| `GAZEKEY_SELECTION_DEBUG=1` | Selection policy follows best every frame (no hysteresis) |

### 7) Legacy-only (do not modify; fallback)

- `gazekey/calibration/*` — v1 session, affine/interpolation mappers, `calibration_store` / `calibration_v1.json` (legacy, not loaded at runtime).
- Used only when v2 mapper is absent and v1 path is triggered in `_process_gaze_typing`.

### 8) Exact runtime flow (step-by-step)

#### Tracking → main thread

1. `TrackingManager` → `EyeDetector.detect` → `EyeData`
2. `TrackingBridge.forward` → `VirtualKeyboard._on_eye_data_main_thread`

#### Feature path

3. `FeatureExtractor.from_eye_data` → `FrameFeatures`
4. If calibrating: `CalibrationOverlay.add_features_dt` → `CalibrationV2Session.process`
5. If runtime: `PcaFeatureSmoother.smooth` → mapper → `GazeSmoother` → intent → selection → dwell/activate

#### Calibration v2

6. `_start_calibration()` → `keyboard_geometry_targets` (or fullscreen9) → `CalibrationV2Session` + overlay
7. Per target: fixation lock → accepted window mean → next target
8. `_on_calibration_finished` → `fit_calibration_mapper` → quality gates → `MapperStore.save` → preview mode on success

#### Runtime typing

9. `_gaze_mapper_v2.predict(smoothed_features)` → screen (x, y)
10. `score_keys(..., focused_key_id=..., row_stickiness=..., cross_row_penalty=...)`
11. `SelectionPolicy.update(..., best_row_index=...)` → focus + dwell
12. `GazeTypingController` + `_on_gaze_activate_key`

### 9) Debug artifacts (repo root)

| File | Contents |
|------|----------|
| `calibration_samples.csv` | Per-frame calibration samples |
| `calibration_summary.csv` | Per-target summary after fit |
| `calibration_debug.csv` | Per-target train/LOOCV errors + features |
| `calibration_ratio_space.csv` | Row-level avg_v stats export |
| `calibration_v2.json` | Fitted mapper + wrappers (v7) |
| `runtime_key_confidence.csv` | Runtime gaze/selection log |
| `keyboard_layout.csv` | Exported key geometry snapshot |

### 10) Legacy / cleanup notes

- `gazekey/debug/runtime_key_confidence_logger.py` docstring still says “Phase 0” — fields are live; docstring is stale.
- Per-frame `[rt2]` logs are gated by `GAZEKEY_GAZE_DEBUG_*` env vars.
- IDW mappers and `RowAwareMapper` remain candidates for future experiments, not current defaults.

### Quick checklist

- Calibration: **v2** + **keyboard15** (15 key-aligned points)
- Fit: **frozen pca4_baseline** + **region gates** + **row bias** + **local Y correction**
- Typing candidate doc: **`TYPING_CANDIDATE.md`**
- Persist: **`calibration_v2.json`** via `MapperStore`
- Runtime: **smoothed PCA features** → **v2 mapper** → **row-stable intent** → **hysteresis selection**
- Legacy `gazekey/calibration/`: **not used** on successful v2 path
