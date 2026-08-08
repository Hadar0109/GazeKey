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

---

## Quickstart §C notes (T050) — 2026-08-08

Live webcam short-word gaze typing (§C steps 1–7) requires an operator and
was **not** executed in this agent batch.

| SC / check | Automated / harness status |
|------------|----------------------------|
| SC-007 request vs delivered | **PASS** — `tests/contract/test_typing_dispatch_path.py` |
| Dwell → KeyAction → FakeOsInputAdapter | **PASS** — contract + unit suites |
| Mouse same path | **PASS** — contract test |
| Paused → no OS inject | **PASS** — contract test |
| Delivery failure non-blocking UI | **PASS** — `test_delivery_failure_shows_nonblocking_status` |
| Focus path (§B) | **PASS** — earlier T034 log |
| Live ≥4-char gaze word into Notepad | **PENDING operator** |
| Live Pause/Resume / Shift / Ctrl-Alt | **PENDING operator** |

## T050 usability revision — key-switch confirmation (2026-08-08)

After the first manual §C run, mid-dwell target transitions were revised:

- Keep 0.9 s dwell, 0.20 s post-fire cooldown, 5-frame post-fire re-arm.
- Add **0.25 s** continuous key-switch confirmation (selection/dwell layer only).
- Brief raw hit-test flicker MUST NOT immediately switch/cancel.
- Tracking/mapped-gaze loss still cancels immediately (no grace).

Docs: `contracts/dwell-selection.md` v1.3.0, spec FR-002/003/004, research R3,
plan, data-model, quickstart.

**T050 remains incomplete** until operator re-runs §C against this behavior.
Upstream mapping accuracy can cause unintended keys; that is **not** treated as a
dwell/typing regression and must **not** be “fixed” via calib/mapping changes in
this feature. T051–T054 proceeded per product schedule with T050 still pending.

---

## T051–T054 post-typing focus validation — 2026-08-08

**Overall**: **PASS** after full typing integration.

### Scope

- **T051**: Confirm/preserve fullscreen calib + top-half keyboard geometry (no redesign).
- **T052**: OS/window focus hardening (`WindowDoesNotAcceptFocus`, `WA_ShowWithoutActivating`, host `NoFocus`) — no geometry change.
- **T053**: Key/chrome widgets `NoFocus` so optional mouse clicks do not permanently capture the external typing target.
- **T054**: Re-run `tools/focus_validation.py` after typing wiring; this log section.

### Method (extended harness)

Same as T034, plus:

1. Assert keyboard window flags include `WindowDoesNotAcceptFocus` + show-without-activating
2. Optional `QTest.mouseClick` on letter key `a` before inject
3. Geometry check still expects top-half (`0.62` height, `position_at_top`)

### Results

| Check | Result | Evidence |
|-------|--------|----------|
| Top-half keyboard geometry preserved | **PASS** | `geo=(0,0 1280x416)` expected_h≈416 |
| Focus hardening flags | **PASS** | `focus_hardening_ok=True` |
| Mouse click does not leave keyboard active | **PASS** | `mouse_click_keeps_external_focus=True` |
| Focus on external target before inject | **PASS** | `focus_after_calib_cycle=QPlainTextEdit` |
| Inject delivery (`ok=true`) | **PASS** | `delivered=[True, True]` |
| Characters in external target | **PASS** | `target_text='hi'` |
| Characters not in keyboard status field | **PASS** | `keyboard_text_display=''` |
| **§B overall (post-typing)** | **PASS** | `PASS=True` (exit 0) |

Command:

```text
PYTHONPATH=. python tools/focus_validation.py
```

Deviation noted during T061: one earlier run saw `inject ok` with empty
`target_text` when restore after mouse was conditional on Qt `focusWidget` only —
Windows foreground can diverge. Harness always restores once after optional mouse;
3 consecutive reruns **PASS**. See `quickstart-results.md`.
