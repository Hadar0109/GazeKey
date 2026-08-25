# Implementation Plan: Paged Large-Target Keyboard

**Branch**: `006-paged-large-target-keyboard` | **Date**: 2026-08-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/006-paged-large-target-keyboard/spec.md`

## Summary

Improve practical gaze typing by **enlarging visible letter targets**, without
changing GazeFollower. Split QWERTY letters into two pages and switch with a
tall vertical arrow:

`GazeFollower screen gaze → live QRect hit-test (visible page only) →
existing dwell → KeyAction → OS` (unchanged below the keyboard surface)

Left page: **Q W E R T / A S D F G / Shift Z X C V Backspace** plus a
right-side **→** strip. Right page: **Y U I O P / H J K L / Shift B N M
Backspace** plus a left-side **←** strip. Suggestions, Calibrate, Space,
Enter, and chrome stay on both pages. Arrow never types. Mapping, dwell
timing, and prediction logic stay sealed.

## Technical approach

1. **Full-QWERTY baseline (before layout change)** — Record practical
   intended-key/focus on the current keyboard under chin/head support with
   fixed inputs ([research R10](./research.md)). Later SC-006 comparison
   uses that file, not memory. Not a mapping benchmark; do not retune
   GazeFollower.
2. **Letter-area rebuild (gate)** — Two-pane layout per [research R1](./research.md);
   stretch **4:1** letters:arrow (R2); destroy/recreate on page change with
   **synchronous** removal from target discovery before export (R3).
3. **Page state** — `letter_page` left|right on `VirtualKeyboard` (R4); default
   left; persist across minimize/restore; reset left after official
   recalibrate hide/show. Restore Shift visual from `TypingSession` after
   rebuild (FR-019).
4. **System control** — `system:page_right` / `system:page_left` as
   `gazeTarget`; runtime callback; no `KeyAction` (R5). Do not edit
   `dwell_engine.py`.
5. **Geometry sync** — After previous-page widgets are unparented from the
   export root, `export_keyboard_layout` in the same switch so `_layout_keys`
   matches on-screen QRects (R6). Do not rely solely on `deleteLater()`.
6. **Tests + USER GATE** — Immediate hidden-letter isolation test; relative
   size/page-content tests; chin/head-support mixed-page `hello` typing
   (SC-003); SC-006 intended-key/focus vs the **recorded** 12-letter
   baseline (R10). No mapping retune (R8, R10).

## Technical Context

**Language/Version**: Python 3.11 (project `.venv`; do not run on 3.14)

**Primary Dependencies**: Existing product stack (PySide6, official
GazeFollower backend, pynput OS adapter). **No new pip deps.**

**Storage**: In-process `letter_page` only; not persisted to disk. Practical
baseline notes live under `specs/006-paged-large-target-keyboard/baseline/`
(recorded evidence, not a mapping run store).

**Testing**: pytest — page contents, arrow placement, relative letter vs
arrow geometry, **immediate** hit-test isolation after switch (previous-page
letters absent without waiting on `deleteLater`), page-switch does not
OS-inject, Shift armed survives switch; full-project `pytest -q`. Live
USER GATE: pre-change full-QWERTY intended-key/focus baseline on the R10
12-letter sequence, then the same sequence after paging (SC-006); separate
mixed-page `hello` typing check (SC-003). Chin/head support. Not a mapping
benchmark.

**Target Platform**: Windows desktop (primary)

**Project Type**: Desktop application (PySide6 keyboard + GazeFollower)

**Performance Goals**: Page rebuild is a user action, not per-frame. Tracking
~GazeFollower rate unchanged. After a switch, previous-page letters MUST
already be undiscoverable and `_layout_keys` MUST already match the new page
before the switch function returns (export in the same switch; not
`deleteLater`-only).

**Constraints**:

- Spec 006 clarifications + [research.md](./research.md)
- Stretch weights 4:1; tests use relative fractions, not pixels
- Dwell parameters unchanged (0.9 s / 0.20 s cooldown / 5-frame leave /
  0.25 s switch)
- Prediction, GazeFollower, origin/DPR, filtering, mapping benchmarks
  unmodified
- Top-of-screen keyboard size/placement unchanged
- Feature 004 historical; not a live gate
- Manual USER GATE for live webcam / external-app checks, including the
  **pre-implementation full-QWERTY baseline** (R10) before layout change
- Page rebuild MUST synchronously remove previous-page widgets from target
  discovery before export (R3); no `deleteLater`-only isolation

**Scale/Scope**: Single-monitor English QWERTY product keyboard; two letter
pages; one user; chin/head-support practical checks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (GazeKey **v1.4.0**)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| Accuracy First | Mapping independently validated; 006 consumes GazeFollower screen gaze only; larger keys are UI, not mapping compensation | ✅ |
| Measurable Progress | 006 SC in spec; pre-change full-QWERTY intended-key/focus **record** (R10) then paged comparison; mapping benchmarks unchanged and not this feature’s gate | ✅ |
| Simple Pipeline | Sealed upstream remains GazeFollower → screen gaze → live geometry → dwell; no post-backend remap | ✅ |
| Spec Before Code | Spec + clarifications + this plan before implement | ✅ (`tasks.md` next) |
| Feature Scope Control | Matches 006 spec; no prediction/dwell/backend redesign | ✅ |
| Testable Architecture | Keyboard surface and page-switch control separable from backend and prediction | ✅ |
| Run Clarity | One lightweight baseline note + geometry tests; no diagnostics platform; mapping run summaries unchanged | ✅ |
| Documentation Hierarchy | Spec Kit SoT for this phase; Feature 004 untouched | ✅ |
| Targeted Cleanup | No unrelated deletions; Feature 003 chrome removals stay | ✅ |
| Simple Logging | Optional verbose on page switch; no logging framework | ✅ |
| Minimal Calibration UI | Official GazeFollower Preview/Calibration unmodified; 006 does not host calib UI | ✅ |

**Post-design re-check**: Same — keyboard geometry changes are downstream UI.
Synchronous layout export / hit-test refresh is required sync, not mapper
retune. The full-QWERTY baseline is a practical interaction record, not a
mapping benchmark. GazeFollower official UI remains unmodified (Principle XI
exception).

## Project Structure

### Documentation (this feature)

```text
specs/006-paged-large-target-keyboard/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Phase 1 entities
├── quickstart.md        # Manual validation
├── baseline/            # Recorded practical intended-key notes (R10)
│   ├── full-qwerty-intended-key.md   # BEFORE layout change
│   └── paged-intended-key.md         # AFTER paged layout (same inputs)
├── contracts/
│   ├── keyboard-layout-006.md
│   └── page-switch.md
└── tasks.md             # /speckit-tasks (next)
```

### Source Code (repository root)

```text
gazekey/
├── ui/                            # MODIFY
│   ├── keyboard_layout.py         # Paged letter area + spanning arrow
│   └── virtual_keyboard.py        # letter_page state, switch, persist/reset
├── typing/                        # EXTEND (thin)
│   ├── key_semantics.py           # SYSTEM_PAGE_SWITCH / system:page_*
│   └── gaze_typing_runtime.py     # callback; no KeyAction; cancel dwell
├── layout/                        # TOUCH ONLY IF NEEDED
│   └── layout_inspector.py        # classify system:page_* as special
├── prediction/                    # DO NOT MODIFY
├── backend/                       # DO NOT MODIFY GazeFollower internals
└── typing/dwell_engine.py         # DO NOT MODIFY

tests/
├── unit/
│   ├── test_layout_geometry.py    # EXTEND relative size + page contents
│   └── test_paged_keyboard.py     # NEW page switch; immediate stale-target isolation
```

**Structure Decision**: Extend the existing product keyboard and the existing
system-control branch. No new top-level package. Do not add a second live
layout exporter.

## Implementation phases (for tasks.md)

### Phase 0 — Full-QWERTY practical baseline (before layout change)

- On the **current** Feature 003 full-QWERTY keyboard, chin/head support,
  suggestions unused, official GazeFollower calibration unchanged
- Run the fixed intended-key/focus protocol from research R10:
  `Q T A G Z V / Y P H L B M` (both pages’ letters, all three QWERTY rows)
- Record `specs/006-paged-large-target-keyboard/baseline/full-qwerty-intended-key.md`
  (per trial: intended key, focused key, correct/incorrect; plus total
  wrong-focus count)
- **USER GATE**: baseline file exists with those 12 trials
- **Do not** change production layout until this record exists
- **Do not** retune GazeFollower or treat this as a mapping benchmark
- `hello` is **not** this protocol; it remains the Phase D mixed-page
  typing USER GATE (SC-003)

### Phase A — Paged layout & geometry gate

- Two-pane letter area; 4:1 stretch; spanning arrow (R1–R2)
- Left default page; Shift/Backspace on both third rows
- Bottom row / suggestions / chrome unchanged
- Destroy/recreate on page API with **synchronous** unparent/removal before
  export (R3)
- Automated relative-geometry + page-content tests
- Automated **immediate** hidden-letter isolation test is a **Phase A
  rebuild checkpoint** (tasks T013), not deferred to later US4-only proof
- **USER GATE**: visual layout (arrow side/direction, larger letters) plus
  dwell **2–3 left-page letters** into Notepad (not `hello`, not SC-006)

### Phase B — Page-switch interaction

- `system:page_*` gazeTarget + runtime callback (R5)
- Export in the same switch after sync removal; dwell cancel (R3, R6)
- Mouse click parity; no OS injection; Shift survives switch
- Completed arrow must not accept an in-progress suggestion dwell
- Unit/contract: hidden letters not hit-tested (already T013); arrow does
  not type

### Phase C — Persistence

- Minimize/restore keeps page (R4)
- Reset to left only on the explicit **return-from-official-recalibrate**
  path; do **not** blanket-reset on every `showEvent`
- Launch after calibration shows left page

### Phase D — Integration & quickstart

- Mixed-page word (`hello`) USER GATE under chin/head support (SC-003
  end-to-end typing; not the SC-006 comparison)
- Record `baseline/paged-intended-key.md` with the **same** R10 sequence
  `Q T A G Z V / Y P H L B M` and the same per-trial fields; compare
  total wrong-focus to the Phase 0 file (SC-006)
- Suggestions still complete suffix + Space after a page switch
- Full `pytest -q`
- Confirm no GazeFollower / dwell-engine / prediction diffs

## Complexity Tracking

No constitution violations requiring justification.

## Generated artifacts

| Artifact | Path |
|----------|------|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Quickstart | [quickstart.md](./quickstart.md) |
| Contracts | [contracts/](./contracts/) |

**Next command**: `/speckit-tasks`
