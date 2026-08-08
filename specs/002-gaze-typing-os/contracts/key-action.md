# Contract: KeyAction

**Version**: 1.1.0  
**Feature**: `002-gaze-typing-os`

## Purpose

Semantic selection result and dispatcher delivery semantics.

## Schema

```text
KeyAction
  kind: CHAR | BACKSPACE | ENTER
  text: optional string          # CHAR only (already cased if Shift oneshot armed)
  source: dwell | mouse
  key_id: string
  timestamp: float
```

## Producer rules

- Emit only for OS-bound keys: A–Z, Space, Backspace, Enter (Shift arms oneshot;
  does not itself require an OS CHAR)
- Emit only when `TypingSession.state == active`
- Do not emit for Pause/Resume, Ctrl, Alt, suggestions, language, symbols, chrome

## Dispatcher semantics

```text
publish(action):
  1. notify on_action_requested(action)     # selected / requested
  2. result = OsInputAdapter.inject(action)
  3. notify on_action_delivered(action, result)  # success or failure
```

Future observers MUST distinguish **requested** from **successfully delivered**
(`result.ok == true`).

## Consumer rules

- UI/dwell MUST NOT bypass dispatcher
- `pynput` only inside adapter

## Test contract

- Dwell completion → one requested KeyAction
- Fake adapter failure → requested fired, delivered with `ok=false`
- Pause → zero requests
- Ctrl/Alt → zero requests
