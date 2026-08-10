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

- [ ] T001 Confirm branch `003-predictive-text-keyboard-ux` and feature dir
  `specs/003-predictive-text-keyboard-ux/`
- [ ] T002 Create `gazekey/prediction/` package layout with `__init__.py`,
  `word_provider.py` (Protocol stub), `trie_provider.py` (stub),
  `typing_context.py` (stub), `suggestion_dispatch.py` (stub), and
  `gazekey/prediction/data/` per `specs/003-predictive-text-keyboard-ux/plan.md`
- [ ] T003 [P] Add `gazekey/prediction/data/README.md` placeholder documenting
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

- [ ] T004 [US3] Remove Pause button and product pause UI wiring from
  `gazekey/ui/keyboard_layout.py` and `gazekey/ui/virtual_keyboard.py`; leave
  product typing session active when mapper available; remove or gate product
  dwell path to `PAUSE_RESUME` (research R9); update tests that assume
  `pause_resume_btn`
- [ ] T005 [US3] Remove product Preview button and product-only wiring from
  `gazekey/ui/keyboard_layout.py` / `gazekey/ui/virtual_keyboard.py`; **preserve**
  `python -m tools.preview`, `GazeLoopController.process_gaze_preview`, and
  shared preview runtime (FR-008b / research R8)
- [ ] T006 [P] [US3] Remove language toggle (`lang_btn`) and product wiring from
  `gazekey/ui/keyboard_layout.py` / `gazekey/ui/virtual_keyboard.py`
- [ ] T007 [P] [US3] Remove symbols toggle, symbols layout path
  (`create_symbols_layout` / `switch_layout`), and Ctrl/Alt keys from product
  letters layout in `gazekey/ui/keyboard_layout.py`; clean
  `gazekey/ui/virtual_keyboard.py` handlers
- [ ] T008 [P] [US3] Remove typed-text display bar (`text_display` /
  `create_text_display`) from `gazekey/ui/keyboard_layout.py` and replace any
  delivery-error UX that depended on it with `mvp_log` verbose (research R10)
  in `gazekey/ui/virtual_keyboard.py`
- [ ] T009 [US3] Remove gaze-status chrome text (`camera_status_label` /
  `Gaze active | …%`) from product control bar in `gazekey/ui/keyboard_layout.py`
  and stop updating it from `gazekey/runtime/gaze_loop.py`

### Layout redistribution + suggestion bar geometry

- [ ] T010 [US3] Redistribute keyboard layout in `gazekey/ui/keyboard_layout.py`
  per research R7 / `contracts/keyboard-layout-003.md`: no empty gaps; enlarge
  letter/editing key targets where appropriate; ensure suggestion bar is fully
  visible (not clipped); keep Calibrate + window chrome
- [ ] T011 [US3] Make suggestion slots use `objectName="gazeTarget"` and stable
  `key_id`s `suggestion:0`…`suggestion:2` in `gazekey/ui/keyboard_layout.py` so
  they export via `gazekey/layout/layout_inspector.py` (may still show
  placeholders until US1 wires prediction)
- [ ] T012 [US3] Update semantic-row / layout-export assumptions in
  `gazekey/ui/virtual_keyboard.py` (and any calibration-row helpers) for the
  simplified surface; **do not** change `gazekey/mapping/config.py`
- [ ] T013 [US3] Extend `tests/unit/test_layout_geometry.py` for suggestion-slot
  hit-test coverage and absence of removed controls; fix
  `tests/unit/test_focus_and_layout_us2.py` / other UI tests broken by removals
- [ ] T014 [US3] Run geometry gate: `pytest tests/unit/test_layout_geometry.py
  tests/test_keyboard_geometry_targets.py -q` and record pass/fail in
  `specs/003-predictive-text-keyboard-ux/quickstart-gate-log.md` (create if
  needed); **STOP if fail**
- [ ] T015 [US3] Verify `python -m tools.preview` still launches and preview works
  without product Preview button; note result in
  `specs/003-predictive-text-keyboard-ux/quickstart-gate-log.md`

**Checkpoint**: Simplified product keyboard; geometry tests green; tools preview
preserved. Prediction not required yet.

---

## Phase 3: Foundational — Prediction core (blocks US1 / US2 / US4)

**Purpose**: Licensed word list, trie top-3 provider, and delivery-only
`TypingContext` — shared by suggestion stories.

**⚠️ CRITICAL**: US1/US2/US4 MUST NOT start until T020–T023 pass.

- [ ] T016 Choose and document a clearly redistributable English word list
  (public-domain / CC0 / MIT / BSD / Apache-2.0 or equivalent); write provenance
  into `gazekey/prediction/data/README.md` (research R1) — **reject** unclear
  license sources
- [ ] T017 Add `gazekey/prediction/data/words_en.txt` from the chosen licensed
  source (frequency-ordered; ~20k–50k target)
- [ ] T018 Implement `WordProvider` Protocol in
  `gazekey/prediction/word_provider.py` per
  `specs/003-predictive-text-keyboard-ux/contracts/word-provider.md`
- [ ] T019 Implement `TrieWordProvider` in `gazekey/prediction/trie_provider.py`
  with **efficient top-3 frequency retrieval** (research R2: not naive
  full-subtree collect-then-sort); min prefix length ≥2 returns `[]` for shorter
- [ ] T020 [P] Add `tests/unit/test_word_provider.py`: API rules (`hel` matches,
  `h`→`[]`, `zzzz`→`[]`, `len<=3`) plus deterministic **quality smoke** for
  common prefixes (e.g. `th`, `he`, `an`, `in`, `wh`) asserting sensible
  completions against the bundled list
- [ ] T021 Implement `TypingContext` in `gazekey/prediction/typing_context.py`
  per `contracts/typing-context.md` / data-model: update only on
  `on_action_delivered` with `ok=True`; no post-batch `clear_prefix()` for
  suggestion accept
- [ ] T022 [P] Add `tests/unit/test_typing_context.py`: letter append, backspace,
  Space clears, ENTER clears, failed inject leaves prefix unchanged, suggestion
  suffix+Space clears via Space delivery only
- [ ] T023 Wire `TypingContext` subscription to `ActionDispatcher` in
  `gazekey/ui/virtual_keyboard.py` (or thin helper) without refreshing
  suggestions on the gaze frame path

**Checkpoint**: Provider + context unit tests pass; ready for suggestion UI.

---

## Phase 4: User Story 1 — Complete a word from suggestions (P1) 🎯 MVP

**Goal**: Show ≤3 suggestions from prefix; gaze/mouse accept dispatches
suffix + Space via existing KeyAction path (FR-001–FR-005).

**Independent Test**: Quickstart §B–C; contract path with fake adapter.

- [ ] T024 [US1] Implement `suggestion_dispatch` in
  `gazekey/prediction/suggestion_dispatch.py`: compute suffix; dispatch sequential
  CHAR + Space through `ActionDispatcher`; stop on first delivery failure;
  Shift-armed + non-empty lowercase prefix → clear Shift, do **not** apply to
  suffix (research R5)
- [ ] T025 [P] [US1] Add `tests/unit/test_suggestion_dispatch.py`: `hel`+`hello`
  → `lo `; epoch stale → no dispatch; Shift-armed + prefix `hel` → lowercase
  `lo ` and Shift cleared (**no** `helLo`); partial failure leaves context
  consistent with delivered chars
- [ ] T026 [US1] Activate suggestion bar UI: enable slots, hide/disable empty
  slots (no placeholders), set labels from `WordProvider.suggest` in
  `gazekey/ui/keyboard_layout.py` / `gazekey/ui/virtual_keyboard.py` on
  `TypingContext` change (`prefix_epoch`)
- [ ] T027 [US1] Extend `gazekey/typing/key_semantics.py` and
  `gazekey/typing/gaze_typing_runtime.py` so `suggestion:0..2` are dwellable
  when enabled; on fire, call suggestion accept with epoch guard
  (`contracts/suggestion-selection.md`)
- [ ] T028 [US1] Wire mouse click on suggestion buttons to the same accept path
  as dwell in `gazekey/ui/virtual_keyboard.py` (parity with keys)
- [ ] T029 [US1] Add `tests/contract/test_suggestion_typing_path.py`: dwell/mouse
  suggestion → fake adapter receives suffix+Space; empty slot not dwellable
- [ ] T030 [US1] Manual smoke: type `hel`, dwell a suggestion, confirm external
  app shows completed word + Space (quickstart §C)

**Checkpoint**: US1 MVP — suggestions appear and complete words via OS path.

---

## Phase 5: User Story 2 — Keep typing when suggestions unused (P1)

**Goal**: Fail open; character typing works with empty or ignored suggestions
(FR-007, FR-012).

**Independent Test**: Quickstart §D; existing typing contract tests still pass.

- [ ] T031 [US2] Ensure empty suggestion slots are not dwellable and do not
  block key hit-testing in `gazekey/typing/gaze_typing_runtime.py` /
  layout export
- [ ] T032 [US2] Verify ignore-suggestions path: typing letters/Space/Backspace/
  Enter still uses unchanged KeyAction → dispatcher → adapter path in
  `gazekey/ui/virtual_keyboard.py` / `gazekey/typing/gaze_typing_runtime.py`
- [ ] T033 [P] [US2] Extend or add regression coverage in
  `tests/contract/test_typing_dispatch_path.py` (and/or
  `tests/unit/test_gaze_typing_runtime.py`) proving OS-bound keys still deliver
  with suggestions empty or ignored
- [ ] T034 [US2] Manual smoke: type a short word key-by-key ignoring suggestions;
  type a non-dictionary prefix → empty slots; typing still works (quickstart §D)

**Checkpoint**: Prediction never blocks normal typing.

---

## Phase 6: User Story 4 — Consistent suggestion behavior (P2)

**Goal**: Prefix/suggestions stay coherent across type, delete, word boundary,
and accept (FR-006, FR-006a, SC-003).

**Independent Test**: Quickstart §B + §E; unit epoch/context tests.

- [ ] T035 [US4] On every successful delivery that changes `TypingContext`,
  refresh suggestion set synchronously on UI thread in
  `gazekey/ui/virtual_keyboard.py` (no gaze-frame refresh; research R6)
- [ ] T036 [US4] Cancel in-progress suggestion dwell when `prefix_epoch` changes
  mid-dwell in `gazekey/typing/gaze_typing_runtime.py` (research R6)
- [ ] T037 [P] [US4] Add/extend unit tests for: type→suggest update, backspace→
  shorten, Space→clear suggestions, accept→empty prefix via Space delivery,
  stale epoch accept rejected (`tests/unit/test_typing_context.py` and/or
  `tests/unit/test_suggestion_dispatch.py`)
- [ ] T038 [US4] Manual scripted sequence (quickstart §B/§E): prefix, backspace,
  accept/ignore, Space — suggestions always match internal prefix

**Checkpoint**: No stale suggestion accepts; context matches delivered text.

---

## Phase 7: Polish & cross-cutting

**Purpose**: Integration validation; docs; no mapping changes.

- [ ] T039 [P] Update `README.md` and/or `docs/PROJECT_STRUCTURE.md` briefly for
  prediction package + simplified product keyboard (no mapping retune)
- [ ] T040 [P] Update `docs/TYPING_CANDIDATE.md` note that 003 adds prediction
  downstream of mapped gaze without changing PCA4 constants
- [ ] T041 Run automated sweep from quickstart:
  `pytest tests/unit/test_typing_context.py tests/unit/test_word_provider.py
  tests/unit/test_suggestion_dispatch.py tests/unit/test_layout_geometry.py
  tests/contract/test_typing_dispatch_path.py
  tests/contract/test_suggestion_typing_path.py -q`
- [ ] T042 Execute remaining quickstart.md sections A–G; append results to
  `specs/003-predictive-text-keyboard-ux/quickstart-gate-log.md`
- [ ] T043 Confirm `gazekey/mapping/config.py` and mapping benchmarks were not
  modified for this feature (SC-007)

**Checkpoint**: Feature ready for `/speckit-implement` completion review.

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

### User Story Dependencies

| Story | Depends on | Notes |
|-------|------------|-------|
| US3 | Setup | Runs first (plan Phase A) |
| US1 | US3 + Prediction core | MVP |
| US2 | US1 (suggestion slots exist) | Fail-open / regression |
| US4 | US1 (+ US2 refresh wiring) | Consistency / epoch |

### Parallel Opportunities

- T006, T007, T008 after T004/T005 inventory of shared layout edits (coordinate
  if same file — prefer sequential on `keyboard_layout.py`)
- T020 ∥ T022 after provider/context implemented
- T025 ∥ T029 after dispatch exists
- T033 ∥ T037 in polish-adjacent testing
- T039 ∥ T040 documentation

### Within stories

- Geometry gate (T014) before prediction core
- Word list license (T016) before shipping `words_en.txt` (T017)
- Provider before UI refresh; TypingContext before accept path
- Shift casing regression (T025) before declaring US1 done

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

**US3 geometry gate + Phase 3 + US1** (through T030). US2/US4 before merge.

---

## Notes

- Do **not** retune calibration/mapping for UI or prediction issues
- `<1 ms` suggest / `<200 ms` trie build = design targets, not SC gates
- No post-batch `clear_prefix()` after suggestion accept
- Commit after each task or logical group
- Avoid vague tasks; keep file paths exact
