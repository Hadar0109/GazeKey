# Contract: Typing context

**Version**: 1.0.0  
**Feature**: `003-predictive-text-keyboard-ux`

## Purpose

Internal prefix tracking for prediction (FR-006, FR-006a).

## State

```text
TypingContext
  prefix: str              # lowercase in-progress word
  prefix_epoch: int        # increments on every prefix mutation
  shift_armed: bool        # mirrored from TypingSession
```

## Subscription

```text
on_action_delivered(action, result):
  if not result.ok:
    return   # no context mutation on failure

  match action.kind:
    CHAR letter  -> append lowercase letter to prefix
    CHAR space   -> clear prefix; epoch++
    BACKSPACE    -> pop last char if prefix non-empty; epoch++
    ENTER        -> clear prefix; epoch++
```

Suggestion completion does **not** call a separate `clear_prefix()`. Suffix
letters and trailing Space evolve/clear the prefix through the same delivery
rules. Partial failure leaves context consistent with delivered characters.

## Query

```text
get_prefix() -> str
get_epoch() -> int
```

## Rules

- MUST NOT read external application text
- MUST NOT update on `on_action_requested` alone
- `prefix_epoch` increments on every prefix clear or single-char mutation
- MUST NOT double-update via a post-batch clear after suggestion accept

## Test contract

- Type `h`,`e`,`l` → prefix `"hel"`
- Backspace → `"he"`
- Space → `""`
- Failed inject → prefix unchanged
- Suggestion accept of `hello` after `hel` with successful `l`,`o`,` ` →
  prefix becomes `""` via Space delivery only (no extra clear)