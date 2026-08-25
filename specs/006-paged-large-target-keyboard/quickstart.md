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
production layout until this record exists. This is the SC-006
**keyboard-surface** intended-key/focus comparison — **not** a mapping
benchmark, and MUST NOT retune GazeFollower. Do **not** use `hello` here;
`hello` is the separate mixed-page typing check in §C.

**Fixed sequence** (12 trials; both pages’ letters; all three QWERTY rows;
first and last of each page-row). Use **exactly** this order before and
after paging:

`Q T A G Z V / Y P H L B M`

| Order | Intended | Page (after paging) | Row |
|------:|----------|---------------------|-----|
| 1 | Q | left | 1 |
| 2 | T | left | 1 |
| 3 | A | left | 2 |
| 4 | G | left | 2 |
| 5 | Z | left | 3 |
| 6 | V | left | 3 |
| 7 | Y | right | 1 |
| 8 | P | right | 1 |
| 9 | H | right | 2 |
| 10 | L | right | 2 |
| 11 | B | right | 3 |
| 12 | M | right | 3 |

1. Chin/head support on; suggestions unused; official GazeFollower
   calibration accepted as today
2. For each intended letter in that sequence, dwell and record **focus**
   (wrong-focus counts even if dwell does not fire)
3. Write
   `specs/006-paged-large-target-keyboard/baseline/full-qwerty-intended-key.md`
   with date, chin/head support, calibration accepted, and a 12-row table:

   | trial | intended key | focused key | correct/incorrect |
   |------:|--------------|-------------|-------------------|
   | 1–12 | … | … | correct or incorrect |

   Plus **total wrong-focus count** (number of incorrect trials).

**Pass**: the baseline file exists with all 12 trials and is the SC-006
`eval_before`. Later paged comparison (§C2) MUST use this file, the same
sequence, and the same conditions — not memory of the old layout.

## A. Geometry gate (after paged layout)

1. Launch `python main.py`; complete official GazeFollower calibration
2. Confirm the keyboard opens on the **left** letter page:
   - Letters: QWERT / ASDFG / ZXCV with Shift and Backspace on the third row
   - Tall **→** on the **right** of the letter area (one strip, not three)
   - No YUIOP / HJKL / BNM visible
   - Suggestion bar, Calibrate | Space | Enter, minimize/close unchanged
3. Confirm visible letters are clearly **larger** than the old full-QWERTY
   letters (same window size)
4. Run (must include T013 immediate stale-target isolation):

```bash
python -m pytest tests/unit/test_layout_geometry.py tests/unit/test_paged_keyboard.py -q
```

5. Focus Notepad; dwell **2–3 left-page letters** (for example Q, A, Z)
   through the existing typing path. This is a small US1 live dwell-to-OS
   gate — **not** the §C `hello` word and **not** the §C2 SC-006 sequence.

**Pass**: tests green; layout matches `contracts/keyboard-layout-006.md`;
those 2–3 letters appear in Notepad.

## B. Page switch (no OS character)

1. Dwell on **→** until selection completes
2. **Pass**: right page shown (YUIOP / HJKL / BNM, Shift + Backspace);
   tall **←** on the **left**; left-page letters gone; Notepad unchanged
3. Click **←** (optional mouse parity) → left page returns; still no character
4. Rapid hold on the arrow must not flip twice without leave + new dwell

## C. Mixed-page typing (`hello`) USER GATE (SC-003)

End-to-end practical typing. **Not** the SC-006 intended-key comparison
(that is §A0 / §C2).

1. Focus Notepad; chin/head support on; suggestions unused
2. Type `hello` by gaze, switching pages as needed (H on the right page,
   E on the left page, and so on)
3. Backspace and Space still work on both pages
4. Arm Shift on one page, switch pages, dwell a letter → one-shot still
   applies; Shift does not stay armed

**Pass**: Notepad shows `hello` (or `hello ` if Space was used). Page
switches must not inject characters by themselves.

## C2. SC-006 paged intended-key comparison (same sequence as A0)

Repeat **exactly** the §A0 sequence and conditions on the paged keyboard.
Switch pages as needed so each intended letter is a **visible** target.
This remains a keyboard-surface interaction comparison only — not a
mapping benchmark, and MUST NOT retune GazeFollower.

1. Chin/head support on; suggestions unused; same official GazeFollower
   calibration condition as A0 (no backend changes)
2. Intended letters, in order: `Q T A G Z V / Y P H L B M`
3. Record `specs/006-paged-large-target-keyboard/baseline/paged-intended-key.md`
   with the same 12-row table as A0 (trial, intended key, focused key,
   correct/incorrect) plus total wrong-focus count
4. **Pass**: total wrong-focus count is **lower than the A0 file** (SC-006).
   If it is not, do **not** retune GazeFollower to compensate. Do **not**
   substitute `hello` for this comparison.

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
paging. SC-006 uses the A0 recorded 12-letter baseline vs §C2, not memory
and not the `hello` typing check.
