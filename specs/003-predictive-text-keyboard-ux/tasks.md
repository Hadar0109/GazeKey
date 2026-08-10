# Tasks: Predictive Text & Keyboard UX

**Input**: Design documents from `specs/003-predictive-text-keyboard-ux/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`; Constitution v1.3.0

**Tests**: Included per plan Testing section and research R1/R2/R5 (word
provider quality smoke, TypingContext delivery-only updates, suggestion
dispatch epoch + Shift casing regression, layout geometry). Mapping benchmark
remains independent (`001` / tools) — no mapping retune tasks.

**Organization**: Phases follow **plan binding order** (UI cleanup → geometry
gate → prediction core → suggestion gaze/dispatch → integration). User-story
labels map to `spec.md` US1–US4. **US3 (keyboard UI) runs before US1** despite
P2 priority (plan Phase A).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no incomplete blockers)
- **[Story]**: [US1]…[US4] on story-phase tasks only

---

## Phase 1: Setup

**Purpose**: Scaffold prediction package without changing product behavior yet.

- [X] T001 Confirm branch `003-predictive-text-keyboard-ux` and feature dir
  `specs/003-predictive-text-keyboard-ux/`
- [X] T002 Create `gazekey/prediction/` package layout with `__init__.py`,
  `word_provider.py` (Protocol stub), `trie_provider.py` (stub),
  `typing_context.py` (stub), `suggestion_dispatch.py` (stub), and
  `gazekey/prediction/data/` per `specs/003-predictive-text-keyboard-ux/plan.md`
- [X] T003 [P] Add `gazekey/prediction/data/README.md` placeholder documenting
  that `words_en.txt` MUST name source URL/name, license, and attribution
  before bundling (research R1) — do not ship an unlicensed list

**Checkpoint**: `gazekey/prediction/` exists; no product UI changes yet.

---

## Phase 2: User Story 3 — Simplified keyboard & geometry gate (P2, runs first)

**Goal**: Remove inactive product chrome; redistribute space; keep/fix
suggestion bar (fully visible); preserve `tools.preview`; geometry/hitboxes
synchronized (FR-008, FR-008a–c, FR-011).

**Independent Test**: `specs/003-predictive-text-keyboard-ux/quickstart.md` §A;
`pytest tests/unit/test_layout_geometry.py tests/test_keyboard_geometry_targets.py`.

### Product UI removals (one logical group; clean wiring)

- [X] T004 [US3] Remove Pause button and product pause UI wiring from
  `gazekey/ui/keyboard_layout.py` and `gazekey/ui/virtual_keyboard.py`; leave
  product typing session active when mapper available; remove or gate product
  dwell path to `PAUSE_RESUME` (research R9); update tests that assume
  `pause_resume_btn`
- [X] T005 [US3] Remove product Preview button and product-only wiring from
  `gazekey/ui/keyboard_layout.py` / `gazekey/ui/virtual_keyboard.py`; **preserve**
  `python -m tools.preview`, `GazeLoopController.process_gaze_preview`, and
  shared preview runtime (FR-008b / research R8)
- [X] T006 [US3] Remove language toggle (`lang_btn`) and product wiring from
  `gazekey/ui/keyboard_layout.py` / `gazekey/ui/virtual_keyboard.py`
- [X] T007 [US3] Remove symbols toggle, symbols layout path
  (`create_symbols_layout` / `switch_layout`), and Ctrl/Alt keys from product
  letters layout in `gazekey/ui/keyboard_layout.py`; clean
  `gazekey/ui/virtual_keyboard.py` handlers
- [X] T008 [US3] Remove typed-text display bar (`text_display` /
  `create_text_display`) from `gazekey/ui/keyboard_layout.py` and replace any
  delivery-error UX that depended on it with `mvp_log` verbose (research R10)
  in `gazekey/ui/virtual_keyboard.py`
- [X] T009 [US3] Remove gaze-status chrome text (`camera_status_label` /
  `Gaze active | …%`) from product control bar in `gazekey/ui/keyboard_layout.py`
  and stop updating it from `gazekey/runtime/gaze_loop.py`

### Layout redistribution + suggestion bar geometry

- [X] T010 [US3] Redistribute keyboard layout in `gazekey/ui/keyboard_layout.py`
  to the research **R7 acceptance layout** / `contracts/keyboard-layout-003.md`:
  no empty dead gaps; suggestion bar fully visible (not clipped); reclaimed
  space redistributed appropriately to active letter/editing keys; keep Calibrate
  + window chrome. Key enlargement is a layout/usability goal, **not** a
  mapping-accuracy requirement.
- [X] T011 [US3] Create **exactly three** suggestion slots with
  `objectName="gazeTarget"` and stable `key_id`s `suggestion:0`…`suggestion:2`
  in `gazekey/ui/keyboard_layout.py` so they export via
  `gazekey/layout/layout_inspector.py`. Slots MUST have **fixed positions and
  fixed geometry**; when unlabeled they stay blank/disabled (not dwellable). Do
  **not** resize/reflow the bar by suggestion count (placeholders OK until US1
  wires prediction labels).
- [X] T012 [US3] Update **only** layout export / semantic-row / hit-test geometry
  alignment in `gazekey/ui/virtual_keyboard.py` (and related layout helpers) so
  the simplified surface stays synchronized with `inspect_keyboard_layout` /
  `hit_test_layout_keys`. **MUST NOT** change calibration strategy, calibration
  targets, PCA4 fit/predict, `gazekey/mapping/config.py`, or mapping parameters
  to compensate for UI redesign.
- [X] T013 [US3] Extend `tests/unit/test_layout_geometry.py` for fixed
  suggestion-slot hit-test coverage (three slots always present; disabled slots
  not dwellable) and absence of removed controls; fix
  `tests/unit/test_focus_and_layout_us2.py` / other UI tests broken by removals
- [X] T014 [US3] Run automated geometry gate:
  `pytest tests/unit/test_layout_geometry.py tests/test_keyboard_geometry_targets.py -q`
  and record pass/fail in
  `specs/003-predictive-text-keyboard-ux/quickstart-gate-log.md` (create if
  needed); **STOP if fail**. Automated tests do **not** claim live webcam/OS
  typing passed.
- [X] T015 [US3] **USER GATE**: Ask the user to run/confirm
  `python -m tools.preview` (preview without product Preview button) and visual
  check of the redesigned keyboard (quickstart §A / FR-008b). Record result in
  `specs/003-predictive-text-keyboard-ux/quickstart-gate-log.md`. **STOP and wait
  for user confirmation before Phase 3.**

**Checkpoint**: Simplified product keyboard; geometry tests green; **user
confirmed** tools preview + visual layout. Prediction not required yet.

---

## Phase 3: Foundational — Prediction core (blocks US1 / US2 / US4)

**Purpose**: Licensed word list, trie top-3 provider, and delivery-only
`TypingContext` — shared by suggestion stories.

**⚠️ CRITICAL**: US1/US2/US4 MUST NOT start until T020–T023 pass.

- [X] T016 Choose and document a clearly redistributable English word list
  (public-domain / CC0 / MIT / BSD / Apache-2.0 or equivalent); write provenance
  into `gazekey/prediction/data/README.md` (research R1) — **reject** unclear
  license sources
- [X] T017 Add `gazekey/prediction/data/words_en.txt` from the chosen licensed
  source (frequency-ordered; ~20k–50k target)
- [X] T018 Implement `WordProvider` Protocol in
  `gazekey/prediction/word_provider.py` per
  `specs/003-predictive-text-keyboard-ux/contracts/word-provider.md` (abstraction
  for UI/typing; future personalized providers allowed without implementing them
  here)
- [X] T019 Implement `TrieWordProvider` in `gazekey/prediction/trie_provider.py`
  with **efficient top-3 frequency retrieval** (research R2: not naive
  full-subtree collect-then-sort); min prefix length ≥2 returns `[]` for shorter;
  load/`suggest` failures MUST raise or return safely so callers can fail open
  (FR-012) — do not crash the product
- [X] T020 [P] Add `tests/unit/test_word_provider.py`: API rules (`hel` matches,
  `h`→`[]`, `zzzz`→`[]`, `len<=3`) plus deterministic **quality smoke** for
  common prefixes (e.g. `th`, `he`, `an`, `in`, `wh`); plus fail-open cases
  (missing word file / `suggest` exception handled by caller contract)
- [X] T021 Implement `TypingContext` in `gazekey/prediction/typing_context.py`
  per `contracts/typing-context.md` / data-model: update only on
  `on_action_delivered` with `ok=True`; no post-batch `clear_prefix()` for
  suggestion accept
- [X] T022 [P] Add `tests/unit/test_typing_context.py`: letter append, backspace,
  Space clears, ENTER clears, failed inject leaves prefix unchanged, suggestion
  suffix+Space clears via Space delivery only
- [X] T023 Wire `TypingContext` and a single composition-root `WordProvider`
  instance (concrete `TrieWordProvider` constructed **once** in setup, typed as
  `WordProvider`) in `gazekey/ui/virtual_keyboard.py` (or thin factory). UI and
  typing MUST import `WordProvider` only — **not** `TrieWordProvider` /
  trie internals. Refresh suggestions from delivery path only (not gaze frames).

**Checkpoint**: Provider + context unit tests pass; ready for suggestion UI.
  **Do not start US1 until T015 USER GATE confirmed.**

---

## Phase 4: User Story 1 — Complete a word from suggestions (P1) 🎯 MVP

**Goal**: Show ≤3 suggestions from prefix; gaze/mouse accept dispatches
suffix + Space via existing KeyAction path (FR-001–FR-005).

**Independent Test**: Quickstart §B–C; contract path with fake adapter.

- [X] T024 [US1] Implement `suggestion_dispatch` in
  `gazekey/prediction/suggestion_dispatch.py`: compute suffix; dispatch sequential
  CHAR + Space through `ActionDispatcher`; stop on first delivery failure;
  Shift-armed + non-empty lowercase prefix → clear Shift, do **not** apply to
  suffix (research R5)
- [X] T025 [P] [US1] Add `tests/unit/test_suggestion_dispatch.py`: `hel`+`hello`
  → `lo `; epoch stale → no dispatch; Shift-armed + prefix `hel` → lowercase
  `lo ` and Shift cleared (**no** `helLo`); partial failure leaves context
  consistent with delivered chars
- [X] T026 [US1] Activate suggestion bar UI: keep **three fixed-geometry** slots;
  label enabled slots from `WordProvider.suggest` (not `TrieWordProvider`);
  unused slots blank/disabled (not dwellable); **no** resize/reflow by count —
  in `gazekey/ui/keyboard_layout.py` / `gazekey/ui/virtual_keyboard.py` on
  `TypingContext` change (`prefix_epoch`)
- [X] T027 [US1] Extend `gazekey/typing/key_semantics.py` and
  `gazekey/typing/gaze_typing_runtime.py` so `suggestion:0..2` are dwellable
  **only when enabled**; on fire, call suggestion accept with epoch guard
  (`contracts/suggestion-selection.md`). Typing modules MUST NOT import trie
  internals.
- [X] T028 [US1] Wire mouse click on suggestion buttons to the same accept path
  as dwell in `gazekey/ui/virtual_keyboard.py` (parity with keys)
- [X] T029 [US1] Add `tests/contract/test_suggestion_typing_path.py`: dwell/mouse
  suggestion → fake adapter receives suffix+Space; empty/disabled slot not
  dwellable
- [X] T030 [US1] **USER GATE**: Ask the user to run/confirm end-to-end suggestion
  MVP (quickstart §C): type `hel`, dwell a suggestion, confirm external app
  shows completed word + Space. Automated tests MUST NOT claim live webcam or
  external-app typing passed. **STOP and wait for user confirmation before
  Phase 5.**

**Checkpoint**: US1 MVP — suggestions appear and complete words via OS path
  (**user-confirmed** live path).

---

## Phase 5: User Story 2 — Keep typing when suggestions unused (P1)

**Goal**: Fail open; character typing works with empty or ignored suggestions
(FR-007, FR-012).

**Independent Test**: Quickstart §D; existing typing contract tests still pass.

- [X] T031 [US2] Ensure blank/disabled suggestion slots are not dwellable and do
  not block key hit-testing in `gazekey/typing/gaze_typing_runtime.py` /
  layout export; on provider/load/`suggest` failure, clear labels and disable
  all three slots (fail open; FR-012) without raising into the gaze loop
- [X] T032 [US2] Verify ignore-suggestions path: typing letters/Space/Backspace/
  Enter still uses unchanged KeyAction → dispatcher → adapter path in
  `gazekey/ui/virtual_keyboard.py` / `gazekey/typing/gaze_typing_runtime.py`
- [X] T033 [P] [US2] Extend or add regression coverage in
  `tests/contract/test_typing_dispatch_path.py` (and/or
  `tests/unit/test_gaze_typing_runtime.py` / `tests/unit/test_word_provider.py`)
  proving OS-bound keys still deliver when suggestions empty/ignored **and**
  when provider load/`suggest` fails (fail open)
- [X] T034 [US2] **USER GATE**: Ask the user to confirm quickstart §D (type
  key-by-key ignoring suggestions; non-dictionary prefix → blank slots; typing
  still works). Automated tests MUST NOT substitute for this confirmation.

**Checkpoint**: Prediction never blocks normal typing — **user-confirmed** (§D).

---

## Phase 6: User Story 4 — Consistent suggestion behavior (P2)

**Goal**: Prefix/suggestions stay coherent across type, delete, word boundary,
and accept (FR-006, FR-006a, SC-003).

**Independent Test**: Quickstart §B + §E; unit epoch/context tests.

- [X] T035 [US4] On every successful delivery that changes `TypingContext`,
  refresh suggestion set synchronously on UI thread in
  `gazekey/ui/virtual_keyboard.py` (no gaze-frame refresh; research R6)
- [X] T036 [US4] Cancel in-progress suggestion dwell when `prefix_epoch` changes
  mid-dwell in `gazekey/typing/gaze_typing_runtime.py` (research R6)
- [X] T037 [P] [US4] Add/extend unit tests for: type→suggest update, backspace→
  shorten, Space→clear suggestions, accept→empty prefix via Space delivery,
  stale epoch accept rejected (`tests/unit/test_typing_context.py` and/or
  `tests/unit/test_suggestion_dispatch.py`)
- [X] T038 [US4] **USER GATE**: Ask the user to run/confirm the scripted
  consistency sequence (quickstart §B/§E): prefix, backspace, accept/ignore,
  Space — suggestions always match internal `TypingContext`. Automated tests
  MUST NOT claim live webcam behavior passed.

**Checkpoint**: No stale suggestion accepts; context matches delivered text —
  **user-confirmed** (§B/§E).

---

## Phase 7: Polish & cross-cutting

**Purpose**: Integration validation; docs; modularity; full regression; no
mapping changes.

- [X] T039 [P] Update `README.md` and/or `docs/PROJECT_STRUCTURE.md` briefly for
  prediction package + simplified product keyboard (no mapping retune)
- [X] T040 [P] Update `docs/TYPING_CANDIDATE.md` note that 003 adds prediction
  downstream of mapped gaze without changing PCA4 constants
- [X] T041 Run Feature 003 automated sweep from quickstart:
  `pytest tests/unit/test_typing_context.py tests/unit/test_word_provider.py
  tests/unit/test_suggestion_dispatch.py tests/unit/test_layout_geometry.py
  tests/contract/test_typing_dispatch_path.py
  tests/contract/test_suggestion_typing_path.py -q`
- [X] T042 **USER GATE**: Ask the user to execute remaining live quickstart.md
  sections A–G as needed; append results to
  `specs/003-predictive-text-keyboard-ux/quickstart-gate-log.md`. Automated
  suites MUST NOT be used to claim webcam gaze or external-app typing passed.
- [X] T043 Confirm `gazekey/mapping/config.py` and mapping benchmarks were not
  modified for this feature (SC-007)
- [X] T044 [P] Architectural modularity check: ensure `gazekey/ui/` and
  `gazekey/typing/` do **not** import `TrieWordProvider` or
  `gazekey.prediction.trie_provider` internals (depend on `WordProvider` only);
  add a small unit/static test under `tests/unit/test_prediction_modularity.py`
  (or equivalent grep/assert in suite)
- [X] T045 Full-project regression: run `pytest -q` at repo root; feature is
  **not complete** until the existing project suite still passes

**Checkpoint**: T042 USER GATE + T045 green + Phase 8/9 USER GATEs confirmed —
  Feature 003 complete.

---

## Phase 8: Recalibration target follow-up (FR-008d)

**Purpose**: Move Calibrate/Recalibrate to a large bottom-row gaze recovery
target left of Space; slim top chrome; keep QWERTY balanced. **No** mapping/
PCA4/calibration retune. Larger target = recovery tolerance only.

**Independent Test**: quickstart §H; extended `test_layout_geometry.py`;
`pytest -q`.

- [X] T046 Move orange Calibrate/Recalibrate from the top control bar to the
  bottom keyboard row **left of Space** in `gazekey/ui/keyboard_layout.py`; keep
  `objectName="gazeTarget"` and stable `gazeKeyId`/`key_id` `system:calibrate`;
  slim top chrome to minimize/close only
- [X] T047 Make the recalibration button **noticeably larger** than a normal
  letter key (prefer wider stretch; increase height when vertical space allows);
  reduce/center Space and slightly shrink Enter as needed for a balanced bottom
  row in `gazekey/ui/keyboard_layout.py` `update_responsive_sizes` /
  `create_letters_layout`; reclaim vertical space from the slimmed top chrome
  into letter-key rows; preserve QWERTY
- [X] T048 Synchronize layout export / hit-test / semantic-row geometry only
  (FR-011) so visible Calibrate bounds remain dwellable via
  `inspect_keyboard_layout` / `hit_test_layout_keys`; **MUST NOT** change
  calibration strategy, targets, PCA4, `gazekey/mapping/config.py`, or
  benchmarks
- [X] T049 [P] Extend `tests/unit/test_layout_geometry.py` (and related UI tests
  if needed): Calibrate absent from top chrome; present on bottom row left of
  Space; `system:calibrate` exported and hit-testable; Calibrate rect area
  strictly larger than a typical letter key; removed-chrome assertions still hold
- [X] T050 Run `pytest tests/unit/test_layout_geometry.py
  tests/test_keyboard_geometry_targets.py -q` then full `pytest -q`; record
  results in `specs/003-predictive-text-keyboard-ux/quickstart-gate-log.md`
- [X] T051 **USER GATE**: Ask the user to confirm quickstart §H — (1) recalibrate
  clearly larger/easier to target, (2) bottom row layout correct, (3) gaze
  typing still works, (4) no important UI clipped/misaligned. **STOP and wait**
  for confirmation. Automated tests MUST NOT claim live webcam verification.
- [X] T052 Confirm again `gazekey/mapping/config.py` was not modified for this
  follow-up

**Checkpoint**: Bottom-row large Calibrate live; geometry green; **user
confirmed** §H.

---

## Phase 9: Typing-region geometry consistency (suggestion bar included)

**Purpose**: Make layout-export `typing_region_rect` mean the full interactive
gaze-typing surface (suggestions + keys + Recalibrate). Prefer union of
exported gaze-target rects. **No** mapping stretch/compensation; **no** PCA4/
calib-target/config changes. Geometry consistency first — live reachability is
a USER GATE, not claimed by this task alone.

- [X] T053 Derive product `typing_region_rect` from exported layout gaze targets
  (or equivalent union of suggestion bar + keyboard widget) in
  `gazekey/typing/gaze_ui_mapper.py` / `gazekey/ui/keyboard_layout.py` so the
  region includes fixed `suggestion:0..2` (even when disabled), letter/editing
  keys, and bottom Recalibrate/Space/Enter; keep calibration on
  `letter_keys_region_rect` / existing targets unchanged
- [X] T054 [P] Extend `tests/unit/test_layout_geometry.py` proving
  `typing_region_rect` contains suggestion-row centers and intended product
  gaze targets; region does not shrink when slots are blank/disabled
- [X] T055 Run geometry tests + full `pytest -q`; confirm
  `gazekey/mapping/config.py` untouched; record in
  `specs/003-predictive-text-keyboard-ux/quickstart-gate-log.md`
- [X] T056 **USER GATE**: Ask the user to test live whether gaze can reach the
  suggestion row in the product. Automated tests MUST NOT claim this fixed live
  mapping. **STOP and wait** for confirmation. Do not claim this change fixes
  live mapping unless the user verifies it.

**Checkpoint**: Region metadata consistent; **user-confirmed** live suggestion
reachability (T056).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Immediate
- **Phase 2 (US3)**: After Setup — **blocks** prediction wiring that assumes
  suggestion gazeTargets / simplified chrome
- **Phase 3 (Foundational prediction)**: After US3 geometry gate (T014) —
  **blocks** US1 / US2 / US4
- **Phase 4 (US1)**: After Phase 3 — MVP
- **Phase 5 (US2)**: After US1 (uses suggestion UI empty-slot behavior); can
  overlap late US1 testing
- **Phase 6 (US4)**: After US1 (needs accept + context); builds on US2 refresh
  rules
- **Phase 7 (Polish)**: After desired stories complete
- **Phase 8 (Recalibrate layout follow-up)**: After Phase 7 automated work;
  **USER GATE T051** before closing Feature 003

### User Story Dependencies

| Story | Depends on | Notes |
|-------|------------|-------|
| US3 | Setup | Runs first (plan Phase A) |
| US1 | US3 + Prediction core | MVP |
| US2 | US1 (suggestion slots exist) | Fail-open / regression |
| US4 | US1 (+ US2 refresh wiring) | Consistency / epoch |

### Parallel Opportunities

- T006–T008 are **sequential** (same UI files; no `[P]`)
- T020 ∥ T022 after provider/context implemented
- T025 ∥ T029 after dispatch exists
- T033 ∥ T037 in polish-adjacent testing
- T039 ∥ T040 documentation
- T044 ∥ T041 after implementation stable

### Within stories

- Geometry gate (T014) + **USER GATE T015** before prediction core / US1
- Word list license (T016) before shipping `words_en.txt` (T017)
- Provider before UI refresh; TypingContext before accept path
- Shift casing regression (T025) before declaring US1 done
- **USER GATE T030** before Phase 5
- Full regression **T045** required for completion

### USER GATES (manual / live)

| Task | Gate |
|------|------|
| T015 | Tools preview + visual keyboard after geometry redesign |
| T030 | First end-to-end suggestion MVP (webcam + external app) |
| T034 | Typing with suggestions ignored / empty |
| T038 | Consistency sequence vs `TypingContext` |
| T042 | Remaining live quickstart A–G |
| T051 | Bottom-row large Calibrate recovery target (quickstart §H) |
| T056 | Live gaze reachability of suggestion row after typing_region_rect update |

Implementer MUST stop and ask the user to run/confirm these before continuing
past the gate. Automated tests do not satisfy USER GATE criteria.

---

## Parallel Example: Prediction core

```text
# After T019 + T021:
Task: "Add tests/unit/test_word_provider.py (API + quality smoke)"
Task: "Add tests/unit/test_typing_context.py (delivery-only updates)"
```

## Parallel Example: US1

```text
# After T024:
Task: "tests/unit/test_suggestion_dispatch.py (suffix, epoch, Shift casing)"
# After T027:
Task: "tests/contract/test_suggestion_typing_path.py"
```

---

## Implementation Strategy

### MVP First (US3 geometry + US1 suggestions)

1. Phase 1 Setup
2. Phase 2 US3 — stop at geometry gate
3. Phase 3 Prediction core
4. Phase 4 US1 — **STOP and validate** quickstart §B–C
5. Demo: type `hel`, accept `hello` → `hello ` in Notepad

### Incremental Delivery

1. US3 → cleaner keyboard + geometry proof
2. US1 → predictive completion MVP
3. US2 → fail-open confidence
4. US4 → stale/consistency hardening
5. Polish → quickstart A–G + docs

### Suggested MVP scope

**US3 geometry gate (through T015 USER GATE) + Phase 3 + US1 (through T030 USER
GATE)**. US2/US4 + T044/T045 before merge.

---

## Notes

- Do **not** retune calibration/mapping for UI or prediction issues
- `<1 ms` suggest / `<200 ms` trie build = design targets, not SC gates
- No post-batch `clear_prefix()` after suggestion accept
- Three suggestion slots: fixed geometry; blank/disabled when unused
- UI/typing → `WordProvider` only; compose `TrieWordProvider` once at setup
- Commit after each task or logical group
- Avoid vague tasks; keep file paths exact
- **USER GATE** tasks require explicit user confirmation before continuing
