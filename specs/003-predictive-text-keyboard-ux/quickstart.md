# Quickstart: Predictive Text & Keyboard UX

**Feature**: `003-predictive-text-keyboard-ux`  
**Date**: 2026-08-10

Manual validation after implementation. Does **not** require `001` key-hit
floors. Does **not** retune calibration/mapping.

## Prerequisites

- Windows, webcam working
- External editor (Notepad) in lower half; GazeKey top-half keyboard
- `python main.py` product path
- Optional: `python -m tools.preview` for developer preview check

## A. Geometry gate (after UI redistribution)

1. Launch `python main.py`; complete fullscreen calibration
2. Confirm product keyboard shows:
   - Calibrate + window chrome only (no Pause, Preview, lang, status text,
     typed-text bar)
   - Suggestion bar with up to 3 slots, **fully visible** (not clipped)
   - No Ctrl/Alt; no symbols layout
   - No empty dead rows
3. Run automated geometry tests:

```bash
python -m pytest tests/unit/test_layout_geometry.py tests/test_keyboard_geometry_targets.py -q
```

**Pass**: all geometry tests green; visual inspection matches contract
`keyboard-layout-003.md`.

## B. Prefix tracking (internal only)

1. Focus Notepad; type `hel` by gaze dwell on keys
2. Confirm suggestions appear (≥1 of hello/help-class words)
3. Backspace once → suggestions update for `he`
4. Space → suggestions clear / empty
5. Type in Notepad with physical keyboard while GazeKey idle → GazeKey prefix
   does **not** change until next GazeKey action (expected divergence)

## C. Suggestion accept

1. Type `hel` by gaze
2. Dwell on a visible suggestion (e.g. `hello`)
3. **Pass**: Notepad shows `hello ` (suffix `lo` + trailing space) without typing
   remaining letters individually
4. With Shift armed and prefix `hel`, accept `hello` → still lowercase `hello `
   (no mixed casing); Shift cleared
5. Repeat with mouse click on suggestion if mouse parity enabled

## D. Normal typing unaffected

1. Ignore suggestions; type `test` key-by-key → `test` in Notepad
2. Type word with no dictionary match → empty suggestion slots; typing works
3. Shift one-shot + letter still works; Shift clears on recalibrate

## E. Stale-suggestion guard (smoke)

1. Begin dwell on a suggestion
2. Before dwell completes, complete a key that changes prefix (harder manual
   test) OR rely on unit test for epoch guard
3. **Pass** (unit): stale epoch produces zero dispatch

## F. Developer preview preserved

```bash
python -m tools.preview
```

Complete calibration; confirm mapped-gaze preview works **without** product
Preview button.

## G. Mapping isolation

- Do **not** change `gazekey/mapping/config.py` for this feature
- Optional sanity: `python -m tools.evaluation` still runs independently

## Automated test sweep (before merge)

```bash
python -m pytest tests/unit/test_typing_context.py tests/unit/test_word_provider.py tests/unit/test_suggestion_dispatch.py tests/unit/test_layout_geometry.py tests/unit/test_prediction_modularity.py tests/contract/test_typing_dispatch_path.py tests/contract/test_suggestion_typing_path.py -q
```

Then full-project regression:

```bash
python -m pytest -q
```

(Exact new test module names per `tasks.md`.)

**Note**: Automated tests do **not** claim live webcam gaze or external-app
typing passed. Those require USER GATE confirmation (quickstart live sections).
