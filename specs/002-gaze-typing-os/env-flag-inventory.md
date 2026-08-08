# GAZEKEY_* / launch-option inventory (002)

**Feature**: `002-gaze-typing-os`  
**Status**: **ENV → CLI migration complete** (2026-08-08)  
**Date**: 2026-08-08

**Rules**:
- Normal workflows do **not** require environment variables.
- Launch options are explicit CLI flags on entry points.
- **No** `GAZEKEY_*` environment-variable fallback after migration.
- Process config lives in `gazekey/app_config.py` (apply at entry; runtime reads
  `get_config()` / thin helpers only).

---

## Entry points

| Entry | Meaning |
|-------|---------|
| `python main.py` | Product: calibration → typing |
| `python -m tools.preview` | Developer mapped-gaze preview |
| `python -m tools.evaluation` | Developer benchmark/evaluation (**implies** auto-benchmark) |

## CLI options

| Option | Product | Preview | Evaluation | Notes |
|--------|:-------:|:-------:|:----------:|-------|
| `--verbose` | ✓ | ✓ | ✓ | Quiet-by-default detail logs |
| `--calib-mode <mode>` | ✓ | ✓ | ✓ | Override layout; default `keyboard15` |
| `--calib-debug` | ✓ | ✓ | ✓ | Verbose fixation UI |
| `--gaze-debug` | ✓ | ✓ | ✓ | Extra mapped-gaze labels |
| `--camera-preview-during-calib` | ✓ | ✓ | ✓ | Camera PiP during fixation |
| `--calib-geom-debug` | — | ✓ | ✓ | Tools-only; **independent** of verbose/calib-debug |

Evaluation does **not** take `--no-auto-benchmark`; the entry itself enables it.

## Deleted (no code reads)

| Former env | Disposition |
|------------|-------------|
| `GAZEKEY_DEV_BENCHMARK` | **DELETE** — replaced by evaluation entry |
| `GAZEKEY_DIAG_EXTRACTOR` | **DELETE** |
| `GAZEKEY_VERBOSE` | **DELETE** — `--verbose` |
| `GAZEKEY_CALIB_MODE` | **DELETE** — `--calib-mode` |
| `GAZEKEY_CALIB_DEBUG` | **DELETE** — `--calib-debug` |
| `GAZEKEY_GAZE_DEBUG` | **DELETE** — `--gaze-debug` |
| `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB` | **DELETE** — `--camera-preview-during-calib` |
| `GAZEKEY_CALIB_GEOM_DEBUG` | **DELETE** — `--calib-geom-debug` |
| `GAZEKEY_SELECTION_DEBUG` / `GAZEKEY_GAZE_DEBUG_PRED` / `GAZEKEY_GAZE_DEBUG_SELECTION` | Already deleted |
| `GAZEKEY_KEYBOARD_ACCURACY_*` | Docs-only; remain deleted |
| `GAZEKEY_ENABLE_TYPING` | Never a real flag |

## Modules

| Module | Role |
|--------|------|
| `gazekey/app_config.py` | `AppConfig`, parsers, `apply_config` / `get_config` |
| `gazekey/ui/env_flags.py` | Thin product helpers over `get_config()` |
| `tools/flags.py` | `auto_benchmark_enabled`, `calib_geom_debug` over `get_config()` |
| `gazekey/mvp_log.py` | Verbose gate from `get_config().verbose` |
