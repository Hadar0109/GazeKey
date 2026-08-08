# Implementation Plan: Gaze Typing & OS Integration

**Branch**: `002-gaze-typing-os` | **Date**: 2026-08-08 (revised) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-gaze-typing-os/spec.md`

## Summary

Extend the sealed upstream pipeline (`tracking → features → calibration → PCA4
mapping → mapped gaze`) with a **product typing path**:

`mapped gaze → key detection → dwell/click selection → KeyAction →
ActionDispatcher → OsInputAdapter → intended external typing target`.

Typing **auto-starts** after successful calibration/mapping. Calibration/mapping
remain isolated and unchanged. UI layout stays as today: **fullscreen
calibration**, then keyboard in its **current top-half** position with the
external app usable in the lower half — no redesign or reposition.

Cleanup and package boundaries (`gazekey/` vs `tools/`, delete obsolete
future/intent/selection/dormant typing) happen **before** most new typing
implementation. Preview and benchmark are **separate developer entry points**,
not product modes.

## Technical approach

1. **Package cleanup first** — Establish `gazekey/` vs `tools/`; remove/disconnect
   `future/`, `intent/`, `selection/`, dormant dwell controllers; audit
   `GAZEKEY_*` flags; move evaluation/debug/preview out of the product package.
   Keep only runtime session/calibration **state** in product; move artifact
   writers/summaries to tools where appropriate.
2. **KeyAction → ActionDispatcher → OsInputAdapter** — Selection publishes a
   **requested** `KeyAction`; adapter reports **delivery** outcome; observers can
   distinguish requested vs successfully delivered. `pynput` only inside the
   adapter.
3. **Reliability-first dwell** — **0.9 s** dwell; **0.20 s** global cooldown after
   successful dwell-based activations that change typing state (including typing
   keys, Shift, Pause, Resume, unless implementation evidence justifies an
   exception); same-key lockout; **5 consecutive off-key frames** for confirmed
   leave. Rebuild only after cleanup gate + injection skeleton + focus check.
4. **Active OS key set** — A–Z, Space, Backspace, Enter; **Shift = one-shot** for
   the next letter; clear pending Shift on Pause, recalibration, mapping/session
   reset, tracking/mapping session termination, and similar unsafe transitions.
   Ctrl/Alt may stay visible but **must not** produce OS input. Pause/Resume is
   internal (no OS `KeyAction`).
5. **Layout preserved** — No keyboard reposition/redesign. Focus is an
   OS/window-behavior concern only; **early focus validation runs only after** a
   minimal KeyAction→dispatcher→adapter path exists.
6. **Dev tooling** — Separate entry points for preview and benchmark; `GAZEKEY_*`
   changes only after an explicit KEEP / MOVE TO TOOLS / DELETE inventory.

## Technical Context

**Language/Version**: Python 3.8+ (project baseline; local env may be newer)

**Primary Dependencies**: PySide6 ≥6.6, OpenCV ≥4.8, MediaPipe ≥0.10, NumPy ≥1.24,
pynput ≥1.7.6 (behind adapter only)

**Storage**: Runtime session state in-process; developer artifacts under `runs/`
via **tools** writers (not required inside product `gazekey/` modules)

**Testing**: pytest — dwell/cooldown/leave, KeyAction request vs delivery,
adapter fake, pause/resume; early manual focus validation in quickstart

**Target Platform**: Windows desktop (primary)

**Project Type**: Desktop application (PySide6 + tracking thread)

**Performance Goals**: ~30 FPS tracking; dwell per frame on main thread &lt; 1 ms;
OS inject on selection completion only

**Constraints**:

- Spec 002 clarifications + this plan revision
- Do not change calibration/mapping fit/predict for typing
- Preserve existing fullscreen calib + top-half keyboard geometry
- No Ctrl/Alt shortcuts or multi-key chords; no UI redesign

**Scale/Scope**: Single user, single monitor, letters-keyboard OS key set as
narrowed above, external app typing via OS injection

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (GazeKey **v1.3.0**)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| Accuracy First | Mapping remains independently validated; 002 consumes mapped gaze only and does not compensate via mapping changes | ✅ |
| Measurable Progress | Mapping SC remain in `001`; typing SC are dwell→KeyAction→OS (own spec) | ✅ |
| Simple Pipeline | Sealed upstream through mapped gaze; typing stages specified downstream; no mapper compensations for typing | ✅ |
| Spec Before Code | Spec + clarifications + plan before implement | ✅ (`tasks.md` next) |
| Feature Scope Control | 002 specifies dwell/typing/OS; advanced prediction/language/etc. still out of 002 | ✅ |
| Testable Architecture | KeyAction + dispatcher + adapter + tools split; mapping packages untouched in role | ✅ |
| Run Clarity | No diagnostics platform; artifact writers in tools | ✅ |
| Documentation Hierarchy | Spec Kit is SoT for this phase | ✅ |
| Targeted Cleanup | Cleanup early; inventory-first flag/deletes via tasks | ✅ |
| Simple Logging | Quiet + optional verbose | ✅ |
| Minimal Calibration UI | Unchanged fullscreen calib; fixation distraction rules intact | ✅ |

**Post-design re-check**: Same results under v1.3.0 — prior “OS injection out of MVP” tension is resolved by Feature Scope Control; Complexity Tracking rows that only existed for that ban are obsolete.

## Project Structure

### Documentation (this feature)

```text
specs/002-gaze-typing-os/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── pipeline.md
│   ├── key-action.md
│   ├── dwell-selection.md
│   ├── os-input.md
│   └── package-boundaries.md
├── spec.md
└── tasks.md             # /speckit-tasks — not created here
```

### Source Code (target layout)

```text
main.py                              # Product entry
gazekey/                             # RUNTIME PRODUCT ONLY
  tracking/
  features/
  calibration/                       # UNCHANGED responsibilities
  mapping/                           # UNCHANGED responsibilities
  runtime/                           # gaze_loop typing branch after cleanup
  layout/
  ui/                                # existing geometry; Pause control; no tools imports
  typing/                            # KeyAction, dwell_engine, dispatcher, typing_session
  input/                             # OsInputAdapter; pynput only here
  # minimal runtime session/calibration state only if still required by product
  # (no developer artifact writers / run-summary dumps inside gazekey/)
tools/                               # DEVELOPER TOOLING
  evaluation/                        # benchmark + diagnostics writers
  debug/
  preview/                           # separate preview entry
  # separate CLI/entry scripts for preview & benchmark
scripts/                             # audit; delete unjustified
tests/
runs/                                # written by tools / justified writers only
```

**Structure Decision**: Cleanup and `tools/` split first. Product keeps typing +
input + existing UI geometry. Do **not** introduce a fat `gazekey/session/` for
artifact I/O — only in-process runtime state needed to run the keyboard.
Calibration/mapping packages stay behaviorally unchanged.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Broader / earlier cleanup than historical “first MVP only” wording | Spec FR-011–013a + implement-order preference under v1.3.0 Feature Scope Control | Building typing atop dormant stacks recreates entanglement |
| New pipeline stages after mapping | Required for external typing (allowed when specified; consume mapped gaze only) | UI→pynput direct calls break testability |

## Phase outline (for `/speckit-tasks`)

Not tasks yet — **implementation order** (binding):

1. **Boundaries & cleanup** — Move evaluation/debug/preview to `tools/`;
   disconnect product imports; delete/disconnect `future/`, `intent/`,
   `selection/`, dormant dwell/typing; strip developer artifact writers from
   product; leave only needed runtime state in `gazekey/`. Complete an
   **explicit `GAZEKEY_*` flag inventory** (flag → read sites → tests/docs →
   KEEP / MOVE TO TOOLS / DELETE) **before** any flag deletion.
2. **Post-cleanup behavior gate** — After moves/deletes, verify the product still:
   launches; completes **fullscreen calibration**; fits/produces existing **PCA4
   mapped gaze**; preserves **current top-half keyboard** geometry; and the
   **relocated developer benchmark** still runs via its independent tools entry.
   Do **not** proceed to new typing work if this gate fails.
3. **Minimal injection skeleton** — `KeyAction`, `ActionDispatcher` (requested vs
   delivered), `OsInputAdapter` protocol + fake + pynput impl — enough to inject
   a test `KeyAction` under test/manual harness.
4. **Early Windows focus validation** — Using that minimal path, after fullscreen
   calib → top-half keyboard, verify injected KeyActions reach the external app
   without per-character focus restore (OS/window behavior only; no layout
   redesign). Focus proof **requires** the skeleton from step 3. Gate further
   dwell/typing UX on this check (or a documented mitigation if it fails).
5. **Full dwell / typing integration** — 0.9 s dwell; 0.20 s global cooldown after
   successful dwell activations that change typing state (keys, Shift, Pause,
   Resume unless evidence says otherwise); same-key lock; 5-frame leave;
   auto-start typing; Pause/Resume; Shift one-shot with clears on Pause /
   recalibrate / mapping-session reset / termination; Ctrl/Alt non-OS; mouse path.
6. **Dev entry points polish** — Finalize separate preview and benchmark launches
   (not product modes) if not already done in step 1.
7. **Tests + quickstart** — Unit/contract + manual checklist (post-cleanup gate,
   focus validation, layout preservation, Shift clears, cooldown).
