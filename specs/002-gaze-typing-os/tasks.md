# Tasks: Gaze Typing & OS Integration

**Input**: Design documents from `specs/002-gaze-typing-os/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`,
`quickstart.md`; Constitution v1.3.0

**Tests**: Included for KeyAction/dispatcher/adapter/dwell (spec SC-007 +
quickstart automated checks). Mapping benchmark remains independent (001 / tools).

**Organization**: Phases follow **plan binding order** (cleanup → post-cleanup gate
→ inject skeleton → focus validation → full typing). User-story labels map to
spec.md US1–US4. **US3 (cleanup) runs before US1** despite P3 priority.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no incomplete blockers)
- **[Story]**: [US1]…[US4] on story-phase tasks only

---

## Phase 1: Setup

**Purpose**: Scaffold `tools/` and planning inventories without breaking product yet.

- [x] T001 Confirm branch `002-gaze-typing-os` and feature dir `specs/002-gaze-typing-os/`
- [x] T002 Create `tools/` package layout with `tools/__init__.py`, `tools/evaluation/`, `tools/debug/`, `tools/preview/` per `specs/002-gaze-typing-os/plan.md`
- [x] T003 [P] Add `specs/002-gaze-typing-os/env-flag-inventory.md` skeleton table (Flag | Read sites | Tests/docs | KEEP/MOVE/DELETE) seeded from research R4 — **no flag deletions until inventory complete and reviewed**

**Checkpoint**: `tools/` exists; flag inventory file started.

---

## Phase 2: Foundational — Flag inventory (blocks cleanup deletes)

**Purpose**: Explicit `GAZEKEY_*` inventory before any flag MOVE/DELETE.

- [x] T004 Complete `specs/002-gaze-typing-os/env-flag-inventory.md` by repo-searching all `GAZEKEY_*` reads (include `gazekey/ui/env_flags.py`, `gazekey/mvp_log.py`, `gazekey/features/extractor.py`, tests, docs) with KEEP / MOVE TO TOOLS / DELETE
- [x] T005 [P] Document intended tools entry points in `tools/README.md` (preview module path, benchmark module path) — not product modes

**Checkpoint**: Flag inventory drafted (still must pass Phase 3 review gate before MOVE/DELETE).

---

## Phase 3: User Story 3 — Runtime package vs developer tooling (P3, runs first)

**Goal**: `gazekey/` = product runtime; evaluation/debug/preview outside; obsolete
paths removed; product still calibrates/maps.

**Independent Test**: Post-cleanup gate in `specs/002-gaze-typing-os/quickstart.md` §A.

### Move developer code to `tools/`

- [x] T006 [US3] Move benchmark stack from `gazekey/evaluation/benchmark_*.py`, `failure_analysis.py`, `benchmark_diagnostics.py`, `coverage_diagnostics.py` into `tools/evaluation/` and update imports
- [x] T007 [US3] Move `gazekey/debug/` modules into `tools/debug/` and update imports
- [x] T008 [US3] Move read-only preview orchestration from product default path into `tools/preview/` (e.g. extract from `gazekey/ui/gaze_preview.py` / VK wiring); product MUST NOT require preview mode
- [x] T009 [US3] Relocate developer artifact/summary writers used only for tooling from product modules into `tools/` (keep only in-process runtime state in `gazekey/`); update `gazekey/ui/calibration_finish.py` / `virtual_keyboard.py` imports accordingly
- [x] T010 [US3] Remove product imports of `tools.*` from default `main.py` / `gazekey/ui/virtual_keyboard.py` path; wire tools-only entry for benchmark (e.g. `python -m tools.evaluation` or `tools/run_benchmark.py`)
- [x] T011 [US3] Add tools preview entry (e.g. `python -m tools.preview` or `tools/run_preview.py`) separate from product launch

### Delete / disconnect obsolete typing paths (one task each)

- [x] T012 [US3] Delete package `gazekey/future/` and update any imports/tests
- [x] T013 [US3] Delete package `gazekey/intent/` and update any imports/tests
- [x] T014 [US3] Delete package `gazekey/selection/` and update any imports/tests
- [x] T015 [US3] Delete dormant `gazekey/typing/dwell_selector.py` and update tests (e.g. `tests/test_gaze_typing.py`)
- [x] T016 [US3] Delete dormant `gazekey/typing/gaze_typing_controller.py` and update references
- [x] T017 [US3] Remove dead gaze-typing stubs in `gazekey/ui/virtual_keyboard.py` / missing `GazeLoopController.process_gaze_typing` delegates

### Inventories + STOP/review gate (before broad deletions)

- [x] T018 [P] [US3] Repo-wide cleanup inventory only: list obsolete `archive/` leftovers, unjustified `scripts/`, stale docs/tests in `specs/002-gaze-typing-os/cleanup-inventory.md` with proposed KEEP / MOVE / DELETE (no deletions in this task)
- [x] T019 [US3] **STOP / review gate**: Report completed `env-flag-inventory.md` and `cleanup-inventory.md` (KEEP/MOVE/DELETE) for review; **do not** execute broad flag MOVE/DELETE or archive/script/test/doc deletions until review sign-off is recorded in both inventory files (or a short `specs/002-gaze-typing-os/inventory-review.md`)

### Apply reviewed deletions / moves

- [x] T020 [US3] Apply **reviewed** `env-flag-inventory.md`: MOVE classified flags into tools entrypoints/docs
- [x] T021 [US3] Apply **reviewed** `env-flag-inventory.md`: DELETE classified flags from `gazekey/ui/env_flags.py` and call sites
- [x] T022 [US3] Execute **reviewed** deletions from `cleanup-inventory.md` (one logical group per follow-up if list is long; start with clearly approved dead items)

### Post-cleanup behavior gate

- [x] T023 [US3] Verify `python main.py` launches after cleanup
- [x] T024 [US3] Verify fullscreen calibration still completes (layout unchanged)
- [x] T025 [US3] Verify existing PCA4 fit still produces mapped gaze (observe via tools preview or equivalent without making preview a product mode)
- [x] T026 [US3] Verify keyboard returns to current top-half geometry after calib
- [x] T027 [US3] Verify relocated developer benchmark runs via independent tools entry
- [x] T028 [US3] Record gate results in `specs/002-gaze-typing-os/quickstart-gate-log.md` (pass/fail); **STOP if fail**

**Checkpoint**: US3 done; sealed calib/mapping path healthy; tools benchmark independent.

---

## Phase 4: Foundational — Inject skeleton + hard focus gate (blocks US1/US2)

**Purpose**: Minimal KeyAction path required before focus proof and full dwell.

**⚠️ CRITICAL**: Phase 5 (US1) MUST NOT start until the focus path **passes**
(T034/T035). Documenting a mitigation without a passing rerun is **not** enough.

- [x] T029 [P] Implement `KeyAction` dataclass/enums in `gazekey/typing/key_action.py` per `contracts/key-action.md` / `data-model.md`
- [x] T030 [P] Implement `OsInputAdapter` protocol + `FakeOsInputAdapter` in `gazekey/input/os_input_adapter.py` (no `pynput` in typing/UI)
- [x] T031 Implement `PynputOsInputAdapter` in `gazekey/input/pynput_adapter.py` (`pynput` import only here)
- [x] T032 Implement `ActionDispatcher` in `gazekey/typing/action_dispatcher.py` with `on_action_requested` then inject then `on_action_delivered` semantics
- [x] T033 [P] Add unit tests in `tests/unit/test_key_action_dispatcher.py` for request vs delivered success/failure with fake adapter
- [x] T034 **Hard focus gate**: Run early Windows focus validation per `quickstart.md` §B — after fullscreen calib → top-half keyboard, inject test KeyActions via dispatcher+pynput without restoring focus between characters; record result in `specs/002-gaze-typing-os/focus-validation-log.md`
- [x] T035 If T034 fails: implement **minimal OS/window-only** mitigation in `gazekey/ui/keyboard_layout.py` / `virtual_keyboard.py` (**no layout redesign/reposition**), **rerun** T034, and require **PASS** before Phase 5; record the passing run in `focus-validation-log.md`. If the minimal fix still does not pass, **stop for review** rather than expanding scope automatically; Phase 5 remains blocked until pass

**Checkpoint**: Skeleton works; focus path **passing** (hard gate).

---

## Phase 5: User Story 1 — Type into external app by gaze dwell (P1) 🎯 MVP

**Goal**: Auto-start typing after calibration when a usable mapper / mapped-gaze
state is available (usable = normal calib produced a mapper capable of supplying
mapped gaze for runtime; **not** 001 thresholds); dwell → KeyAction → OS with
on-key circular progress feedback; Pause/Resume; Shift one-shot; Ctrl/Alt
non-OS; mouse optional same path.

**Independent Test**: `quickstart.md` §C short-word gaze typing into Notepad.

**Prerequisite**: T034/T035 focus path **PASS**.

### Dwell engine & session

- [x] T036 [US1] Implement `TypingSession` state (`inactive`/`active`/`paused`) + Shift oneshot arm/clear rules in `gazekey/typing/typing_session.py`
- [x] T037 [US1] Implement dwell engine in `gazekey/typing/dwell_engine.py` (0.9 s dwell, 0.20 s global activation cooldown for keys/Shift/Pause/Resume, same-key lock, 5-frame confirmed leave, **0.25 s key-switch confirmation / hysteresis**; **cancel progress and emit no KeyAction on tracking/mapped-gaze loss during dwell**) per `contracts/dwell-selection.md`
- [x] T038 [P] [US1] Add unit tests in `tests/unit/test_dwell_engine.py` for progress, cancel, lock, 5-frame leave, cooldown, pause drop, **key-switch confirmation (freeze/resume/confirm/wander-cancel)**, **and tracking/mapped-gaze loss cancel (no KeyAction)**
- [x] T039 [P] [US1] Add unit tests in `tests/unit/test_typing_session.py` for Shift clear on Pause / recalib / session reset / termination

### Key set & semantics

- [x] T040 [US1] Update `gazekey/typing/key_semantics.py` (and helpers) so OS-bound set is A–Z, Space, Backspace, Enter; Shift arms oneshot; Ctrl/Alt produce no OS KeyAction
- [x] T041 [US1] In typing controller module e.g. `gazekey/typing/gaze_typing_runtime.py` (new rebuild — not old deleted controller): wire **MappedGazePoint → existing keyboard geometry hit-test** (`gazekey/typing/key_hit_tester.py` / `KeyHitTester`) → `target_key_id` → dwell engine as the **single** key-detection path (reuse current layout geometry as SoT; **do not** create a second/parallel key-detection implementation; **do not** change keyboard geometry or mapping behavior); then map dwell/mouse completions to `KeyAction` + dispatcher publish

### Runtime / UI wiring

- [x] T042 [US1] Wire `gazekey/runtime/gaze_loop.py` to **auto-start typing after calibration when a usable mapper / mapped-gaze state is available** — usable = normal calibration flow has produced a mapper capable of supplying mapped gaze for runtime use (no Enable Typing; no product preview-first; **do not** gate on 001 benchmark thresholds) — and feed each MappedGazePoint through the T041 path only: existing hit-test → `target_key_id` → dwell engine (no parallel key detection)
- [x] T043 [US1] Add Pause/Resume system control (dwell primary + optional mouse) in `gazekey/ui/` / keyboard layout without emitting OS KeyAction; apply activation cooldown
- [x] T044 [US1] Route optional mouse clicks on OS-bound keys through same ActionDispatcher path in `gazekey/ui/virtual_keyboard.py` (or key handler module)
- [x] T045 [US1] Ensure calibration fixation path in `gazekey/ui/calibration_overlay.py` / session never dwell-injects OS input
- [x] T046 [US1] Disconnect in-app `TextBufferController` from the product typing success path; **delete or move** `gazekey/typing/text_buffer.py` (and VK wiring) if it has no justified runtime purpose — do **not** leave it as dormant product code
- [x] T047 [US1] Implement dwell **visual feedback on existing key geometry** in `gazekey/ui/` (e.g. key style + overlay on the hovered key in `keyboard_layout.py` / VK): clearly visible colored border/highlight on the current gaze key; semi-transparent circular progress ring over that key that fills over the full 0.9 s dwell; on full cycle complete selection/activate; on gaze leave before completion hide/reset ring and do not activate; on move to another key restart the same process there; **preserve current keyboard layout/size/position** — no redesign; no retry/prediction/advanced interaction behavior
- [x] T048 [US1] Add simple **non-blocking** UI feedback for **failed OS delivery** (`on_action_delivered` / `OsInjectResult.ok == false`) **and for no usable external typing target**, in `gazekey/ui/virtual_keyboard.py` (or status surface): do not crash; do not corrupt or end the active calibration/mapping session; no retry logic, target-management complexity, or new UI flows

### US1 tests & verification

- [x] T049 [P] [US1] Add automated contract/integration test in `tests/contract/test_typing_dispatch_path.py` (or `tests/integration/`) covering selection → `KeyAction` → `ActionDispatcher` → `FakeOsInputAdapter` for dwell completion, mouse click, paused state (no inject), and delivery failure
- [ ] T050 [US1] Manual short-word gaze test per quickstart §C; confirm SC-001/SC-001a/SC-002/SC-003 notes in `focus-validation-log.md` or `quickstart-gate-log.md` — **PENDING**: live §C still needs operator; upstream mapping accuracy may cause unintended keys (not a dwell/typing regression; do not change calib/mapping in this feature). 0.25 s key-switch confirmation remains as reviewed. T051–T054 proceeded with this still open.

**Checkpoint**: External app receives gaze-typed characters; visuals/Pause/Shift/cooldown/loss/failure feedback behave per spec.

---

## Phase 6: User Story 2 — Preserve external typing-target ownership (P2)

**Goal**: Fullscreen calib + existing top-half keyboard unchanged; focus remains
OS/window concern; continuous inject without per-character focus restore.

**Independent Test**: quickstart layout + continuous inject checks.

- [x] T051 [US2] Confirm/preserve fullscreen calibration presentation and post-calib top-half keyboard geometry in `gazekey/ui/keyboard_layout.py` / VK — **no redesign or reposition**
- [x] T052 [US2] Apply any remaining OS/window-only focus hardening needed after full typing wiring in `gazekey/ui/keyboard_layout.py` / `virtual_keyboard.py` without changing layout geometry
- [x] T053 [US2] Ensure key widgets use focus policies that avoid permanently capturing the external typing target on optional mouse use
- [x] T054 [US2] Re-run focus validation after typing integration; update `specs/002-gaze-typing-os/focus-validation-log.md` (**must remain PASS**)

**Checkpoint**: SC-004 satisfied; layout unchanged.

---

## Phase 7: User Story 4 — Keep calibration and mapping isolated (P4)

**Goal**: Typing consumes mapped gaze only; PCA4 fit/predict responsibilities unchanged.

**Independent Test**: Calib/mapping still work; no typing imports in mapping/calib fit path.

- [x] T055 [P] [US4] Verify `gazekey/calibration/` and `gazekey/mapping/` have no imports of `gazekey.input` or dwell/dispatcher; fix if any crept in
- [x] T056 [P] [US4] Verify typing does not alter `gazekey/mapping/ridge.py` / `config.py` / quality gates for “typing fixes”
- [x] T057 [US4] Confirm mapping benchmark still runnable via tools entry and remains the independent mapping accuracy path (001 metrics)

**Checkpoint**: Mapping foundation isolation intact (Constitution I/V).

---

## Phase 8: Polish & cross-cutting

**Purpose**: Docs, remaining inventories, full quickstart, full regression.

- [x] T058 [P] Update `docs/CURRENT_PIPELINE.md` and `docs/PROJECT_STRUCTURE.md` for product typing path + `tools/` split (no preview-as-product)
- [x] T059 [P] Update `docs/TYPING_CANDIDATE.md` / `README.md` for auto-start when usable mapper available, tools entries, removed flags, dwell visuals
- [x] T060 Remove or rewrite obsolete tests that assert product `_gaze_typing_active() is False` / preview-only product default (e.g. `tests/unit/test_preview_readonly.py`)
- [x] T061 Run full `specs/002-gaze-typing-os/quickstart.md` checklist; record results
- [x] T062 [P] Run focused 002 unit suite: `pytest tests/unit -k "dwell or key_action or os_input or typing_session"`
- [x] T063 Run **full** regression test suite after cleanup and integration: `pytest` (entire `tests/`); record pass/fail summary

**Checkpoint**: Feature ready for `/speckit.implement` completion review / analyze.

---

## Dependencies & Execution Order

### Phase dependencies

```text
Phase1 Setup
  → Phase2 Flag inventory draft
    → Phase3 US3 moves + obsolete path deletes
      → T018 cleanup inventory + T019 STOP/review
        → T020–T022 reviewed deletions
          → T023–T028 post-cleanup gate
            → Phase4 Skeleton + hard focus PASS (T034/T035)
              → Phase5 US1 typing (MVP)
                → Phase6 US2 ownership/layout/focus polish
                → Phase7 US4 isolation verify (can overlap late US1)
                  → Phase8 Polish + full pytest regression
```

- **US1 depends on US3 + Phase 4 focus PASS** (binding)
- **T020–T022 blocked on T019 review sign-off**
- **Phase 5 blocked on T034/T035 PASS** (not merely “mitigation documented”)
- **US2** builds on US1 inject path + layout constraints
- **US4** is verification-heavy; may run checks after US1 wiring
- **Do not** start Phase 5 if T028 or focus gate failed

### Parallel opportunities

- T003 inventory skeleton || T002 tools dirs (Phase 1)
- T006–T008 moves partially parallel if import conflicts managed carefully
- T012–T017 deletes parallel after moves stabilize (prefer sequential if tests break)
- T029–T030 parallel; T033 after T032
- T038–T039 parallel after engines exist
- T049 can proceed once dispatcher + dwell/mouse paths exist
- T055–T056 parallel
- T058–T059 parallel
- T062 || docs once code stable; T063 after integration complete

### Independent tests (per story)

| Story | Independent test |
|-------|------------------|
| US3 | quickstart §A post-cleanup gate |
| US1 | quickstart §C short-word gaze typing + dwell visuals |
| US2 | continuous inject + unchanged top-half geometry |
| US4 | no typing imports in calib/mapping; tools benchmark still maps accuracy |

---

## Implementation Strategy

### MVP first

1. Phase 1–4 complete (cleanup gate + skeleton + **passing** focus)
2. Phase 5 US1 complete → **demo external typing**
3. Then US2/US4/polish + full `pytest`

### Incremental delivery

1. Tools split + inventory review + gate → safe foundation  
2. Inject skeleton + hard focus proof → risk retired early  
3. Full dwell typing + visuals → product value  
4. Ownership polish + isolation verify → harden  
5. Docs + focused units + full regression → done  

---

## Notes

- Each obsolete typing-path deletion is its own task (T012–T017)
- Broad flag/archive/script/test/doc deletions only after **T019 review**
- No keyboard redesign/reposition in any task (including dwell visuals)
- Calibration/PCA4 fit path must remain behaviorally unchanged
- Typing auto-start = after calibration when usable mapper/mapped-gaze is
  available; usable = normal calib produced a runtime-capable mapper — **not**
  001 SC thresholds
- Hard focus gate: validate → minimal OS/window-only fix → rerun → PASS before
  Phase 5; if still fail after minimal fix, stop for review
- Failed delivery / no usable external target: simple non-blocking feedback only
  (T048); no retry/target-management flows
- Mapping accuracy acceptance stays on tools benchmark / 001 — not typing SC
- TextBuffer: delete or move if unjustified — no dormant leftover in product
