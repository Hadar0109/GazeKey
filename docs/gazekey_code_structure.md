# GazeKey Code Structure (`gazekey/` + `tools/`)

**Last updated:** 2026-08-08 (tools split + inventory T020–T022)

Authoritative runtime narrative: **`docs/CURRENT_PIPELINE.md`**. Frozen mapper
config: **`docs/TYPING_CANDIDATE.md`** / **`gazekey/mapping/config.py`**.

## Product active path

```text
main.py → VirtualKeyboard (ui/)
  tracking/ → features/ → calibration/ (session collection)
  → mapping/ (PCA4 ridge fit) → runtime/ (fit, predict, gaze loop)
  → typing/ (hit testing, text buffer, gaze smoother)
```

`gazekey/` is **product-runtime only**. Preview, benchmark, and debug artifact
writers live under **`tools/`** and attach via `tools.devtools_install`.

Mouse clicks still type via `typing/text_buffer.py`. Dwell typing / OS injection
are not wired yet (`002-gaze-typing-os`).

Session artifacts are written under **`runs/<session_id>/`**.

---

## Root (`gazekey/`)

| File | Role |
|------|------|
| `__init__.py` | Package marker (`__version__`). |
| `mvp_log.py` | Quiet-by-default logging (`--verbose`). |
| `app_config.py` | CLI → process `AppConfig` (no `GAZEKEY_*` env). |

---

## `gazekey/tracking/`

| File | Role |
|------|------|
| `tracking_bridge.py` | Qt signal from worker thread. |
| `video_capture.py` | Webcam frame capture thread. |
| `eye_detector.py` | `EyeDetector`, `EyeData` — MediaPipe landmarks. |
| `tracking_manager.py` | Orchestrates capture + detection. |

---

## `gazekey/features/`

| File | Role |
|------|------|
| `feature_types.py` | `FrameFeatures` dataclass. |
| `extractor.py` | `EyeData` → `FrameFeatures`. |
| `feature_smoother.py` | Runtime PCA EMA (`FEATURE_SMOOTHER_ALPHA`). |

---

## `gazekey/calibration/`

| File | Role |
|------|------|
| `session.py` | `CalibrationSession`, `CalibrationResult`. |
| `targets.py` | Target layouts (`keyboard15` default; override via `--calib-mode`). |
| `fixation_gate.py` | Fixation stability gating. |
| `quality.py` | Post-fit quality / usable-mapper gates. |
| `region_quality.py` | Per-target region LOOCV checks. |
| `outliers.py` | Peer outlier detection among targets. |

Session IDs: `gazekey/runtime/session_id.py`. Tools summaries/paths:
`tools/evaluation/`.

---

## `gazekey/mapping/`

**Active:** PCA4 ridge only.

| File | Role |
|------|------|
| `config.py` | Frozen MVP config (α grid, gates, smoothers, `keyboard15`). |
| `base.py` | `Mapper`, `MapperPrediction`, `MapperFitResult`. |
| `ridge.py` | `Pca4BaselineMapper`, `fit_calibration_mapper`, LOOCV α selection. |
| `row_bias.py` | Post-fit row-Y bias wrapper (`APPLY_ROW_Y_BIAS=True`). |

Inactive / archived variants: prefer `archive/mapping_variants/`.

---

## `gazekey/runtime/`

| File | Role |
|------|------|
| `tracking_controller.py` | Camera/tracking lifecycle. |
| `gaze_loop.py` | Eye-data dispatch (calibration vs mapped-gaze / tools modes). |
| `mapper_runtime.py` | Post-calibration fit, quality gates, predict/clamp. |
| `session_id.py` | Product session id helper. |

---

## `gazekey/layout/`

| File | Role |
|------|------|
| `layout_inspector.py` | Qt widget → `KeyGeometryRow` list. |

Layout CSV export: **`tools/debug/layout_csv.py`**.

---

## `gazekey/typing/`

| File | Role |
|------|------|
| `key_hit_tester.py` | Gaze-point hit testing (tools benchmark + future typing). |
| `key_semantics.py` | Button label → action. |
| `gaze_ui_mapper.py` | Screen bounds → keyboard region rects. |
| `text_buffer.py` | Text field updates (mouse typing; re-eval T046). |
| `gaze_smoother.py` | Screen-coordinate EMA (`GAZE_SMOOTHER_ALPHA`). |

---

## `gazekey/ui/`

| File | Role |
|------|------|
| `virtual_keyboard.py` | Thin orchestrator — wires controllers + NullDevTools. |
| `keyboard_layout.py` | Key grid, chrome, responsive geometry. |
| `calibration_controller.py` | Start calibration session + overlay. |
| `calibration_overlay.py` | Fullscreen fixation UI. |
| `calibration_finish.py` | Post-session fit; delegates tools artifacts via DevTools. |
| `camera_preview_window.py` | Floating webcam PiP. |
| `devtools_api.py` | `DevTools` protocol + `NullDevTools`. |
| `env_flags.py` | Thin helpers over `gazekey.app_config`. |

---

## `tools/` (developer)

| Path | Role |
|------|------|
| `devtools_install.py` | Attach preview / benchmark / artifact writers. |
| `flags.py` | `DEV_BENCHMARK`, `CALIB_GEOM_DEBUG`. |
| `preview/` | Read-only gaze preview entry (`python -m tools.preview`). |
| `evaluation/` | Benchmark + session paths + finish artifacts. |
| `debug/` | Mapper store, layout CSV, geometry overlay, offline analysis. |

---

## `archive/`

| Path | Role |
|------|------|
| `archive/calibration_v1/` | Legacy v1 calibration. |
| `archive/mapping_variants/` | Poly12, local-Y, and other experiments. |
| `archive/tests/` | Offline comparisons against archived artifacts. |

---

## Removed in cleanup (`002`)

| Was | Now |
|-----|-----|
| `gazekey/future/`, `intent/`, `selection/` | Deleted |
| Product `evaluation/` / `debug/` / preview controllers | `tools/` |
| `scripts/camera_*.py`, `eye_landmarker_demo.py` | Deleted |
| `scripts/analyze_correction_layers.py` | `tools/debug/analyze_correction_layers.py` |
| Dead flags `SELECTION_DEBUG`, `GAZE_DEBUG_PRED`, `GAZE_DEBUG_SELECTION` | Deleted |
