# Focus validation log (T034 / T035)

**Feature**: `002-gaze-typing-os`  
**Date**: 2026-08-08  
**Branch**: `002-gaze-typing-os`  
**Scope**: quickstart.md §B — early Windows focus gate via minimal
KeyAction → ActionDispatcher → PynputOsInputAdapter path.

**Overall**: **PASS** (T034). T035 mitigation **not required**.

---

## Method

Harness: `tools/focus_validation.py`

1. Lower-half external `QPlainTextEdit` stand-in for an external editor
   (Notepad-equivalent OS focus target; same process, separate top-level window)
2. Product `VirtualKeyboard` shown at **current top-half** geometry
   (`full_keyboard_size` = full width × 0.62 height, `position_at_top`) —
   auto-calibration suppressed so the inject skeleton can be exercised without
   changing calib/PCA4 behavior
3. Fullscreen calib-like overlay (same window flags as product overlay:
   Frameless + StaysOnTop + Tool) shown/activated then closed
4. **No** re-activation of the external target after the overlay cycle
5. Inject `"hi"` via `ActionDispatcher` + `PynputOsInputAdapter` with **no**
   focus restore between characters

## Results

| Check | Result | Evidence |
|-------|--------|----------|
| Top-half keyboard geometry preserved | **PASS** | `geo=(0,0 1280x416)` on available `1280×672`; expected height ≈416 |
| Focus remains on external target after calib-like overlay cycle | **PASS** | `focus_after_calib_cycle=QPlainTextEdit` |
| Inject delivery (`ok=true`) for each character | **PASS** | `delivered=[True, True]` |
| Characters appear in external target | **PASS** | `target_text='hi'` |
| Characters do **not** land in keyboard `QLineEdit` | **PASS** | `keyboard_text_display=''` |
| **§B overall** | **PASS** | `PASS=True` (exit 0) |

Command:

```text
PYTHONPATH=. python tools/focus_validation.py
```

## T035

Not applied. First-run validation **PASS**ed with existing window flags
(`FramelessWindowHint | WindowStaysOnTopHint | Tool`) and current top-half
geometry. No OS/window-level mitigation and no layout redesign/reposition.

## Stop

Phase 5 (T036+) remains gated only by this PASS — ready when scheduled.
Do **not** start dwell / Pause / Shift / full gaze typing in this batch.
