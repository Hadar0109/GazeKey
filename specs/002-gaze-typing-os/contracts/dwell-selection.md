# Contract: Dwell Selection

**Version**: 1.3.0  
**Feature**: `002-gaze-typing-os`

## Purpose

Reliability-first dwell timing, cancel, same-key lock, **key-transition
confirmation (hysteresis)**, pause, Shift arm/clear, and global activation
cooldown.

## Parameters (fixed for 002)

| Name | Value |
|------|-------|
| `dwell_sec` | **0.9** |
| `post_activation_cooldown_sec` | **0.20** global after successful dwell-based activations that change typing state |
| Same-key lockout | Until confirmed leave (OS-bound typing keys) |
| `leave_confirm_frames` | **5** consecutive off-key frames (post-fire re-arm only) |
| `key_switch_confirm_sec` | **0.25** continuous confirmation before changing the active dwell key |

## Cooldown scope

Apply **0.20 s** cooldown consistently after successful dwell completion of:

- OS-bound typing keys (letter / space / backspace / enter)
- **Shift** (oneshot arm)
- **Pause** and **Resume**

Exempt a control only if implementation evidence documents a specific reason.

## Behavior

1. Stable `target_key_id` + session `active` → accumulate dwell time (subject to
   cooldown gate).
2. **Key-transition confirmation (selection stability only)**:
   - A brief raw hit-test change away from the current dwell key MUST NOT
     immediately switch the active target or cancel progress.
   - While a switch is pending: **freeze** dwell progress on the current key
     (do not accumulate); keep the **visual target** on the current key.
   - If gaze returns to the current key before `key_switch_confirm_sec`
     completes → **resume** the previous dwell progress.
   - If **one** different key remains continuously detected for
     `key_switch_confirm_sec` (0.25 s) → confirm the switch: cancel/reset the
     old key’s dwell, move visual feedback to the new key, start its 0.9 s
     dwell from zero.
   - Continuous off-key (`null`) for `key_switch_confirm_sec` → cancel dwell
     (no `KeyAction`).
   - Wandering among different keys without any single key held continuously
     for 0.25 s MUST NOT preserve the old partial dwell indefinitely — after
     0.25 s continuously away from the active key without a confirmed new
     target, cancel.
3. Completion on OS-bound key → `KeyAction` via dispatcher; `fired_lock` on that
   key; start cooldown.
4. Re-arm same key only after 5 consecutive frames with hit-test ≠ locked key
   (post-fire lock only — independent of key-switch confirmation).
5. Shift dwell success → arm oneshot + cooldown; no OS CHAR from Shift itself.
6. Pause/Resume dwell success → toggle session + cooldown; clear Shift on Pause;
   no OS `KeyAction`.
7. `paused` → no OS-bound KeyAction requests.
8. Clear `shift_oneshot_armed` on: letter consume, Pause, recalibration,
   mapping/session reset, tracking/mapping session termination, and similar
   unsafe transitions.
9. **Tracking / mapped-gaze loss** is **not** part of key-switch grace: cancel
   dwell immediately; emit no `KeyAction`.

## Visual feedback (on existing key geometry)

- Current **active** dwell key (not raw flicker): visible colored border/highlight
- Semi-transparent circular progress ring on that key over `dwell_sec` (0.9 s)
- Full circle = selection/activation
- Pending switch: keep ring/highlight on the current key with frozen progress
- Confirmed leave / cancel → hide/reset ring; no selection
- Confirmed switch to another key → restart the same process there from zero
- Preserve existing keyboard layout/geometry (no redesign)

## Non-goals

- Intent scoring, prediction, language models, Ctrl/Alt chords
- Advanced / cross-row intent hysteresis beyond this **minimal 0.25 s
  key-transition confirmation**
- Keyboard redesign/reposition (dwell visuals overlay existing key geometry only)
- Changing calibration, PCA4/mapping, mapped-gaze smoothing, or hit-test geometry
