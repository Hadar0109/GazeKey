# Contract: Suggestion selection

**Version**: 1.0.0  
**Feature**: `003-predictive-text-keyboard-ux`

## Purpose

Gaze/mouse selection of a word suggestion through the existing dwell path.

## Layout targets

| key_id | Role |
|--------|------|
| `suggestion:0` | Best candidate slot |
| `suggestion:1` | Second slot |
| `suggestion:2` | Third slot |

- `objectName`: `gazeTarget` (exported in layout geometry)
- Exactly three slots with **fixed positions and fixed geometry**
- Empty/unused slot: blank, disabled, not dwellable — **no** resize/reflow

## Selection flow

```text
dwell/mouse complete on suggestion:N
  -> read word label + prefix_epoch at dwell start
  -> if epoch stale: cancel (no dispatch)
  -> compute suffix = word[len(prefix):]   # e.g. hel + hello → "lo"
  -> if Shift armed and prefix non-empty: clear Shift without applying to suffix
  -> dispatch KeyAction CHAR* for suffix (lowercase) + CHAR Space
  -> TypingContext evolves only via those successful deliveries
     (letters append; Space clears) — no extra clear_prefix()
```

## Dwell parameters

Same as keys: **0.9 s** dwell, **0.20 s** cooldown, same-key lockout,
**5-frame** leave, **0.25 s** key-switch confirmation.

## Producer rules

- Suggestion targets use same `GazeTypingRuntime` path as keys
- MUST NOT call `pynput` or OS APIs directly
- MUST NOT bypass `ActionDispatcher`

## Delivery semantics (FR-005)

Example: prefix `hel`, word `hello`:

```text
KeyAction CHAR 'l'
KeyAction CHAR 'o'
KeyAction CHAR ' '   # space
```

External result: `hello ` (suffix `lo` + Space).

**Casing / Shift**: If one-shot Shift is armed and `prefix` is non-empty, clear
Shift and dispatch the suffix in lowercase (do not produce mixed casing such as
`helLo`). See research R5.

## Test contract

- Dwell suggestion with matching epoch → suffix+Space in fake adapter
- Stale epoch → zero requests
- Empty slot → not hit-testable / not dwellable
- Prefix `hel`, pick `hello` → external fake receives `lo ` (then Space)
- Shift armed + prefix `hel` + accept `hello` → still `lo ` lowercase; Shift
  cleared; **no** mixed casing (`helLo` must fail)
- Partial inject failure mid-suffix → context matches delivered chars only
  (no separate clear)