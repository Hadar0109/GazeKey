# Inventory review gate (T019)

**Feature**: `002-gaze-typing-os`  
**Date**: 2026-08-08  
**Status**: **SIGNED OFF** — T020–T022 may proceed per decisions below

This gate blocked T020–T022 until human review. Sign-off recorded here.

## Artifacts reviewed

1. `specs/002-gaze-typing-os/env-flag-inventory.md`
2. `specs/002-gaze-typing-os/cleanup-inventory.md`

## Sign-off

| Field | Value |
|-------|-------|
| Reviewer | User (feature owner) |
| Sign-off date | 2026-08-08 |
| Approved env-flag actions | See below |
| Approved cleanup actions | See below |

### Approved `GAZEKEY_*` actions

| Action | Flags |
|--------|-------|
| **KEEP** | `VERBOSE` |
| **MOVE TO TOOLS** | `DEV_BENCHMARK`, `CALIB_GEOM_DEBUG` |
| **DELETE** | `SELECTION_DEBUG`, `GAZE_DEBUG_PRED`, `GAZE_DEBUG_SELECTION`; scrub docs-only obsolete accuracy flag names (`KEYBOARD_ACCURACY_DEBUG`, `KEYBOARD_ACCURACY_COMPARE`) |
| **PRESERVE / RE-EVALUATE** (no final MOVE/DELETE yet) | `CALIB_MODE`, `GAZE_DEBUG`, `CALIB_DEBUG`, `DIAG_EXTRACTOR`, `CAMERA_PREVIEW_DURING_CALIB` |

Notes: `CALIB_MODE` may eventually become a developer override while the product
keeps one default calibration configuration — do not MOVE/DELETE it in T020–T022.

### Approved cleanup actions

| Action | Items |
|--------|-------|
| **DELETE** | Four standalone camera/MediaPipe demos (`scripts/camera_simple.py`, `camera_face.py`, `camera_mediapipe_iris_demo.py`, `eye_landmarker_demo.py`) after final import/workflow check |
| **MOVE** | `scripts/analyze_correction_layers.py` → appropriate developer tooling area (mapping analysis remains an active workflow); delete later only if inspection shows no valid purpose |
| **KEEP + REWRITE** | Active repository documentation (README + pipeline/structure docs) |
| **KEEP** | Active test suite |
| **DEFER** | `text_buffer` → later T046 re-evaluation |

## Explicitly not in this sign-off

- Final MOVE/DELETE for RE-EVALUATE flags
- T023+ post-cleanup behavior gate
- New typing implementation
- Calibration/mapping behavior changes

## T020–T022 execution (2026-08-08)

Executed per this sign-off; **STOP before T023**.

| Task | Result |
|------|--------|
| T020 | `DEV_BENCHMARK` / `CALIB_GEOM_DEBUG` → `tools/flags.py`; tools consumers updated; removed from product `env_flags` |
| T021 | Deleted `SELECTION_DEBUG`, `GAZE_DEBUG_PRED`, `GAZE_DEBUG_SELECTION` (+ VK dead fields); scrubbed obsolete accuracy flag names from active docs |
| T022 | Deleted four camera/MediaPipe demos; moved `analyze_correction_layers.py` → `tools/debug/`; rewrote README + `docs/{CURRENT_PIPELINE,PROJECT_STRUCTURE,gazekey_code_structure,TYPING_CANDIDATE}.md` + `tools/README.md` |
