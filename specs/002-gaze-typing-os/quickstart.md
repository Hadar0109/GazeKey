# Quickstart: Gaze Typing & OS Integration

**Feature**: `002-gaze-typing-os`  
**Date**: 2026-08-08 (revised)

Manual validation after implementation. Does **not** require `001` key-hit floors.
**Do not** change keyboard layout/position for these checks.

## Prerequisites

- Windows, webcam working
- External editor usable in the **lower half**; GazeKey keeps **existing top-half**
  keyboard geometry
- Dependencies installed (`pynput` included)
- Approve OS accessibility/input prompts if shown

## A. Post-cleanup behavior gate (before new typing)

After package moves/deletes, confirm:

1. `python main.py` launches normally
2. **Fullscreen calibration** completes as today
3. Existing **PCA4** fit still produces mapped gaze (preview-via-tools or
   equivalent observe-only check acceptable)
4. Keyboard returns to **current top-half** geometry (unchanged)
5. Relocated **developer benchmark** still runs via its **independent tools entry**

Do not continue if this gate fails.

## B. Early focus validation (after minimal inject skeleton)

Requires KeyAction → ActionDispatcher → OsInputAdapter path.

1. Open Notepad; click the text area once
2. Launch product; complete fullscreen calibration
3. Confirm top-half keyboard geometry unchanged
4. Inject a few characters via the minimal path **without** clicking Notepad
   between characters
5. **Pass**: continuous inject into Notepad. **Fail**: apply the **minimum
   OS/window-only** fix (no layout redesign/reposition), **rerun** this section,
   and require **PASS** before §C. If the minimal fix still fails, **stop for
   review** (do not expand scope automatically). Documented mitigation without a
   passing rerun is not enough.

## C. Full product typing path (after focus PASS)

Requires usable mapper/mapped-gaze after calibration (normal calib produced a
runtime-capable mapper — **not** `001` thresholds). Typing auto-starts; no
Enable Typing step.

1. Type a short word (≥4 chars) by **gaze dwell only** (~0.9 s); confirm circular
   progress ring / key highlight on existing geometry; brief gaze jitter across
   neighboring keys MUST NOT flicker/cancel immediately (0.25 s switch confirm)
2. Pause / Resume via gaze; Pause emits no character; Shift clears on Pause
3. Same-key double: fire, clear leave (≥5 frames), return, dwell again
4. Shift one-shot then letter; confirm Shift clears after letter; also confirm
   Shift clears if Pause/recalibrate instead of typing the letter
5. Ctrl/Alt: no OS shortcuts
6. Optional mouse on a letter — same OS path
7. With no usable external target (e.g. desktop focus): simple non-blocking
   feedback; no crash; calib/mapping session preserved

## Developer tooling

- Preview and benchmark: **separate tools entry points** (not product modes)

## Automated checks

```text
pytest tests/unit -k "dwell or key_action or os_input or typing_session"
```

Expect: 0.9 s / 0.20 s activation cooldown / 5-frame post-fire leave /
0.25 s key-switch confirmation; request vs delivered;
Shift clear rules; pause; no Ctrl/Alt OS actions; fake adapter only.
