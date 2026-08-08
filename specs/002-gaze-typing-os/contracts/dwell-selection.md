# Contract: Dwell Selection

**Version**: 1.2.0  
**Feature**: `002-gaze-typing-os`

## Purpose

Reliability-first dwell timing, cancel, same-key lock, pause, Shift arm/clear,
and global activation cooldown.

## Parameters (fixed for 002)

| Name | Value |
|------|-------|
| `dwell_sec` | **0.9** |
| `post_activation_cooldown_sec` | **0.20** global after successful dwell-based activations that change typing state |
| Same-key lockout | Until confirmed leave (OS-bound typing keys) |
| `leave_confirm_frames` | **5** consecutive off-key frames |

## Cooldown scope

Apply **0.20 s** cooldown consistently after successful dwell completion of:

- OS-bound typing keys (letter / space / backspace / enter)
- **Shift** (oneshot arm)
- **Pause** and **Resume**

Exempt a control only if implementation evidence documents a specific reason.

## Behavior

1. Stable `target_key_id` + session `active` → accumulate dwell time (subject to
   cooldown gate).
2. Leave before completion → reset (cancel).
3. Completion on OS-bound key → `KeyAction` via dispatcher; `fired_lock` on that
   key; start cooldown.
4. Re-arm same key only after 5 consecutive frames with hit-test ≠ locked key.
5. Shift dwell success → arm oneshot + cooldown; no OS CHAR from Shift itself.
6. Pause/Resume dwell success → toggle session + cooldown; clear Shift on Pause;
   no OS `KeyAction`.
7. `paused` → no OS-bound KeyAction requests.
8. Clear `shift_oneshot_armed` on: letter consume, Pause, recalibration,
   mapping/session reset, tracking/mapping session termination, and similar
   unsafe transitions.

## Visual feedback (on existing key geometry)

- Current gaze key: visible colored border/highlight
- Semi-transparent circular progress ring on that key over `dwell_sec` (0.9 s)
- Full circle = selection/activation
- Leave before completion → hide/reset ring; no selection
- Move to another key → restart the same process there
- Preserve existing keyboard layout/geometry (no redesign)

## Non-goals

- Intent scoring, cross-row hysteresis, Ctrl/Alt chords
- Keyboard redesign/reposition (dwell visuals overlay existing key geometry only)
