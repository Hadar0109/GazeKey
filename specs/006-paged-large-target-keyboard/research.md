# Research: Paged Large-Target Keyboard

**Feature**: `006-paged-large-target-keyboard`  
**Date**: 2026-08-25

All specify-time clarifications are already resolved in `spec.md`. This file
records **planning** decisions: letter-area structure, relative sizing, page
state, and how page-switch integrates with existing dwell/hit-test without
touching GazeFollower.

## R1 — Letter-area structure (two-pane, bottom row full width)

**Decision**: Rebuild the letter region as a horizontal two-pane layout:

- **Left page**: `[letters column] | [tall → arrow]`
- **Right page**: `[tall ← arrow] | [letters column]`

The letters column is a vertical stack of three rows (FR-002 / FR-003) with
Shift and Backspace on the third row (FR-008). The arrow is **one** gaze
target spanning the **first two** letter rows only. The third letter row is
**full letter-area width** (no arrow beside Shift / ZXCV or BNM / Backspace).
The bottom row (Calibrate | Space | Enter) stays **full keyboard width**
below the letter area. Suggestion bar and chrome are unchanged.

**Rationale**: A two-row spanning arrow is still a large vertical gaze
target (FR-004, T016 visual revision) without stealing width from the
Shift/Backspace row. Nested panes let letters expand into leftover width
instead of staying trapped in a native QWERTY half (FR-007).

**Alternatives considered**:

- Native-half letters + unused half as the arrow — rejected by specify Q1
  (weak letter-width gain).
- Three stacked arrow buttons (one per row) — looks like three targets and
  splits the hitbox.
- Overlay/absolute positioning — fights existing layout export and
  `update_responsive_sizes`.

## R2 — Arrow vs letter relative sizing (no pixels in spec)

**Decision**: Size the two-row letter+arrow panes with **stretch weights**,
not pixels:

- Letter pane stretch **5**
- Arrow pane stretch **1**

That is about **17%** of the two-row pane width for the arrow and **83%**
for letters (letter-area width for the first two rows). On the left page,
five first-row letters share that 83%, so each is about **17%** of
letter-area width versus about **10%** today (ten equal keys). The third
row is full letter-area width. A moderate window-height increase (R9)
makes keys taller as well. Together these satisfy SC-001 without a
spec-level stretch factor.

Implementation may keep these as named layout weights (e.g.
`LETTER_PANE_STRETCH = 5`, `ARROW_PANE_STRETCH = 1`). Tests MUST assert
**relative** geometry on the live widget:

- Arrow width is between **12%** and **22%** of the letter-area width
  (5:1 ≈ 16.7%; band allows Qt rounding)
- Mean visible letter-key width **exceeds** letter-area width / 10 (beats
  the current full-QWERTY first-row share)
- Arrow height spans the **first two** letter rows (taller than one letter
  key; does **not** cover the third row)

Width remains a relative SC-001 check. Letter-row **height** may increase
with the planned window ratio (FR-015 / R9); do **not** treat the width
check as a second stretch factor, and do **not** assert a numeric area
multiplier in tests.

Do **not** encode absolute pixel sizes in the spec, plan constants for
production layout, or tests that assume a particular screen resolution.

**Rationale**: Spec FR-004 / FR-006 require planning to choose ratios from
the live letter area. After T016 visual review, **5:1** leaves more width
for letters than 4:1 while keeping the arrow as a strip (not a tiny icon).
The 12–22% test band allows Qt rounding without locking pixels.

**Alternatives considered**:

- 4:1 (arrow 20%, three-row span) — first paged layout; rejected at T016
  visual review (arrow too wide and too tall; letters not large enough).
- 3:1 (arrow 25%) — larger arrow, smaller letters; weaker SC-001 margin.
- Match arrow width to one letter key exactly — too narrow for a page-switch
  control that must be easier to hit than a letter.

## R3 — Rebuild visible page; synchronous removal before export

**Decision**: On page change, **destroy and recreate** the letter-area
widgets. Do **not** keep the other page’s letter buttons hidden in the tree.

Removal from **active target discovery** MUST be **synchronous** and MUST
complete **before** `export_keyboard_layout` runs:

1. Take previous letter-area widgets out of the inspected keyboard tree
   (layout `takeAt` / unparent so `findChildren` under the export root does
   not see them).
2. Drop host references (`letter_keys`, arrow button, `_layout_keys` entries
   for previous-page letters).
3. Create the destination page widgets.
4. Restore Shift visual state; `apply_no_focus_policies`;
   `update_responsive_sizes`.
5. Call `export_keyboard_layout` (refresh `_layout_keys` / hitboxes) **in
   the same switch**, after step 1–2. Cancel in-progress letter **or
   suggestion** dwell (completed arrow MUST NOT dispatch a suggestion).

Do **not** rely solely on deferred Qt `deleteLater()` to prevent stale
targets. `deleteLater()` may leave widgets parented and discoverable until
the event loop runs. A page-switch function that returns, then exports, must
already have previous-page letters absent from export and `hit_test_layout_keys`.

**Required test** (Phase A / tasks **T013** checkpoint, not US4-only):
switch page, and **immediately** (no extra wait for `deleteLater`) assert
previous-page letters are absent from `inspect_keyboard_layout` and produce
zero hits.

**Rationale**: Live hit-testing consumes `_layout_keys` from layout export.
A same-stack export after `deleteLater()` would still see old letters and
violate FR-010/FR-011.

**Alternatives considered**: Toggle `hide()`/`show()` on two prebuilt pages —
faster, but hidden widgets remain discoverable if export does not filter
them. Relying on `QTimer.singleShot(0, export)` plus `deleteLater()` —
event-loop ordering is not an explicit contract and fails the immediate
isolation test.

## R4 — Page identity and persistence

**Decision**: Store `letter_page` on `VirtualKeyboard` as `"left"` | `"right"`.
Default and launch value: `"left"`.

| Event | Page |
|-------|------|
| First UI build / `python main.py` after calibration | `left` |
| User completes page-switch arrow | toggle |
| Minimize / restore | **unchanged** (window stays shown; only chrome swaps) |
| Official recalibrate hide → show | reset to `left` |

Reset after recalibrate in **GazeKey keyboard code** on the explicit
**return-from-official-recalibrate** path only (`VirtualKeyboard` after
`run_official_recalibrate` returns — a dedicated post-recalibrate hook or
flag). Do **not** reset `letter_page` in a blanket `showEvent` (that would
also fire on ordinary show / restore and violate FR-009 minimize/restore).
Do **not** change GazeFollower Preview/Calibration, sampling, or
`gazekey/backend/` geometry/filter/origin logic.

**Rationale**: Matches FR-009. Minimize already keeps `main_content_widget`
in memory and does **not** go through official recalibrate, so page widgets
persist without a showEvent reset. Recalibrate returns through
`run_official_recalibrate`; that return is the reset hook.

**Alternatives considered**: Persist across recalibrate — rejected by specify
Q3. Reset on minimize/restore — also rejected (Q3).

## R5 — Page-switch as a system control (no OS input)

**Decision**: Treat the arrow like Calibrate, not like a letter.

| Page | `gazeKeyId` / `gazeKeyAction` | Label | Placement |
|------|-------------------------------|-------|-----------|
| Left | `system:page_right` | `→` | Right side of letter area |
| Right | `system:page_left` | `←` | Left side of letter area |

- `objectName="gazeTarget"` (exported and dwellable)
- New `KeyRole.SYSTEM_PAGE_SWITCH` in `key_semantics.py`
- `GazeTypingRuntime._handle_activation` calls a keyboard callback; returns
  no `KeyAction`; applies existing activation cooldown
- Dwell parameters **unchanged** (0.9 s, lockout, 5-frame leave, 0.25 s
  switch confirm, 0.20 s cooldown)
- `dwell_engine.py` is **not** modified
- Prediction / `TypingContext` is **not** notified (FR-005, FR-019)
- Restore Shift checked-state and letter case from `TypingSession` after
  rebuild (FR-019)

**Rationale**: Existing calibrate/suggestion branches already separate
system controls from OS injection. Reusing that pattern keeps Feature 002
dwell timing intact.

**Alternatives considered**: Emit a dummy KeyAction and filter in the
dispatcher — extra surface for accidental OS delivery. Unicode in
`action_from_label` without `gazeKeyAction` — brittle.

## R6 — Hit-test / export sync after switch

**Decision**: Page switch is a **functional geometry change**. The only
allowed sync updates are:

- Live widget bounds
- `inspect_keyboard_layout` export → `_layout_keys` / `_keys_by_id`
- `typing_region_rect` union (must include the arrow while visible)
- Semantic row map as needed so export stays coherent

Do **not** change `hit_test_layout_keys` math, snap margins, origin/DPR
conversion, GazeFollower filtering, or mapping benchmarks.

**Risk**: A two-row-tall arrow has a different height than letter keys.
`inspect_keyboard_layout` clusters rows by y-center with a tolerance based
on **median** height. Many letter/suggestion keys should keep the median at
letter height so rows do not merge. Mitigation: stable `gazeKeyId` on the
arrow; geometry tests that left-page letters still form three distinct
rows, that the arrow covers only the first two rows, and that hidden-page
letters are absent from export and hit-test.

**Rationale**: Gaze loop already hit-tests exported layout keys each frame.
That export is valid only if previous-page letters were synchronously
removed from discovery before it ran (R3).

## R7 — Isolation (forbidden vs allowed)

**Decision**: Allowed edits are the product keyboard surface and the thin
system-control branch:

- `gazekey/ui/keyboard_layout.py`, `gazekey/ui/virtual_keyboard.py`
- `gazekey/typing/key_semantics.py`, `gazekey/typing/gaze_typing_runtime.py`
  (page-switch callback only)
- Layout inspector only if stable id / special-key classification needs
  `system:page_*`
- Tests + Feature 006 spec artifacts

**Forbidden** (must remain byte-identical unless a task proves a one-line
keyboard callback is required at the existing recalibrate handoff):

- `gazekey/backend/` GazeFollower lifecycle, adapter, filtering, origin/DPR,
  geometry audit
- `gazekey/typing/dwell_engine.py` timing
- `gazekey/prediction/` ranking, trie, TypingContext rules
- Feature 004 specs/runs/tags
- Mapping/evaluation acceptance gates

**Rationale**: Constitution I–III, V and spec FR-012–FR-017.

## R8 — Practical typing check vs mapping benchmarks

**Decision**: Automated tests cover layout, page contents, immediate
hit-test isolation after switch, and “arrow does not OS-inject”. Live
chin/head-support checks cover SC-002/SC-003/SC-006. Independent GazeFollower
/ mapping benchmarks are **not** this feature’s gate and MUST NOT be retuned.

SC-006 comparison MUST use a **recorded Feature 006 baseline** (R10), not
memory of the old full-QWERTY layout.

**Rationale**: Spec SC-006 is a practical interaction outcome from larger
targets, not a mapping metric.

## R9 — Responsive sizing

**Decision**: Extend `update_responsive_sizes` so the arrow height equals the
stacked **first two** letter rows (including the gap between them). Letter
keys keep a per-row height policy (taller when the window is taller). The
third letter row and the bottom Calibrate/Space/Enter row stay full width.
Window height ratio is **~70%** of available screen height (`KEYBOARD_HEIGHT_RATIO
= 0.70`), still pinned to the **top** (FR-015). About **30%** of available
height remains for the focused external application on the same screen.

**Rationale**: T016 visual review: keys need more width (5:1, two-row arrow)
and more height (moderate window growth). Full-screen or moving the overlay
off the top remains out of scope.

## R10 — Pre-implementation full-QWERTY practical baseline

**Decision**: Before any production layout change, run a Feature 006
**baseline USER GATE** on the **current full-QWERTY** product keyboard
(Feature 003 R7 + bottom-row Calibrate). Record practical
**intended-key / focus** results under **chin/head support** with **fixed
test inputs**. Later paged-layout comparison (SC-006) MUST cite that
recorded file — not recollection.

This is a **practical interaction baseline**, not a mapping benchmark:

- Do **not** retune GazeFollower, filtering, origin/DPR, or mapping
- Do **not** use Feature 004 T060 / mapping-percentage gates
- Do **not** add a diagnostics platform; one lightweight recorded note is
  enough (Constitution VII)

**Fixed inputs** (same protocol before and after paging):

- Official GazeFollower calibration accepted; no backend changes between
  baseline and paged comparison
- Chin/head support on; suggestions unused
- Scripted intended letters (12 trials covering **both pages** and **all
  three QWERTY rows**; first and last letter of each page-row):

  `Q T A G Z V / Y P H L B M`

  Left-page letters: Q, T, A, G, Z, V. Right-page letters: Y, P, H, L, B, M.
  After paging, the user switches pages as needed; the intended sequence
  does not change.
- For **each** trial record: intended key, focused key, correct/incorrect.
  Wrong-focus counts even if dwell never fires (Feature 005 focus rule).
  Also record the session **total wrong-focus count**.
- `hello` is **not** this comparison. It remains the separate SC-003
  mixed-page typing USER GATE (type the word into the external app).
- Optionally note Space/Backspace only if needed to recover the trial; they
  are not the comparison metric

**Record** at
`specs/006-paged-large-target-keyboard/baseline/full-qwerty-intended-key.md`
(create at gate time): date, chin/head support, calibration accepted, the
12-trial table (intended / focused / correct-incorrect), total wrong-focus
count. After the paged layout exists, a matching note under
`baseline/paged-intended-key.md` uses the **same sequence and conditions**.

**Rationale**: SC-006 requires fewer visible-letter focus errors than the
current layout. A 12-letter sequence spanning both pages and all three
rows is a fairer target-size comparison than `hello` (five dwells, mostly
one right-page key). Without a pre-change record, the comparison is
anecdotal. `hello` still validates mixed-page typing (SC-003).

**Alternatives considered**: Compare from memory after the old layout is
gone — rejected. Reuse Feature 004 mapping runs as `eval_before` — those
are mapping evidence, not this feature’s practical keyboard-surface
baseline, and MUST NOT gate or retune GazeFollower here.
