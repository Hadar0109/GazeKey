# Implementation Plan: Predictive Text & Keyboard UX

**Branch**: `003-predictive-text-keyboard-ux` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-predictive-text-keyboard-ux/spec.md`

## Summary

Extend the working `002` typing path with **prefix-based word completion** and a
**simplified product keyboard**:

`mapped gaze → hit-test (keys + suggestions) → dwell → KeyAction(s) →
ActionDispatcher → OsInputAdapter → external app`

New stages (downstream of mapped gaze only):

1. **`TypingContext`** — track in-progress prefix from successful deliveries
2. **`WordProvider`** — prefix → ≤3 ranked suggestions (bundled trie, English)
3. **Suggestion bar** — active gaze targets; accept dispatches suffix + Space
   via existing KeyAction path
4. **Keyboard UI cleanup** — remove Pause, Preview, lang, symbols, Ctrl, Alt,
   status text, typed-text bar; redistribute space to enlarge keys and fix
   suggestion bar clipping

Calibration/mapping **unchanged**. Developer preview via `tools.preview`
preserved.

## Technical approach

1. **UI + geometry first (gate)** — Remove dead product chrome; redistribute
   layout per [research R7](./research.md); verify
   `test_layout_geometry` / `test_keyboard_geometry_targets` before prediction
   wiring.
2. **`gazekey/prediction/` package** — `WordProvider` protocol, trie
   implementation, bundled `words_en.txt`, `TypingContext`,
   `suggestion_dispatch`.
3. **Wire context to dispatcher** — subscribe `on_action_delivered(ok)`; refresh
   suggestions on prefix change (not per gaze frame).
4. **Activate suggestion targets** — `objectName="gazeTarget"`, stable
   `suggestion:0..2` ids; extend `GazeTypingRuntime` + hit-test export.
5. **Suggestion accept** — epoch guard; sequential CHAR + Space through
   dispatcher; `TypingContext` evolves only via those deliveries (no redundant
   post-batch `clear_prefix()`). Shift-armed + non-empty lowercase prefix: clear
   Shift, do not apply to suffix (avoid mixed casing).
6. **Remove product pause path** — no Pause button; product session stays
   active; clean dead wiring (preserve tools/test hooks if needed).
7. **Preview split** — remove product Preview button; keep `tools.preview` and
   shared preview runtime.

## Technical Context

**Language/Version**: Python 3.8+ (project baseline)

**Primary Dependencies**: PySide6 ≥6.6, OpenCV ≥4.8, MediaPipe ≥0.10, NumPy
≥1.24, pynput ≥1.7.6 (adapter only). **No new pip deps** for prediction v1.

**Storage**: In-memory trie at startup; bundled word list under
`gazekey/prediction/data/` (documented open license only — research R1);
runtime `TypingContext` in-process only

**Testing**: pytest — word provider (incl. top-3 ranking + quality smoke),
typing context (delivery-only updates), suggestion dispatch (epoch + Shift
casing regression), layout geometry regression, contract typing path with fake
adapter

**Target Platform**: Windows desktop (primary)

**Project Type**: Desktop application (PySide6 + tracking thread)

**Performance Goals**: `suggest()` &lt; 1 ms and startup trie build &lt; 200 ms are
**design targets** (not product acceptance gates unless measurement shows they
are necessary); suggestion refresh on delivery only; tracking ~30 FPS unchanged

**Constraints**:

- Spec 003 clarifications + [research.md](./research.md)
- Internal prefix tracking only (no external readback)
- Max 3 suggestions; min prefix length 2
- Accept → suffix + Space via KeyAction path; context via delivery events only
- Trie top-3 retrieval must not assume prefix-node walk alone is enough (R2)
- Bundled vocabulary must have clear redistributable license (R1)
- No mapping/calibration retune for UI redesign
- Visible bounds = hitboxes (FR-011)

**Scale/Scope**: English word completion; letters-only product keyboard; single
monitor; existing dwell parameters (0.9 s, etc.)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (GazeKey **v1.3.0**)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| Accuracy First | Mapping independently validated; 003 consumes mapped gaze only; no mapping compensation | ✅ |
| Measurable Progress | 003 SC in spec; mapping benchmarks unchanged | ✅ |
| Simple Pipeline | Sealed upstream through mapped gaze; prediction downstream only | ✅ |
| Spec Before Code | Spec + clarify + plan before implement | ✅ (`tasks.md` next) |
| Feature Scope Control | Matches 003 spec; no multilingual/personalization v1 | ✅ |
| Testable Architecture | `prediction/` separable; KeyAction boundary preserved | ✅ |
| Run Clarity | No artifact sprawl; bundled word list only | ✅ |
| Documentation Hierarchy | Spec Kit SoT for this phase | ✅ |
| Targeted Cleanup | UI dead code removed per clarify; inventory-first | ✅ |
| Simple Logging | Verbose flag for delivery failures; no new logging framework | ✅ |
| Minimal Calibration UI | Unchanged fullscreen calib | ✅ |

**Post-design re-check**: Same — keyboard geometry changes are downstream UI;
calibration point targets may need **layout-export alignment** only, not mapper
retune.

## Project Structure

### Documentation (this feature)

```text
specs/003-predictive-text-keyboard-ux/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Phase 1 entities
├── quickstart.md        # Manual validation
├── contracts/
│   ├── word-provider.md
│   ├── typing-context.md
│   ├── suggestion-selection.md
│   └── keyboard-layout-003.md
└── tasks.md             # /speckit-tasks (next)
```

### Source Code (repository root)

```text
gazekey/
├── prediction/                    # NEW
│   ├── __init__.py
│   ├── word_provider.py           # Protocol
│   ├── trie_provider.py           # Default implementation
│   ├── typing_context.py          # Prefix + epoch
│   ├── suggestion_dispatch.py     # suffix → KeyActions
│   └── data/
│       ├── words_en.txt           # Bundled frequency list (licensed)
│       └── README.md              # Source + license note (or equivalent)
├── typing/                        # EXTEND
│   ├── gaze_typing_runtime.py     # suggestion:* dwell path
│   └── key_semantics.py           # suggestion role (if needed)
├── ui/                            # MODIFY
│   ├── keyboard_layout.py         # Simplified layout
│   └── virtual_keyboard.py        # Wire prediction + cleanup
└── layout/
    └── layout_inspector.py        # suggestion gazeTarget export

tests/
├── unit/
│   ├── test_word_provider.py      # NEW
│   ├── test_typing_context.py     # NEW
│   ├── test_suggestion_dispatch.py# NEW
│   └── test_layout_geometry.py    # EXTEND (suggestion slots)
└── contract/
    └── test_suggestion_typing_path.py  # NEW
```

**Structure Decision**: Add `gazekey/prediction/` for FR-009 modularity; extend
existing typing/UI packages rather than new top-level app.

## Implementation phases (for tasks.md)

### Phase A — UI cleanup & geometry gate

- Remove product controls per FR-008
- Redistribute layout (research R7)
- Fix suggestion bar clipping
- Remove symbols layout product path
- Preserve `tools.preview`
- **Gate**: geometry tests pass

### Phase B — Prediction core

- Choose/document licensed word list; ship `words_en.txt` + provenance note
- `WordProvider` + trie with efficient top-3 frequency retrieval (R2)
- `TypingContext` + dispatcher subscription (delivery-only; no post-batch clear)
- Unit tests: provider API, quality smoke prefixes, context updates, Shift
  casing regression for suggestion accept

### Phase C — Suggestion UI + gaze selection

- Enable suggestion buttons as gaze targets
- Refresh bar from context
- `GazeTypingRuntime` suggestion branch + epoch guard
- Suffix + Space dispatch; context via deliveries only

### Phase D — Integration & quickstart

- End-to-end product path
- Quickstart sections A–G
- No mapping config changes

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
