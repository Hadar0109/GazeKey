# GAZEKEY_* environment flag inventory (002)

**Feature**: `002-gaze-typing-os`  
**Status**: **Reviewed + T020–T021 applied** (2026-08-08)  
**Date**: 2026-08-08

**Rules**:
- Classifications below match `inventory-review.md` sign-off.
- RE-EVALUATE flags remain in product until a later decision — no final MOVE/DELETE yet.
- `CALIB_MODE` may eventually become a developer override while the product keeps one
  default calibration configuration.

---

## Inventory (post T020–T021)

| Flag | Read sites | Classification | Status |
|------|------------|----------------|--------|
| `GAZEKEY_VERBOSE` | `gazekey/ui/env_flags.py`; `gazekey/mvp_log.py` | **KEEP** | In product |
| `GAZEKEY_DEV_BENCHMARK` | `tools/flags.py` → `tools/evaluation/benchmark_controller.py` | **MOVE TO TOOLS** | **Done** — removed from product `env_flags` |
| `GAZEKEY_CALIB_GEOM_DEBUG` | `tools/flags.py` → `tools/evaluation/calib_finish_artifacts.py` | **MOVE TO TOOLS** | **Done** — removed from product `env_flags` |
| `GAZEKEY_SELECTION_DEBUG` | *(none)* | **DELETE** | **Done** — removed from `env_flags` / VK |
| `GAZEKEY_GAZE_DEBUG_PRED` | *(none)* | **DELETE** | **Done** |
| `GAZEKEY_GAZE_DEBUG_SELECTION` | *(none)* | **DELETE** | **Done** |
| `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB` | `env_flags` → VK / gaze_loop | **RE-EVALUATE** | Preserved in product |
| `GAZEKEY_CALIB_MODE` | `env_flags` → `calibration_controller` | **RE-EVALUATE** | Preserved in product |
| `GAZEKEY_GAZE_DEBUG` | `env_flags` → `rt2_debug` | **RE-EVALUATE** | Preserved in product |
| `GAZEKEY_CALIB_DEBUG` | `env_flags` → VK / fixation UI | **RE-EVALUATE** | Preserved in product |
| `GAZEKEY_DIAG_EXTRACTOR` | `gazekey/features/extractor.py` | **RE-EVALUATE** | Preserved |

### Docs-only / scrubbed

| Flag | Classification | Status |
|------|----------------|--------|
| `GAZEKEY_KEYBOARD_ACCURACY_DEBUG` | **DELETE** (docs) | Scrubbed from active docs (T022) |
| `GAZEKEY_KEYBOARD_ACCURACY_COMPARE` | **DELETE** (docs) | Scrubbed from active docs (T022) |

---

## Classification summary

| Classification | Flags |
|----------------|-------|
| **KEEP** | `GAZEKEY_VERBOSE` |
| **MOVE TO TOOLS** (executed) | `GAZEKEY_DEV_BENCHMARK`, `GAZEKEY_CALIB_GEOM_DEBUG` |
| **DELETE** (executed) | `GAZEKEY_SELECTION_DEBUG`, `GAZEKEY_GAZE_DEBUG_PRED`, `GAZEKEY_GAZE_DEBUG_SELECTION` (+ docs-only accuracy names) |
| **RE-EVALUATE** (preserve) | `GAZEKEY_CALIB_MODE`, `GAZEKEY_GAZE_DEBUG`, `GAZEKEY_CALIB_DEBUG`, `GAZEKEY_DIAG_EXTRACTOR`, `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB` |

---

## Review sign-off

| Field | Value |
|-------|-------|
| Review gate (T019) | Signed off — see `inventory-review.md` |
| T020 MOVE | Done (`tools/flags.py`) |
| T021 DELETE | Done |
| T022 cleanup/docs | Done |
| Next gate | T023+ (do not start until review of this stop) |
