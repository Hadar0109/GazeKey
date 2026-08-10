# Quickstart gate log — 003-predictive-text-keyboard-ux

**Feature**: Predictive Text & Keyboard UX  
**Started**: 2026-08-10

## Automated geometry gate (T014)

**Command**:

```bash
python -m pytest tests/unit/test_layout_geometry.py tests/test_keyboard_geometry_targets.py -q
```

**Result**: **PASS** (2026-08-10) — geometry + related UI tests green (18 passed including focus/preview regressions).

Automated tests do **not** claim live webcam/OS typing passed.

## USER GATE T015 — tools preview + visual keyboard

**Ask user to confirm**:

1. Run `python -m tools.preview` (preview without product Preview button)
2. Visual check of redesigned keyboard (quickstart §A / FR-008b):
   - Calibrate + window chrome only (no Pause, Preview, lang, status text, typed-text bar)
   - Suggestion bar with 3 slots, fully visible
   - No Ctrl/Alt; no symbols layout; no empty dead rows

**Result**: **PASS** (2026-08-10) — user confirmed tools preview + visual keyboard check.

## USER GATE T030 — suggestion MVP live

**Ask user to confirm** (quickstart §C):

1. `python main.py`, calibrate, focus Notepad
2. Type `hel` by gaze → suggestions appear
3. Dwell a suggestion (e.g. `hello`) → Notepad shows `hello ` (suffix + Space)
4. Optional: Shift armed + prefix `hel` + accept → still lowercase `hello `; Shift cleared

**Result**: _pending user confirmation_

Automated tests MUST NOT claim live webcam or external-app typing passed.
