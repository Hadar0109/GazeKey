# Data Model: Gaze Typing & OS Integration

**Feature**: `002-gaze-typing-os`  
**Date**: 2026-08-08 (revised)

Upstream calibration/mapping entities remain as in
`specs/001-calibration-mapping-mvp/data-model.md` and are **unchanged** by this
feature. This document adds typing/OS entities only.

## Entities

### MappedGazePoint

| Field | Type | Notes |
|-------|------|-------|
| x, y | float | After predict + gaze smooth |
| valid | bool | False when tracking/mapping unavailable |

Typing never writes mapping weights.

### ActiveTypingKey (OS-bound)

| Field | Type | Notes |
|-------|------|-------|
| key_id | str | Stable id |
| label | str | UI label |
| role | enum | `letter`, `space`, `backspace`, `enter`, `shift_oneshot` |

**OS-bound set**: A–Z letters, Space, Backspace, Enter, Shift (one-shot arm only).

**Visible but non-OS**: Ctrl, Alt (and suggestions/lang/symbols/chrome) — not
ActiveTypingKey for dispatch.

### SystemControl

| Field | Type | Notes |
|-------|------|-------|
| control_id | str | e.g. `pause_resume` |
| kind | enum | `PAUSE_RESUME` |

Never becomes an OS-bound `KeyAction`.

### DwellIntent

| Field | Type | Notes |
|-------|------|-------|
| target_key_id | str \| null | |
| progress_01 | float | 0–1 |
| phase | enum | `idle`, `progressing`, `fired_lock`, `cancelled` |
| frames_off_target | int | Confirmed-leave counter |

### TypingSession (runtime state in product)

| Field | Type | Notes |
|-------|------|-------|
| state | enum | `inactive`, `active`, `paused` |
| shift_oneshot_armed | bool | True after Shift until next letter consumes it **or** a clear rule fires |

**Clear `shift_oneshot_armed` when**:

- next letter consumes it
- Pause
- recalibration (typing session reset)
- mapping/session reset (mapper cleared / new session / failed gate clearing model)
- tracking/mapping session termination
- other transitions where a stale arm could cause unexpected later uppercase
| last_fired_key_id | str \| null | Same-key lock |

**Transitions**:

```text
inactive --(mapping passed)--> active
active   --(Pause)--> paused
paused   --(Resume)--> active
* --(mapping cleared / recalibrate)--> inactive
```

### KeyAction (requested)

| Field | Type | Notes |
|-------|------|-------|
| kind | enum | `CHAR`, `BACKSPACE`, `ENTER` |
| text | str \| null | For `CHAR` |
| source | enum | `dwell`, `mouse` |
| key_id | str | |
| timestamp | float | |

Shift itself does not emit a lasting OS character action; it arms
`shift_oneshot_armed`. The following letter `KeyAction` carries the shifted
character when armed.

### ActionRequest / ActionDelivery (observer view)

| Entity | Meaning |
|--------|---------|
| ActionRequest | Dispatcher accepted a KeyAction for delivery attempt |
| ActionDelivery | Adapter result for that KeyAction (`ok` / `error`) |

Observers MUST be able to see requests that never delivered successfully.

### OsInjectResult

| Field | Type | Notes |
|-------|------|-------|
| ok | bool | |
| error | str \| null | |

## Relationships

```text
MappedGazePoint --> hit-test --> key?
key in OS-bound set + session active --> DwellIntent|mouse --> KeyAction (request)
KeyAction --> ActionDispatcher --> OsInputAdapter --> ActionDelivery
SystemControl --> TypingSession only
Shift --> arms oneshot; next letter CHAR may be uppercase
```

## Invariants

1. No KeyAction during calibration fixation.
2. No OS inject except via dispatcher → adapter.
3. Same key cannot fire again until 5-frame confirmed leave after lock.
4. `paused` → no ActionRequest for typing keys.
5. Ctrl/Alt never produce ActionRequest/OS inject in 002.
6. Calibration/mapping entities/fit path unchanged.
7. Pending Shift clears on Pause / recalib / session reset / termination (not only
   on letter consume).
