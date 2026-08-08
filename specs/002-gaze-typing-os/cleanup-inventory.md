# Cleanup inventory (002) — T018

**Feature**: `002-gaze-typing-os`  
**Date**: 2026-08-08  
**Status**: Reviewed (T019) — **T022 executed** (demos deleted; analyze script moved; active docs rewritten). Further items remain deferred (e.g. `text_buffer` → T046).

**Scope**: Repository-wide candidates outside the already-completed package moves
(T006–T011) and obsolete-path deletes (T012–T017). Inspected: `archive/`,
`scripts/`, docs, tests, compatibility leftovers, and cross-check with
`env-flag-inventory.md`.

**Rules for T018**: Inventory only. Do **not** delete, move, or rewrite broad
content until T019 sign-off and T020–T022 apply steps.

---

## Already completed (context — not re-actioned here)

| Item | Status |
|------|--------|
| `gazekey/evaluation/` → `tools/evaluation/` | Done (T006) |
| `gazekey/debug/` → `tools/debug/` | Done (T007) |
| Preview / benchmark out of product default path | Done (T008–T011) |
| `gazekey/future/`, `intent/`, `selection/` | Deleted (T012–T014) |
| `typing/dwell_selector.py`, `typing/gaze_typing_controller.py` | Deleted (T015–T016) |
| VK `_gaze_typing_*` stubs | Removed (T017) |

---

## 1. `archive/`

| Path | Classification | Reason |
|------|----------------|--------|
| `archive/` (entire tree) | **N/A — absent** | Not present in the current working tree (`git ls-files archive` empty). 001 cleanup docs still *describe* archived v1 / mapping variants historically. No delete action possible here. If restored from another clone/history: treat as offline research → prefer **KEEP** only if needed for mapping archaeology; otherwise **DELETE**. |

---

## 2. `scripts/` (repo root)

None of these are imported by `main.py` / `gazekey/` / `tools/`.

| Path | Classification | Reason |
|------|----------------|--------|
| `scripts/camera_simple.py` | **DELETE** | **Done (T022)** — no active imports/workflow. |
| `scripts/camera_face.py` | **DELETE** | **Done (T022)**. |
| `scripts/camera_mediapipe_iris_demo.py` | **DELETE** | **Done (T022)**. |
| `scripts/eye_landmarker_demo.py` | **DELETE** | **Done (T022)**. |
| `scripts/analyze_correction_layers.py` | **MOVE** → `tools/debug/` | **Done (T022)** — mapping analysis workflow retained. |
| `scripts/__pycache__/` | **DELETE** | Generated; local only. |

---

## 3. Docs (stale vs product/tools architecture)

| Path | Classification | Reason |
|------|----------------|--------|
| `README.md` | **KEEP** + **rewrite** | **Done (T022)** — product vs tools entrypoints. |
| `docs/CURRENT_PIPELINE.md` | **KEEP** + **rewrite** | **Done (T022)**. |
| `docs/PROJECT_STRUCTURE.md` | **KEEP** + **rewrite** | **Done (T022)**. |
| `docs/gazekey_code_structure.md` | **KEEP** + **rewrite** | **Done (T022)**. |
| `docs/TYPING_CANDIDATE.md` | **KEEP** + **rewrite** | **Done (T022)** — scrubbed obsolete accuracy flags. |
| `docs/GazeKey_Project_Specification.pdf` | **KEEP** | Long-term vision (constitution VIII). |
| `docs/gazekey_system_architecture.png` | **KEEP** | Architecture visual; may be dated but harmless. |
| `docs/mediapipe landmark face.jpg` | **KEEP** | Reference imagery. |
| `docs/current-status.md` | **N/A — absent** | Referenced in older notes; not in tree/git. No action. |

**Note**: Spec Kit history under `specs/001-*` intentionally documents past decisions — **KEEP** as historical SoT for feature 001; do not mass-delete. Optional light “superseded by 002” notes later.

---

## 4. Tests

| Path | Classification | Reason |
|------|----------------|--------|
| `tests/unit/*`, `tests/integration/test_mvp_pipeline.py` | **KEEP** | Active coverage for calib/mapping/tools attach. |
| `tests/test_gaze_typing.py` | **KEEP** | Retained hit-test / smoother / text-buffer tests after T015 dwell removal. |
| `tests/test_ridge_mapper_selection.py` | **KEEP** | Name says “selection” but covers PCA4 alpha selection — active mapping. |
| `tests/test_typing_candidate.py`, `test_keyboard_geometry_targets.py`, `test_fixation_head_gate.py`, `test_*quality*`, `test_feature_smoother.py`, `test_row_y_bias_path.py`, `test_calibration2_*` | **KEEP** | Active calibration/mapping foundation tests. |
| `tests/unit/test_preview_readonly.py` | **KEEP** | Still validates tools preview attach + product non-typing; T060 may rewrite assertions later. |
| `archive/tests/*` | **N/A — absent** | Would be offline-only if archive restored. |

No test file found that *only* targeted deleted `future`/`intent`/`selection` packages remaining to delete in this inventory.

---

## 5. Compatibility / dead product artifacts (code)

| Item | Classification | Reason |
|------|----------------|--------|
| `EnvFlags.selection_debug` / `GAZEKEY_SELECTION_DEBUG` | **DELETE** (via flag inventory T021) | Selection package gone; flag unread beyond load. |
| `EnvFlags.rt2_debug_pred` / `GAZEKEY_GAZE_DEBUG_PRED` | **DELETE** (via T021) | Dead after assignment. |
| `EnvFlags.rt2_debug_selection` / `GAZEKEY_GAZE_DEBUG_SELECTION` | **DELETE** (via T021) | Dead; selection path gone. |
| VK `_on_gaze_focus_key` / `_on_gaze_activate_key` / `_set_key_gaze_style` | **KEEP** | Still used by tools benchmark highlight; will support Phase 5 dwell visuals. |
| `gazekey/typing/text_buffer.py` + VK wiring | **RE-EVALUATE** | Still on product mouse path; T046 later may delete/move if unjustified for OS-typing success path. **Do not delete in T018–T022 without explicit review.** |
| Legacy layout mode strings in `targets.py` (`keyboard15_legacy`, etc.) | **KEEP** | Behind `GAZEKEY_CALIB_MODE` experiments; tied to flag re-eval. |
| `runs/` session artifacts | **KEEP** | Output of tools writers; not source. Optional gitignore hygiene later. |

---

## 6. Cross-check: `GAZEKEY_*` (see `env-flag-inventory.md`)

Provisional directions (still **not applied**):

| Classification | Flags |
|----------------|-------|
| **KEEP** | `VERBOSE` |
| **MOVE TO TOOLS** | `DEV_BENCHMARK`, `CALIB_GEOM_DEBUG` |
| **DELETE** (candidates) | `SELECTION_DEBUG`, `GAZE_DEBUG_PRED`, `GAZE_DEBUG_SELECTION` (+ docs-only accuracy flag names) |
| **RE-EVALUATE** (preserve) | `CALIB_MODE`, `GAZE_DEBUG`, `CALIB_DEBUG`, `DIAG_EXTRACTOR`, `CAMERA_PREVIEW_DURING_CALIB` |

Post–T012–T017 note: DELETE candidates for selection-related flags are **stronger** now that `gazekey/selection/` is gone.

---

## Summary table (proposed actions after sign-off)

| Priority | Action | Candidates |
|----------|--------|------------|
| A | DELETE scripts demos | `camera_*.py`, `eye_landmarker_demo.py` |
| B | MOVE or DELETE | `analyze_correction_layers.py` → tools or remove |
| C | Docs rewrite (not delete) | README, CURRENT_PIPELINE, PROJECT_STRUCTURE, gazekey_code_structure, TYPING_CANDIDATE |
| D | Flag apply (T020–T021) | Per `env-flag-inventory.md` after sign-off |
| E | Defer | `text_buffer` product role (T046); `CALIB_MODE` and other RE-EVALUATE flags |

---

## Review sign-off

| Field | Value |
|-------|-------|
| Inventory complete (T018) | Yes |
| Deletions/moves executed | **No** |
| Review sign-off | *(pending — T019)* |
| Sign-off date | |
| Sign-off notes | |
