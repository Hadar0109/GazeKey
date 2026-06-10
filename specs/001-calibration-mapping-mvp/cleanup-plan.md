# Cleanup Plan — Phase 10B (T044)

**Feature**: `001-calibration-mapping-mvp`  
**Date**: 2026-06-10  
**Source inventory**: [cleanup-inventory.md](./cleanup-inventory.md)  
**Status**: **AWAITING USER APPROVAL (T045)** — do not execute T046+ until approved

## Principles (from plan.md)

1. **No blind deletion** — every removal has a dedicated task and prerequisite
2. **Behavior preservation** — no α, row-Y, local-Y, X correction, smoothing, layout default, or benchmark threshold changes during Phase 10
3. **Future interaction preserved** — dwell/intent/selection/gaze-typing moved aside, not deleted
4. **Layout candidates preserved** — `keyboard_full9`, `keyboard_wide9` stay in `targets.py` behind `GAZEKEY_CALIB_MODE`
5. **Incremental refactor first** — thin `virtual_keyboard.py` before archive/delete (easier to verify behavior)

## Execution order

```text
T045 approval
  → Phase 10C: T046 → T047 → T048 → T049 → T050 → T051 (refactor VK; no mapping param changes)
  → Phase 10D: T052 → T053 → T054 → T055 → T056 → T057 → T058 → T059 (cleanup)
  → T060 behavior gate
  → Phase 11 (T061 resume Phase 8)
```

---

## Section A — Keep (no action)

All **active-mvp** modules from inventory remain. Highlights:

| Area | Paths | Notes |
|------|-------|-------|
| Entry + tracking | `main.py`, `gazekey/tracking/*`, `gazekey/features/*` | Unchanged |
| Calibration v2 | `gazekey/calibration2/*` (all) | Including `targets.py` layout candidates |
| Mapping core | `ridge.py`, `typing_candidate.py`, `base.py`, `row_bias.py`, `local_y_correction.py` | Row bias **stays active** (`APPLY_ROW_Y_BIAS=True`) |
| Evaluation core | `benchmark_runner.py`, `run_summary.py`, `failure_analysis.py` | Unchanged |
| UI (post-refactor) | `calibration_controller.py`, `gaze_preview.py`, `camera_preview_window.py`, extracted modules | VK shrinks via T046–T051 |
| Typing (active) | `key_hit_tester.py`, `key_semantics.py`, `gaze_ui_mapper.py`, `text_buffer.py` | Mouse typing + benchmark hit tests |
| Debug (offline) | `gazekey/debug/*`, `scripts/*`, `evaluation/benchmark_diagnostics.py`, `coverage_diagnostics.py` | **Kept**; disconnected from default import chain in T047/T052 |
| Tests | `tests/unit/*`, `tests/integration/*` | MVP contract tests kept |
| Docs / runs | `specs/`, `runs/`, `docs/`, `TYPING_CANDIDATE.md` | Kept |
| Env-gated UI | `calibration_geometry_overlay.py` | Keep behind `GAZEKEY_CALIB_GEOM_DEBUG` |

---

## Section B — Refactor (Phase 10C, T046–T051)

| Task | Action | Paths | Prerequisite | Risk if rushed |
|------|--------|-------|--------------|----------------|
| **T046** | **refactor** | Extract `gazekey/ui/keyboard_layout.py` from `virtual_keyboard.py` | T045 | UI layout break |
| **T047** | **refactor** + **disconnect** | Extract `gazekey/ui/benchmark_controller.py`; move debug benchmark/diagnostics imports here (lazy/env-gated only) | T046 | Benchmark won't start |
| **T048** | **refactor** | Extract `gazekey/ui/mapper_runtime.py` (fit finish, predict/clamp, mapper store) | T047 | Mapping break |
| **T049** | **refactor** | Extract `gazekey/ui/gaze_loop.py` (eye_data dispatch; dormant typing path isolated) | T048 | Preview/tracking break |
| **T050** | **refactor** | Extract `gazekey/ui/env_flags.py` | T049 | Env flag regression |
| **T051** | **refactor** | Rewire `VirtualKeyboard` as thin orchestrator; T028 must pass | T050 | Integration failures |

**T047 disconnect detail**: `virtual_keyboard.py` must not top-level-import:

- `gazekey.debug.keyboard_accuracy_mapper_diag`
- `gazekey.debug.keyboard_accuracy_compare`
- `gazekey.debug.runtime_key_confidence_logger`
- `gazekey.debug.keyboard_accuracy` (except via `benchmark_controller`)

Diagnostics modules remain in repo; reachable only through `benchmark_controller` or env flags.

---

## Section C — Move aside (future interaction, T052)

| Task | Action | Paths | Prerequisite | Risk |
|------|--------|-------|--------------|------|
| **T052** | **move-aside** | Create `gazekey/future/` facade; re-export intent, selection, gaze typing modules | T051 | **Do not delete** |

**Move-aside scope** (modules preserved, not imported by active MVP gaze loop):

| From | To / pattern |
|------|----------------|
| `gazekey/intent/` | `gazekey/future/intent/` (re-export) or `gazekey/future/interaction.py` facade |
| `gazekey/selection/` | `gazekey/future/selection/` (re-export) |
| `gazekey/typing/gaze_typing_controller.py` | `gazekey/future/` |
| `gazekey/typing/dwell_selector.py` | `gazekey/future/` |

**Keep in `gazekey/typing/`** (active MVP): `key_hit_tester`, `key_semantics`, `gaze_ui_mapper`, `text_buffer`, `gaze_smoother` (shared with preview until ownership clarified in T049).

`VirtualKeyboard` active path imports `gazekey.future` only inside dormant code paths or not at all until interaction is re-enabled.

---

## Section D — Disconnect (Phase 10D)

| Task | Action | Paths | Prerequisite | Risk |
|------|--------|-------|--------------|------|
| **T053** | **disconnect** | Remove v1 `calibration_session` coupling from `calibration_overlay.py` — v2-only overlay API | T051 | Overlay break until v2-only types verified |
| **T054** | **disconnect** | Refactor `gazekey/mapping/__init__.py` to export PCA4/ridge API only (no `IDW*`, `RowAwareMapper`) | T053 | Test import updates required |

**T053 detail**: `calibration_overlay.py` currently imports v1 `CalibrationSession`, `Phase`, etc. Overlay used exclusively via `CalibrationController` + v2 session. Remove dual-path v1 support from overlay; keep v2 fixation UI only.

**T054 detail**: Tests that need dormant mappers import from `archive/mapping_variants/` after T055 (update in same task).

---

## Section E — Archive (Phase 10D, one task each)

| Task | Action | Source | Destination | Prerequisite | Tests affected |
|------|--------|--------|-------------|--------------|----------------|
| **T055** | **archive** | `gazekey/mapping/idw_local.py`, `idw_ratio.py`, `row_aware.py` | `archive/mapping_variants/` | T054 | `test_ridge_mapper_selection.py`, `test_keyboard_accuracy_compare_consistency.py`, `test_poly12_calibration_comparison.py` → update imports or move to `archive/tests/` |
| **T056** | **archive** | v1 calibration except `tracking_bridge.py` | `archive/calibration_v1/` | T053 | `test_calibration.py` |
| **T056** (cont.) | **refactor** | Move `tracking_bridge.py` → `gazekey/tracking/tracking_bridge.py` | — | T053 | Update `virtual_keyboard.py`, `calibration/__init__.py` consumers |
| **T057** | **archive** | `tests/test_calibration.py` | `archive/tests/test_calibration_v1.py` | T056 | v1 tests preserved offline |

**Not archived** (explicit):

- `keyboard_full9`, `keyboard_wide9` in `targets.py`
- `gazekey/debug/` entire tree
- `scripts/`
- `intent/`, `selection/` source (moved aside in T052, not archived)

---

## Section F — Delete (Phase 10D, one task each)

| Task | Action | Path | Prerequisite | Risk |
|------|--------|------|--------------|------|
| **T058** | **delete** | `key_accuracy_debug.csv`, `key_accuracy_compare.csv` (repo root) | T051 | None — duplicates exist under `runs/` |

**Not deleting**:

- Any Python module without archive + test update
- `CURRENT_PIPELINE.md` (keep; optional doc pointer only)
- `runs/` session artifacts

---

## Section G — Behavior gate (T060)

| Task | Action | Prerequisite |
|------|--------|--------------|
| **T060** | Re-run T029 baseline flow; document in `runs/phase10_behavior_gate.txt`; compare to pre-Phase-10 metrics | T052–T058 complete |

---

## Section H — Deferred / out of scope

| Item | Decision | Reason |
|------|----------|--------|
| `calibration2/geometry_diagnostics.py` | keep; already verbose/debug only | Low coupling |
| `README.md` update | defer to post-Phase-10 | Not blocking |
| `CURRENT_PIPELINE.md` superseded banner | optional doc task after T060 | Low priority |
| Mapper variant tests in `tests/` | archive with T055 or update imports | Resolved during T055 |
| `gazekey/calibration/README.md` | archive with T056 | v1 doc |

---

## Task map (tasks.md after T044)

| ID | Phase | Summary |
|----|-------|---------|
| T044 | 10B | This cleanup plan ✅ |
| T045 | 10B | **User approval gate** — pending |
| T046–T051 | 10C | VK refactor (6 tasks) |
| T052 | 10D | Future interaction move-aside |
| T053 | 10D | Overlay v2-only decouple |
| T054 | 10D | mapping `__init__` PCA4-only |
| T055 | 10D | Archive mapper variants |
| T056 | 10D | Move TrackingBridge; archive v1 calibration |
| T057 | 10D | Archive v1 calibration tests |
| T058 | 10D | Delete root stale CSVs |
| T059 | 10D | *(reserved — merged into T047/T052 if no extra work)* |
| T060 | 10D | Behavior preservation gate |
| T061 | 11 | Resume Phase 8 |
| T062–T063 | 12 | Acceptance |

> **Note**: T059 reserved. If T047 fully handles debug disconnect and no extra disconnect remains after T052, T059 is cancelled/skipped. Otherwise assign a leftover disconnect item.

---

## Approval checklist (T045)

Review and confirm:

- [ ] Execution order (10C refactor before 10D archive) is acceptable
- [ ] `gazekey/future/` move-aside approach for interaction code is acceptable
- [ ] `archive/calibration_v1/` and `archive/mapping_variants/` destinations are acceptable
- [ ] TrackingBridge move to `gazekey/tracking/` is acceptable
- [ ] Root CSV deletion is acceptable
- [ ] No mapping accuracy parameters will change during Phase 10
- [ ] `keyboard_full9` / `keyboard_wide9` preservation confirmed

**To approve**: Reply with explicit approval of this plan (e.g. "approve cleanup plan" or note any changes). Implementation of T046+ begins only after approval.
