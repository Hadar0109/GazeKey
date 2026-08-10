# Data Model: Predictive Text & Keyboard UX

**Feature**: `003-predictive-text-keyboard-ux`  
**Date**: 2026-08-10

Upstream entities from `001` (calibration/mapping) and `002` (typing/OS) remain
**unchanged in role**. This document adds prediction + keyboard-surface entities
only.

## Entities

### TypingContext

| Field | Type | Notes |
|-------|------|-------|
| prefix | str | In-progress word, lowercase canonical |
| prefix_epoch | int | Monotonic; increments on every prefix change |
| shift_armed | bool | Mirrored from `TypingSession` for casing |

**Source of truth**: `ActionDispatcher.on_action_delivered` with `ok=True`
only (FR-006a).

**Transitions**:

```text
(empty prefix)
  -- CHAR letter --> append
  -- CHAR space --> stay empty
  -- BACKSPACE --> noop

(non-empty prefix)
  -- CHAR letter --> append
  -- CHAR space --> clear prefix
  -- BACKSPACE --> pop last char (or empty)
  -- ENTER --> clear prefix
```

Suggestion completion has **no separate transition**. Suffix CHARs and trailing
Space update context through the same delivery rules above. Partial failure
leaves `prefix` as whatever letters were successfully delivered.

### WordSuggestion (logical)

| Field | Type | Notes |
|-------|------|-------|
| word | str | Full completion text |
| rank | int | 0 = best |
| suffix | str | `word[len(prefix):]` for dispatch |
| slot_index | int | 0..2 UI slot |

Not persisted; derived per refresh from provider + current prefix.

### SuggestionSet (ephemeral UI state)

| Field | Type | Notes |
|-------|------|-------|
| prefix_epoch | int | Must match `TypingContext.prefix_epoch` for accept |
| items | list[WordSuggestion] | 0..3 entries |
| slot_key_ids | list[str] | e.g. `suggestion:0` |

Empty slots: button remains in fixed geometry, blank/disabled, not dwellable;
no bar resize/reflow by count.

### SuggestionTarget (layout / hit-test)

| Field | Type | Notes |
|-------|------|-------|
| key_id | str | `suggestion:{slot_index}` |
| label | str | Display word |
| rect | QRect | From layout export |
| enabled | bool | False when slot empty |

Exported via `inspect_keyboard_layout` with `objectName="gazeTarget"`.

### SuggestionAccept (intent)

| Field | Type | Notes |
|-------|------|-------|
| slot_index | int | Which suggestion fired |
| word | str | Full word at accept time |
| prefix_epoch | int | Guard against stale accept |
| source | enum | `dwell` \| `mouse` |

Converted to sequential `KeyAction` CHARs + Space by `suggestion_dispatch`.

### TypingSession (002, product subset)

Product changes:

- `PAUSED` state **not reachable** from product UI (Pause removed)
- `shift_oneshot_armed` clear rules remain except Pause-triggered clear
  (removed from product)

### KeyAction (002, unchanged schema)

Suggestion completion emits normal `KeyAction` CHAR sequence; no new `kind`.

## Relationships

```text
ActionDispatcher.on_action_delivered (ok)
        │
        ▼
  TypingContext ──prefix──► WordProvider.suggest()
        │                        │
        │                        ▼
        │                  SuggestionSet
        │                        │
        ▼                        ▼
  prefix_epoch ◄─────── SuggestionTarget (layout)
                               │
                    dwell/mouse accept
                               │
                               ▼
                    SuggestionAccept
                               │
                               ▼
              KeyAction CHAR* + Space → ActionDispatcher
```

## Validation rules

- `len(SuggestionSet.items) <= 3`
- Suggestions shown only when `len(prefix) >= 2`
- Accept rejected when `accept.prefix_epoch != TypingContext.prefix_epoch`
- `suffix` must be non-empty OR word equals prefix (then dispatch Space only)
- Context evolves only via successful `KeyAction` deliveries (no post-batch
  `clear_prefix()`)
- Shift-armed + non-empty lowercase prefix: do not apply Shift to suffix only
  (see research R5); regression test required
