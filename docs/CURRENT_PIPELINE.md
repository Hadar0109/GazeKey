## CURRENT_PIPELINE

Authoritative description of the **active product runtime** after the tools split
(`002-gaze-typing-os` cleanup, 2026-08).

### Entry point

```
main.py
  → QApplication
  → VirtualKeyboard.show()
  → VirtualKeyboard.on_app_started()
       → schedule layout inspect (in memory)
       → start calibration if no usable mapper
```

Developer sessions that need preview / benchmark / debug overlays use:

```
python -m tools.preview
python -m tools.evaluation   # optional GAZEKEY_DEV_BENCHMARK=1
```

Those entries call `tools.devtools_install.install_devtools` so product code never
imports `tools.*`.

### High-level diagram

```
Camera → EyeData → FeatureExtractor
       → [calibrating] CalibrationSession + CalibrationOverlay
       → [after fit]  MapperRuntime (PCA4 ridge + row bias)
       → [product] usable mapped gaze (mouse typing still available)
       → [tools only] GazePreview / BenchmarkEvalSession
```

Mouse clicks on keys still route through the normal Qt button handlers and
`TextBufferController`. Gaze dwell typing and OS injection are **not** on the
product path yet.

---

### Active product packages (`gazekey/`)

| Area | Files | Role |
|------|-------|------|
| UI shell | `gazekey/ui/virtual_keyboard.py` | Thin orchestrator; wires controllers |
| Layout | `gazekey/ui/keyboard_layout.py`, `gazekey/layout/layout_inspector.py` | Keyboard chrome + key geometry snapshot |
| Tracking | `gazekey/tracking/*` | Background capture → `EyeData` |
| Features | `gazekey/features/*` | `FrameFeatures` + runtime PCA EMA |
| Runtime | `gazekey/runtime/*` | Lifecycle, per-frame dispatch, fit/predict, session id |
| Calibration | `gazekey/calibration/*`, `gazekey/ui/calibration_*` | Targets, fixation, finish orchestration |
| Mapping | `gazekey/mapping/*` | PCA4 ridge + optional row-Y bias |
| Typing helpers | `gazekey/typing/*` | Hit test, text buffer, gaze smoother (kept for product/tools) |

### Developer tools (`tools/`)

| Area | Role |
|------|------|
| `tools/preview/` | Read-only gaze preview entry |
| `tools/evaluation/` | Benchmark UI/scoring, session paths, calib finish artifacts |
| `tools/debug/` | Mapper snapshot, layout CSV, geometry overlay/diagnostics, offline analysis |
| `tools/flags.py` | `GAZEKEY_DEV_BENCHMARK`, `GAZEKEY_CALIB_GEOM_DEBUG` |

---

### Mapping (PCA4 only)

| File | Role |
|------|------|
| `gazekey/mapping/config.py` | Frozen MVP constants (α grid, gates, smoothers) |
| `gazekey/mapping/ridge.py` | `fit_calibration_mapper` → `Pca4BaselineMapper` |
| `gazekey/mapping/row_bias.py` | Optional post-fit row-Y bias (`APPLY_ROW_Y_BIAS`) |

`fit_calibration_mapper` fits **only** `pca4_baseline`. Poly12, decoupled, local-Y,
and multi-candidate ranking are **not** on the active path (variants under `archive/`).

### Quality gates

| File | Role |
|------|------|
| `gazekey/runtime/mapper_runtime.py` | Calls fit + `evaluate_calibration_quality` |
| `gazekey/calibration/quality.py` | Usability decision (usable mapper for product path) |
| `gazekey/calibration/region_quality.py` | Per-target region LOOCV checks |

On failure: mapper cleared, RECALIBRATE prompt; debug artifacts still written when
tools are attached.

---

### Mapper selection

- **When**: `CalibrationFinishController.on_finished` → `MapperRuntime.complete_calibration_fit`
- **What**: `pca4_baseline` ridge + optional `MapperWithRowBias`
- **Load on startup**: **disabled** — mapper snapshots are write-only for inspection
- **Runtime handle**: `MapperRuntime.model` (exposed on `VirtualKeyboard` as `_gaze_mapper`)

---

### Calibration modes

| Mode | How | Points |
|------|-----|--------|
| `keyboard15` | Default (`mapping/config.py`) | 15 on real key centers + row structure |
| Other layouts | `GAZEKEY_CALIB_MODE` (product, re-evaluate) | See `gazekey/calibration/targets.py` |

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
7. Quality gates → summaries (+ tools debug exports when attached)

#### After calibration (product)

8. Usable mapper available; mouse typing continues via `TextBufferController`
9. Gaze dwell / OS inject not wired yet (`002` later phases)

#### Tools preview / benchmark (optional)

10. `python -m tools.preview` or `tools.evaluation` attaches DevTools
11. Preview: `MapperRuntime.predict_gaze_v2` → `GazeSmoother` → gaze dot
12. Benchmark (`GAZEKEY_DEV_BENCHMARK=1`): sequential keys via `key_hit_tester` + `benchmark_runner`
13. Write `benchmark_summary.txt` + `benchmark_diag.json` under the session folder

---

### Session artifacts (`runs/<session_id>/`)

| File | When |
|------|------|
| `keyboard_layout.csv` | Tools artifact writer (when attached) |
| `calibration_v2.json` | After ridge fit (inspection snapshot) |
| `calibration_summary.txt` | Calibration finish |
| `coverage.json` | Calibration finish (tools) |
| `calibration_debug.csv` | Calibration finish (fit succeeded) |
| `calibration_ratio_space.csv` | Calibration finish |
| `benchmark_summary.txt` | Tools benchmark finish |
| `benchmark_diag.json` | Tools benchmark finish |

Path helpers: `tools/evaluation/session_paths.py` (tools); product session id:
`gazekey/runtime/session_id.py`.

Nothing new is written to the repository root.

---

### Environment variables

#### Product (`gazekey/ui/env_flags.py`)

| Variable | Effect |
|----------|--------|
| `GAZEKEY_VERBOSE=1` | Verbose calibration/runtime logs |
| `GAZEKEY_CALIB_MODE` | Override calibration target layout (re-evaluate) |
| `GAZEKEY_CALIB_DEBUG=1` | Verbose fixation overlay (re-evaluate) |
| `GAZEKEY_GAZE_DEBUG=1` | Extra gaze predict logs (re-evaluate) |
| `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB=1` | Camera PiP during fixation (re-evaluate) |

#### Tools (`tools/flags.py`)

| Variable | Effect |
|----------|--------|
| `GAZEKEY_DEV_BENCHMARK=1` | Auto 15-key benchmark after tools calib+preview |
| `GAZEKEY_CALIB_GEOM_DEBUG=1` | Post-fit geometry overlay |

Deleted (do not use): `GAZEKEY_SELECTION_DEBUG`, `GAZEKEY_GAZE_DEBUG_PRED`,
`GAZEKEY_GAZE_DEBUG_SELECTION`, and obsolete accuracy flag names.

---

### Not on the active path

| Was / exists | Status |
|--------------|--------|
| `gazekey/future/`, `intent/`, `selection/` | **Deleted** (cleanup) |
| Product preview / auto-benchmark | Moved to `tools/` |
| Standalone `scripts/camera_*.py` demos | **Deleted** |
| Mapping offline analysis | `tools/debug/analyze_correction_layers.py` |
| Poly12 / local-Y / decoupled mappers | `archive/` only |

---

### Quick checklist

- Calibrate every launch: **`CalibrationSession`** + **`keyboard15`**
- Fit: **`pca4_baseline`** + **row Y bias** (no local-Y on active path)
- Config: **`gazekey/mapping/config.py`** + **`docs/TYPING_CANDIDATE.md`**
- Persist: **`runs/<session_id>/calibration_v2.json`** via tools debug writers when attached
- Product: usable mapper after pass; mouse typing; no dwell yet
- Tools: `python -m tools.preview` / `tools.evaluation`
