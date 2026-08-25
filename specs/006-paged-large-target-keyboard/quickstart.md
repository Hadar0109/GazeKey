# Quickstart: Paged Large-Target Keyboard

**Feature**: `006-paged-large-target-keyboard`  
**Date**: 2026-08-25

Manual validation. Section **A0** runs **before** production layout
changes. Later sections run after the paged keyboard exists. Does **not**
retune GazeFollower, calibration, mapping, dwell timing, or prediction.

Product condition: **chin/head support** for live gaze checks.

## Prerequisites

- Windows, project `.venv` on Python 3.11
- External editor (Notepad) in the lower half; GazeKey top-half keyboard
- `python main.py` product path

## A0. Pre-implementation full-QWERTY baseline (before any layout change)

Run this on the **current** full-QWERTY product keyboard. Do **not** change
production layout until this record exists. This is **not** a mapping
benchmark and MUST NOT retune GazeFollower.

1. Chin/head support on; suggestions unused; official GazeFollower
   calibration accepted as today
2. Focus Notepad; for each intended letter in `h e l l o`, dwell and record
   whether **focus** matched the intended key (wrong-focus counts even if
   dwell does not fire)
3. Write
   `specs/006-paged-large-target-keyboard/baseline/full-qwerty-intended-key.md`
   with date, condition, per-letter intended vs focused key, wrong-focus
   count

**Pass**: the baseline file exists and is the SC-006 `eval_before`. Later
paged comparison MUST use this file, not memory of the old layout.

## A. Geometry gate (after paged layout)

1. Launch `python main.py`; complete official GazeFollower calibration
2. Confirm the keyboard opens on the **left** letter page:
   - Letters: QWERT / ASDFG / ZXCV with Shift and Backspace on the third row
   - Tall **→** on the **right** of the letter area (one strip, not three)
   - No YUIOP / HJKL / BNM visible
   - Suggestion bar, Calibrate | Space | Enter, minimize/close unchanged
3. Confirm visible letters are clearly **larger** than the old full-QWERTY
   letters (same window size)
4. Run (includes immediate stale-target isolation):

```bash
python -m pytest tests/unit/test_layout_geometry.py tests/unit/test_paged_keyboard.py -q
```

**Pass**: tests green; layout matches `contracts/keyboard-layout-006.md`.

## B. Page switch (no OS character)

1. Dwell on **→** until selection completes
2. **Pass**: right page shown (YUIOP / HJKL / BNM, Shift + Backspace);
   tall **←** on the **left**; left-page letters gone; Notepad unchanged
3. Click **←** (optional mouse parity) → left page returns; still no character
4. Rapid hold on the arrow must not flip twice without leave + new dwell

## C. Mixed-page typing vs recorded baseline (USER GATE)

1. Focus Notepad; chin/head support on; suggestions unused
2. Repeat the **same** intended letters as A0: `h e l l o`, switching pages
   as needed
3. Record `specs/006-paged-large-target-keyboard/baseline/paged-intended-key.md`
   with the same per-letter intended vs focus fields
4. **Pass**: Notepad shows `hello` (or `hello ` if Space was used); wrong-focus
   count among these visible-letter trials is **lower than the A0 file**
   (SC-006). If it is not, do **not** retune GazeFollower to compensate.
5. Backspace and Space still work on both pages
6. Arm Shift on one page, switch pages, dwell a letter → one-shot still
   applies; Shift does not stay armed

## D. Suggestions still work

1. Type a prefix ≥ 2 that may use both pages (for example `he`)
2. **Pass**: up to three suggestions; accepting one still sends remaining
   suffix + Space through the existing path
3. Empty/disabled slots stay fixed; typing continues

## E. Minimize / recalibrate

1. Switch to the right page; minimize; restore → **still right page**
2. Recalibrate via bottom Calibrate; complete official GazeFollower flow
3. **Pass**: keyboard returns on the **left** page; GazeFollower UI was the
   official one (not a GazeKey copy)

## F. Isolation

- `git diff` on `gazekey/backend/`, `gazekey/typing/dwell_engine.py`, and
  `gazekey/prediction/` should be empty (except an agreed one-line keyboard
  callback at the existing recalibrate handoff, which this plan prefers to
  avoid)
- Do not run or retune Feature 004 mapping experiments as an acceptance gate

## G. Mapping isolation reminder

Independent mapping/GazeFollower benchmarks remain unchanged. Larger keys
are a **target-size** change. Do not add smoothing or remaps to “help”
paging. SC-006 uses the A0 recorded baseline, not memory.
