# Contract: OS Input Boundary

**Version**: 1.1.0  
**Feature**: `002-gaze-typing-os`

## Purpose

Dedicated adapter between requested `KeyAction` and native OS input.

## Interface

```text
protocol OsInputAdapter:
  inject(action: KeyAction) -> OsInjectResult

OsInjectResult:
  ok: bool
  error: optional string
```

## Implementation

- **Product**: `PynputOsInputAdapter` (`pynput` import only here)
- **Tests**: `FakeOsInputAdapter`

## Mapping

| KeyAction | OS behavior |
|-----------|-------------|
| CHAR text | type character (already cased) |
| BACKSPACE | backspace |
| ENTER | enter/return |

No Ctrl/Alt chord injection in 002. Shift is handled as oneshot casing before
CHAR is built — adapter types the final character.

## Failure

- `ok=false` + short reason; non-blocking UI status allowed
- Must not corrupt calibration/mapping
- Must not crash gaze loop
- Dispatcher still emits `on_action_delivered` with failure

## Forbidden

- Dwell/UI importing this module’s `pynput` impl details
- Injecting Pause/Resume, Ctrl, Alt, or non-OS controls
