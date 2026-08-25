---
description: "Task list for paged large-target keyboard implementation"
---

# Tasks: Paged Large-Target Keyboard

**Input**: Design documents from `/specs/006-paged-large-target-keyboard/`

**Prerequisites**: plan.md (required), spec.md (required), research.md,
data-model.md, contracts/, quickstart.md

**Tests**: Included. plan.md and contracts require pytest for page contents,
relative letter vs arrow geometry, **immediate** hidden-letter isolation after
switch, page-switch does not OS-inject, and Shift armed survives switch.
Live webcam / external-app checks are **USER GATE** (not fully automatable).

**Execution constraint (overrides naive parallel story starts):** Product work
follows plan stages **0 → A → B → C → D**. **Do not** change production
letter layout until Phase 2 **T004** (full-QWERTY baseline record) exists.
Later story phases MUST NOT start until the prior phase checkpoint passes.

**Product condition:** Chin/head support for all practical typing USER GATEs
and SC-006 comparison.

**Hard constraints (do not violate while implementing any task):**

- Do **not** modify GazeFollower, `gazekey/backend/` internals, origin/DPR,
  filtering, or mapping. Practical gains come from larger visible targets.
- Do **not** modify `gazekey/typing/dwell_engine.py` timing (0.9 s / 0.20 s
  cooldown / 5-frame leave / 0.25 s switch).
- Do **not** modify `gazekey/prediction/` ranking, trie, or TypingContext rules.
- Do **not** change keyboard window size/placement (top-of-screen ~62% height).
- Do **not** restore Feature 003-removed chrome (Pause, Preview, language,
  symbols, Ctrl/Alt, typed-text bar, gaze-status text).
- Do **not** treat Feature 004 mapping runs or T060 as this feature’s gate.
- Do **not** retune GazeFollower if SC-006 is not met.
- Page rebuild MUST synchronously unparent previous-page widgets from the
  inspected tree **before** `export_keyboard_layout`. Do **not** rely solely
  on `deleteLater()`.
- No new pip dependencies. Python 3.11 project `.venv` only (not 3.14).

**Path conventions**: Repository root (`gazekey/`, `main.py`, `tests/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: [US1] larger letter targets, [US2] page-switch arrow +
  persistence, [US3] preserve typing/suggestions, [US4] live visible-target
  isolation
- Setup / Foundational / Polish / comparison / cleanup: no story label

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the feature branch and add non-layout scaffolding. Do
**not** rebuild `create_letters_layout` yet.

**Independent Test**: Branch is `006-paged-large-target-keyboard`;
`specs/006-paged-large-target-keyboard/baseline/` exists; stretch constants
are named in `keyboard_layout.py`; product keyboard still shows full QWERTY.

- [ ] T001 Confirm branch `006-paged-large-target-keyboard`, feature dir
  `specs/006-paged-large-target-keyboard/`, and product interpreter is the
  project `.venv` on Python 3.11 (do not run on 3.14)
- [ ] T002 [P] Create `specs/006-paged-large-target-keyboard/baseline/` with a
  short README stating that `full-qwerty-intended-key.md` is recorded at the
  T004 USER GATE **before** layout change and `paged-intended-key.md` is
  recorded after paging, both using the same SC-006 sequence
  `Q T A G Z V / Y P H L B M` (research R10); do not invent baseline
  metrics; `hello` is not this comparison
- [ ] T003 [P] Add named stretch constants `LETTER_PANE_STRETCH = 4` and
  `ARROW_PANE_STRETCH = 1` in `gazekey/ui/keyboard_layout.py` without changing
  `create_letters_layout` yet (research R2; no pixel sizes)

**Checkpoint**: Scaffold ready; production letter layout still full QWERTY

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Record the SC-006 `eval_before` on the **current** full-QWERTY
keyboard, and add page-switch **semantics** that do not change widgets.
**No user-story layout work until T004 exists.**

**⚠️ CRITICAL**: T004 BLOCKS Phase 3+. Do not rebuild the letter area until
the baseline file is on disk.

**Independent Test**: Baseline markdown exists with per-trial intended key,
focused key, correct/incorrect, and a total wrong-focus count for the
fixed SC-006 sequence `Q T A G Z V / Y P H L B M`;
`is_page_switch_action("system:page_right")` is true and
`builds_os_key_action` returns None for that id; `gazekey/backend/` and
`dwell_engine.py` are untouched.

- [ ] T004 **USER GATE (plan Phase 0 / R10)**: On the **current** Feature 003
  full-QWERTY product keyboard, chin/head support on, suggestions unused,
  official GazeFollower calibration unchanged, run intended-key/focus for
  the fixed representative sequence `Q T A G Z V / Y P H L B M` (both
  pages’ letters, all three QWERTY rows) per
  `specs/006-paged-large-target-keyboard/quickstart.md` §A0 and write
  `specs/006-paged-large-target-keyboard/baseline/full-qwerty-intended-key.md`
  (date, condition; for each trial: intended key, focused key,
  correct/incorrect; plus total wrong-focus count). This is a
  **keyboard-surface** comparison, **not** a mapping benchmark. Do **not**
  retune GazeFollower. Do **not** use `hello` here (`hello` is the separate
  SC-003 mixed-page typing USER GATE). Do **not** change production layout
  until this file exists
- [ ] T005 [P] Add `KeyRole.SYSTEM_PAGE_SWITCH`, `PAGE_RIGHT_KEY_ID =
  "system:page_right"`, `PAGE_LEFT_KEY_ID = "system:page_left"`, and
  `is_page_switch_action` in `gazekey/typing/key_semantics.py`; map those ids
  in `role_for_action`; keep `builds_os_key_action` returning None (research
  R5 / `contracts/page-switch.md`)
- [ ] T006 [P] Confirm `gazekey/layout/layout_inspector.py` already treats
  `system:` actions as special (stable `gazeKeyId`); add `system:page_*` to
  the comment near the special-key check if needed; do **not** change
  `gazekey/typing/key_hit_tester.py` hit-test math

**Checkpoint**: Baseline record exists; page-switch ids are semantic-only.
Foundation ready — US1 layout work may begin.

---

## Phase 3: User Story 1 - Type On Larger Letter Targets (Priority: P1) 🎯 MVP

**Goal**: After calibration the product keyboard shows the **left** letter
page with substantially larger visible letters (QWERT / ASDFG / ZXCV plus
Shift and Backspace). Right-page contents exist via the page-rebuild API.
Window size is unchanged. Mapping is unchanged.

**Independent Test**: Launch `python main.py` after calibration; left page
is shown; letters are clearly larger than full-QWERTY; dwell **2–3** visible
left-page letters into Notepad; pytest (including T013 immediate isolation):
`tests/unit/test_paged_keyboard.py tests/unit/test_layout_geometry.py`.

### Tests for User Story 1 (write first; must FAIL before layout rebuild)

- [ ] T007 [P] [US1] Add failing page-content tests in
  `tests/unit/test_paged_keyboard.py`: default `letter_page` is `"left"`;
  visible letters are Q W E R T / A S D F G / Z X C V; Shift and Backspace
  on the third row; Y U I O P, H J K L, B N M absent from export
- [ ] T008 [P] [US1] Add failing relative-geometry tests in
  `tests/unit/test_layout_geometry.py`: arrow width 15–25% of letter-area
  width; mean visible letter-key width **exceeds** letter-area width / 10;
  arrow height spans three letter rows (research R2 / SC-001). **Width is
  the SC-001 area proxy only because letter-row height is unchanged**
  (FR-015 / R9); do not treat width as a separate stretch factor. Assert
  relative fractions only — no pixel constants, no screen-size assumptions

### Implementation for User Story 1

- [ ] T009 [US1] Add `letter_page` (`"left"` | `"right"`, default `"left"`)
  on `VirtualKeyboard` in `gazekey/ui/virtual_keyboard.py` per
  `specs/006-paged-large-target-keyboard/data-model.md` LetterPageState
- [ ] T010 [US1] Rebuild the letter region in
  `gazekey/ui/keyboard_layout.py` `create_letters_layout` as a horizontal
  two-pane layout (research R1 / `contracts/keyboard-layout-006.md`): left
  page `[letters column] | [tall →]`; letters column is three rows with
  Shift | Z X C V | Backspace on row three; bottom row Calibrate | Space |
  Enter stays **full keyboard width**; suggestion bar and chrome unchanged
- [ ] T011 [US1] Add `_create_page_switch_arrow` in
  `gazekey/ui/keyboard_layout.py`: one `objectName="gazeTarget"` widget
  (not `keyboardKey`), `gazeKeyId`/`gazeKeyAction` `system:page_right` on
  the left page with label `→`, visually distinct from letter keys (FR-007);
  stretch pane uses `ARROW_PANE_STRETCH`
- [ ] T012 [US1] Implement right-page letter widgets in
  `gazekey/ui/keyboard_layout.py`: `[tall ←] | [letters column]` with
  Y U I O P / H J K L / Shift B N M Backspace and `system:page_left` (`←`)
- [ ] T013 [US1] Implement `switch_letter_page` in
  `gazekey/ui/virtual_keyboard.py` and a synchronous letter-area rebuild
  helper in `gazekey/ui/keyboard_layout.py` (research R3): `takeAt` /
  unparent previous letter-area widgets so `findChildren` under the export
  root does not see them; drop `letter_keys`, arrow, and previous-page
  `_layout_keys` refs; create destination page; restore Shift visual from
  `TypingSession`; `apply_no_focus_policies`; `update_responsive_sizes`;
  call `export_keyboard_layout` **in the same switch**. Do **not** use
  `clear_layout`/`deleteLater()` as the isolation mechanism. **Checkpoint
  test (required here, not deferred to US4):** in
  `tests/unit/test_paged_keyboard.py`, call `switch_letter_page` then
  **immediately** (no extra wait for `deleteLater`) assert previous-page
  letter ids are absent from `inspect_keyboard_layout` and produce zero
  `hit_test_layout_keys` hits (`contracts/keyboard-layout-006.md` invariant
  3). T013 is not done until this test passes
- [ ] T014 [US1] Extend `update_responsive_sizes` in
  `gazekey/ui/keyboard_layout.py` so the arrow height equals the stacked
  three letter rows including gaps; letter keys keep per-row height;
  Calibrate/Space/Enter row unchanged; do **not** change
  `full_keyboard_size` (0.62) or `position_at_top` (FR-015 / research R9)
- [ ] T015 [US1] Keep existing product tests green after the left-default
  paged layout: `tests/unit/test_layout_geometry.py`,
  `tests/unit/test_focus_and_layout_us2.py` (top-half geometry, no-focus,
  Feature 003 chrome still absent)
- [ ] T016 [US1] **USER GATE**: Visual layout per
  `specs/006-paged-large-target-keyboard/quickstart.md` §A (left page,
  larger letters, one right-side `→` strip, suggestions/Calibrate/chrome
  unchanged). Dwell **2–3 left-page letters** (for example Q, A, Z) into
  focused Notepad through the existing typing path — small live dwell-to-OS
  gate, not the SC-003 `hello` word and not the SC-006 12-letter comparison.
  Run `python -m pytest tests/unit/test_layout_geometry.py
  tests/unit/test_paged_keyboard.py -q` (must include the T013 immediate
  isolation test)

**Checkpoint**: Left page is the product keyboard; letters are larger;
programmatic page rebuild exists; **immediate hidden-letter isolation
passes (T013)**; 2–3 visible left-page letters reach Notepad. Dwell typing
still uses the existing OS path.

---

## Phase 4: User Story 2 - Switch Pages With a Large Arrow (Priority: P1)

**Goal**: Dwelling or clicking the tall arrow switches letter pages without
OS input. Page state persists across minimize/restore and resets to left
after official recalibrate. Dwell timing unchanged.

**Independent Test**: From the left page, dwell on `→` → right page with
left-side `←`; Notepad unchanged; click `←` returns left. Minimize on the
right page and restore still right. Recalibrate then return shows left.

### Tests for User Story 2 (write first; must FAIL before runtime wiring)

- [ ] T017 [P] [US2] Add failing contract tests in
  `tests/contract/test_page_switch_path.py` (mirror
  `tests/contract/test_calibrate_dwell_path.py`): dwell and mouse on
  `system:page_right` / `system:page_left` invoke the page-switch callback;
  `published` is None; `FakeOsInputAdapter` receives no events
- [ ] T018 [P] [US2] Add failing unit tests in
  `tests/unit/test_paged_keyboard.py`: activating the visible arrow switches
  `letter_page`; the new arrow has the opposite id/side/direction; left-page
  letters are gone from export after the switch returns

### Implementation for User Story 2

- [ ] T019 [US2] Handle `SYSTEM_PAGE_SWITCH` in
  `gazekey/typing/gaze_typing_runtime.py` `_handle_activation` like
  Calibrate: optional `on_page_switch` callback, return no `KeyAction`,
  apply existing activation cooldown, `dwell.cancel_progress()`. Do **not**
  edit `gazekey/typing/dwell_engine.py`. Do **not** notify `TypingContext`
- [ ] T020 [US2] Wire `VirtualKeyboard` in `gazekey/ui/virtual_keyboard.py`
  to pass `on_page_switch` into `GazeTypingRuntime` and to call
  `switch_letter_page`; connect the arrow’s `clicked` signal to the same
  callback (mouse parity, FR-020)
- [ ] T021 [US2] Preserve `TypingSession.shift_oneshot_armed` and
  `TypingContext` prefix/epoch across the rebuild in
  `gazekey/ui/virtual_keyboard.py`; after widgets exist, copy Shift
  checked-state and letter case from the session (FR-019)
- [ ] T022 [US2] Keep `letter_page` unchanged across
  `on_minimize_clicked` / `on_restore_clicked` in
  `gazekey/ui/virtual_keyboard.py` (main_content_widget already stays in
  memory — add an explicit regression test in
  `tests/unit/test_paged_keyboard.py`)
- [ ] T023 [US2] Reset `letter_page` to `"left"` only on the explicit
  **return-from-official-recalibrate** path in GazeKey keyboard code
  (`VirtualKeyboard` after `run_official_recalibrate` returns — a dedicated
  post-recalibrate hook / flag). Do **not** implement a blanket reset in
  `showEvent` (minimize/restore and ordinary show must keep the current
  page; FR-009). Do **not** edit `gazekey/backend/startup.py` unless a
  one-line keyboard callback at the existing handoff is proven required
  (research R4 / R7 prefer to avoid that). Add a unit test in
  `tests/unit/test_paged_keyboard.py` that recalibrate-return resets to
  left and that a plain show / restore does **not**
- [ ] T024 [US2] **USER GATE**: `specs/006-paged-large-target-keyboard/quickstart.md`
  §B (dwell `→`, Notepad unchanged, optional click `←`, no double-flip from
  one hold) and §E (minimize/restore keeps page; recalibrate returns left
  via official GazeFollower UI)

**Checkpoint**: Arrow switches pages without typing; persistence matches
FR-009.

---

## Phase 5: User Story 3 - Keep Existing Typing, Suggestions, And External-App Behavior (Priority: P1)

**Goal**: Paging does not regress Feature 002/003: dwell typing into the
focused external app, three suggestion slots, Shift/Backspace/Space/Enter,
and Calibrate remain the same product.

**Independent Test**: Type a mixed-page word (`hello`) with required
switches; Backspace and Space work on both pages; a suggestion still
completes remaining suffix + Space; Calibrate still starts official
GazeFollower recalibration.

### Tests for User Story 3

- [ ] T025 [P] [US3] Extend `tests/unit/test_paged_keyboard.py` so Shift and
  Backspace are exported and hit-testable on **both** pages; suggestion
  slots `suggestion:0..2` remain exported when blank/disabled
- [ ] T026 [P] [US3] Add tests in `tests/unit/test_gaze_typing_runtime.py`:
  arm one-shot Shift, switch page, complete a letter → that letter is
  shifted and Shift does not stay armed
- [ ] T027 [P] [US3] Confirm existing OS dispatch still holds in
  `tests/contract/test_typing_dispatch_path.py` for letters, Space,
  Backspace, and Enter; do **not** change `gazekey/input/` or
  `gazekey/typing/action_dispatcher.py`
- [ ] T028 [P] [US3] Confirm suggestion accept still sends remaining suffix
  + Space in `tests/contract/test_suggestion_typing_path.py` after a
  mixed-page prefix; do **not** modify `gazekey/prediction/`

### Implementation / preservation for User Story 3

- [ ] T029 [US3] Keep Calibrate as `system:calibrate` on both pages in
  `gazekey/ui/keyboard_layout.py`; `tests/contract/test_calibrate_dwell_path.py`
  and `tests/contract/test_recalibrate_official_flow.py` still pass
- [ ] T030 [US3] **USER GATE**: `specs/006-paged-large-target-keyboard/quickstart.md`
  §C (mixed-page `hello` into Notepad — SC-003 end-to-end typing, not the
  SC-006 comparison; suggestions unused; Backspace/Space; Shift survives
  switch) and §D (prefix ≥ 2, possibly mixed-page, accept a suggestion →
  suffix + Space)

**Checkpoint**: Feature 002/003 typing product still works on the paged
surface.

---

## Phase 6: User Story 4 - Only Visible Keys Are Live Targets (Priority: P2)

**Goal**: After a page switch, gaze hits only currently visible enabled
controls. Hidden-page isolation is **already required at T013**; this phase
adds row-clustering, typing-region, and mid-dwell cancel (letter and
suggestion) coverage.

**Independent Test**: T013 isolation still green (T031 regression). Visible
arrow is in `typing_region_rect`. Three letter rows remain distinct.
In-progress letter **or suggestion** dwell cancelled by the arrow does not
type or accept a suggestion.

### Tests for User Story 4

- [ ] T031 [US4] Regression only: the **T013** immediate isolation test in
  `tests/unit/test_paged_keyboard.py` still passes after US2/US3 wiring.
  Do not weaken it or move first-proof of hidden-letter isolation into this
  phase — that checkpoint already belongs to T013 / US1
- [ ] T032 [P] [US4] Extend `tests/unit/test_layout_geometry.py` so
  `typing_region_rect` / `typing_region_from_layout_keys` includes the
  visible `system:page_*` arrow as well as letters, suggestions, Shift,
  Backspace, and Calibrate/Space/Enter
- [ ] T033 [US4] Assert in `tests/unit/test_paged_keyboard.py` that
  left-page letters still form **three distinct rows** in
  `inspect_keyboard_layout` despite the three-row-tall arrow (research R6
  median-height clustering risk)
- [ ] T034 [US4] Add tests in `tests/unit/test_gaze_typing_runtime.py` (and
  `tests/unit/test_paged_keyboard.py` if a live widget tree is required):
  (1) an in-progress **letter** dwell is cancelled on page switch and the
  completed arrow does not publish that letter (spec US4 scenario 4);
  (2) an in-progress **suggestion** dwell is cancelled on page switch and
  `_on_suggestion_accept` / suggestion dispatch does **not** run (spec
  edge case: completed arrow must not accept a suggestion). Do **not**
  modify `gazekey/prediction/` or `dwell_engine.py`

### Implementation for User Story 4

- [ ] T035 [US4] If isolation fails, fix only the rebuild/export order in
  `gazekey/ui/keyboard_layout.py` / `gazekey/ui/virtual_keyboard.py`
  (unparent → drop refs → rebuild → `export_keyboard_layout` before return).
  Do **not** filter stale ids inside `hit_test_layout_keys`. Do **not**
  modify `gazekey/typing/key_hit_tester.py` math

**Checkpoint**: Hidden letters cannot be selected; live QRects match the
visible page when the switch function returns.

---

## Phase 7: Practical typing comparison (SC-006) — not a mapping benchmark

**Purpose**: Compare intended-key/focus on the paged surface against the
**recorded** T004 full-QWERTY file using the **same** 12-letter sequence
and conditions. Constitution II practical interaction test for this
keyboard-surface feature. Independent mapping benchmarks and Feature 004
records stay untouched (FR-016, FR-017). `hello` is **not** this
comparison; it remains the T030 mixed-page typing USER GATE (SC-003).

- [ ] T036 **USER GATE**: Repeat the **same** SC-006 sequence as T004 under
  the same conditions (chin/head support, suggestions unused, official
  GazeFollower calibration unchanged): `Q T A G Z V / Y P H L B M`,
  switching pages as needed on the paged keyboard. Write
  `specs/006-paged-large-target-keyboard/baseline/paged-intended-key.md`
  with the same fields as T004 (per trial: intended key, focused key,
  correct/incorrect; plus total wrong-focus count) per `quickstart.md` §C2.
  Do **not** substitute `hello` for this comparison
- [ ] T037 Compare total wrong-focus count among those 12 visible-letter
  trials to `baseline/full-qwerty-intended-key.md` (SC-006). Record
  improved / unchanged / regressed in the paged file. If not improved,
  **stop and report** — do **not** retune GazeFollower, add smoothing, or
  remap
- [ ] T038 Confirm Feature 004 specs, runs, tags, and mapping-percentage
  gates were not used as acceptance; do not run mapping experiments for
  this feature

**Checkpoint**: SC-006 uses a recorded before/after pair, not memory.
Mapping foundation is unchanged.

---

## Phase 8: Targeted Cleanup (isolation only)

**Purpose**: Unambiguous active path (Principle IX). No unrelated deletions.
This feature must not resume Feature 004 or reopen sealed backend code.

- [ ] T039 Verify `git diff -- gazekey/backend/ gazekey/typing/dwell_engine.py
  gazekey/prediction/` is empty (plan prefers no `startup.py` callback; the
  only allowed exception is an agreed one-line keyboard hook at the existing
  recalibrate handoff)
- [ ] T040 Confirm Feature 003 chrome stays removed
  (`tests/unit/test_focus_and_layout_us2.py`); skip broad archival; do not
  delete, renumber, or rewrite Feature 004

**Checkpoint**: Allowed edit surface is the product keyboard + thin
system-control branch only.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Quiet logging, full pytest, remaining quickstart checks.

- [ ] T041 [P] Add optional verbose `mvp_log` on page switch (from/to page,
  no per-frame spam) in `gazekey/ui/virtual_keyboard.py` (Principle X)
- [ ] T042 Run full `python -m pytest -q` on Python 3.11 `.venv` and fix
  regressions caused by paging (do not weaken isolation or geometry tests)
- [ ] T043 Walk remaining
  `specs/006-paged-large-target-keyboard/quickstart.md` checks not already
  gated (isolation reminder §F / §G). §A0/T004, §C/T030, and §C2/T036
  must already be complete
- [ ] T044 Confirm `full_keyboard_size` / `position_at_top` in
  `gazekey/ui/keyboard_layout.py` and
  `tests/unit/test_focus_and_layout_us2.py` still pin the keyboard to the
  top ~62% of available screen

**Checkpoint**: Feature 006 is testable from `tasks.md` + `quickstart.md`
without mapping retune.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup. **T004 BLOCKS all layout
  stories**
- **US1 (Phase 3)**: Depends on T004 + T005/T006. Plan Phase A
- **US2 (Phase 4)**: Depends on US1 page-rebuild API (T013). Plan Phase B+C
- **US3 (Phase 5)**: Depends on US1 layout + US2 switch. Plan Phase D
  product preservation
- **US4 (Phase 6)**: Depends on US2 switch. Immediate hidden-letter
  isolation is a **T013 / US1 checkpoint**; this phase is extra geometry
  and dwell-cancel coverage, plus T031 regression
- **Practical comparison (Phase 7)**: Depends on US1–US3 live path + T004
  baseline file
- **Cleanup / Polish (Phases 8–9)**: Depend on desired stories being
  complete

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational. No other story required. MVP
- **User Story 2 (P1)**: Needs US1 rebuild API so the arrow has a page to
  switch to
- **User Story 3 (P1)**: Needs US1+US2 so mixed-page words and suggestions
  can be checked
- **User Story 4 (P2)**: Needs US2 switch for dwell-cancel cases; T013
  isolation must already be green from US1

### Within Each User Story

- Tests (where listed) MUST be written and FAIL before the matching
  implementation
- Models/state (`letter_page`) before layout widgets
- Layout rebuild before runtime callback
- Runtime callback before persistence hooks
- Story complete before moving to the next plan phase

### Parallel Opportunities

- T002 / T003 after T001
- T005 / T006 in parallel with each other (not with T004’s live session,
  but they may proceed while T004 is being recorded)
- T007 / T008 before any `create_letters_layout` rebuild
- T017 / T018 after US1 checkpoint
- T025 / T026 / T027 / T028 after US2 checkpoint
- T032 / T033 after T013 isolation exists (T031 is regression only)
- T041 in parallel with T042 only if logging does not churn failing tests

---

## Parallel Example: User Story 1

```text
# After T004 baseline exists, launch failing tests together:
Task: "Add failing page-content tests in tests/unit/test_paged_keyboard.py"
Task: "Add failing relative-geometry tests in tests/unit/test_layout_geometry.py"

# After tests exist, implement sequentially (same files):
Task: "Add letter_page on VirtualKeyboard"
Task: "Rebuild two-pane create_letters_layout"
Task: "Add page-switch arrow widget"
Task: "Implement synchronous switch_letter_page + export + immediate isolation test"
```

---

## Parallel Example: User Story 2

```text
Task: "Contract tests in tests/contract/test_page_switch_path.py"
Task: "Unit tests for arrow switch in tests/unit/test_paged_keyboard.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2 including **T004 baseline USER GATE**
3. Complete Phase 3: User Story 1 (paged left layout + rebuild API)
4. **STOP and VALIDATE**: T013 immediate isolation pytest; T016 visual +
   2–3 left-page letters into Notepad
5. Demo larger left-page letters (right-page letters via test API)

### Incremental Delivery

1. Setup + Foundational (T004 record) → safe to change layout
2. US1 → larger left-page letters → demo
3. US2 → arrow switch + persistence → demo mixed alphabet
4. US3 → confirm typing/suggestions/Calibrate → demo `hello` (SC-003)
5. US4 → typing-region, three-row clustering, letter **and suggestion**
   dwell-cancel; T013 isolation remains a regression (T031)
6. Phase 7 SC-006 comparison of `Q T A G Z V / Y P H L B M` against the
   T004 file (not `hello`)
7. Cleanup + full pytest

### Parallel Team Strategy

This is a single-surface keyboard change. Prefer **one implementer** through
US1–US2 (same files: `keyboard_layout.py`, `virtual_keyboard.py`). A second
person can own contract tests (`test_page_switch_path.py`) once the rebuild
API exists. Immediate isolation is part of T013, not a later-only US4 proof.

---

## Notes

- [P] tasks = different files, no incomplete dependencies
- [Story] label maps task to US1–US4 in spec.md
- Do not encode pixel sizes or a stretch factor in spec/tests beyond the
  15–25% arrow band and mean-letter > letter-area/10
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Avoid: GazeFollower retune, dwell redesign, prediction edits, Feature 004
  reuse as a live gate, `deleteLater()`-only page isolation
