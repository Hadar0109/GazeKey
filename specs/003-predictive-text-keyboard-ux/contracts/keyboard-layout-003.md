# Contract: Product keyboard layout (003)

**Version**: 1.1.0  
**Feature**: `003-predictive-text-keyboard-ux`

## Purpose

Functional geometry for simplified product keyboard (FR-008, FR-011, FR-008d).

## Product surface (required regions)

| Region | key_id prefix | Notes |
|--------|---------------|-------|
| Control | window chrome only | Minimize/close; **no** Calibrate; no gaze-status text |
| Suggestions | `suggestion:0..2` | Exactly 3 fixed-geometry slots; fully visible; unused blank/disabled |
| Letters | `r{row}c{col}:{char}` | Enlarged vs 002; QWERTY preserved |
| Actions / editing | Shift, Backspace, Space, Enter, `system:calibrate` | Bottom row: large Calibrate left of Space |

## Bottom-row recalibration target (follow-up)

- Orange Calibrate/Recalibrate sits on the **bottom keyboard row**, **left of Space**
- Target MUST be **noticeably larger** than a normal letter key (width and, when
  vertical space allows, height)
- Space is reduced and visually centered in the remaining bottom-row span; Enter
  may be slightly smaller for balance
- Top chrome is slim (window controls only); reclaimed vertical space may enlarge
  letter-key rows
- Larger recalibrate target improves **recovery tolerance** only — **not** mapper
  accuracy; no PCA4/mapping/benchmark retune

## Removed from product (MUST NOT appear)

- `system:pause_resume`, Preview, lang, symbols, Ctrl, Alt
- Typed-text display row
- Symbols layout (`switch_layout('symbols')` product path deleted)
- Gaze-status label in chrome
- Calibrate button in the **top** control row (moved to bottom)

## Geometry invariants

1. `inspect_keyboard_layout(root)` rows match on-screen `QPushButton` bounds
2. `KeyHitTester.hit_test` and `hit_test_layout_keys` agree on centers
3. Calibration semantic rows updated: drop top-chrome Calibrate; keep
   `suggestions`, `letters1-3`, `actions` (incl. `system:calibrate`) aligned
   with export
4. Top-half window placement unchanged (002 geometry policy)
5. No empty layout rows after removals
6. Research **R7** (+ R7 follow-up) is the acceptance layout; key/recalibrate
   enlargement is not a mapping-accuracy requirement
7. Layout/export/semantic updates only — no calibration/PCA4/mapping retune
8. `system:calibrate` remains a real enabled `gazeTarget` (dwell/mouse)
9. Layout-export `typing_region_rect` is the union of exported product gaze
   targets (fixed suggestion slots + letter/editing keys + bottom Recalibrate /
   Space / Enter). Suggestion slots remain in that union when blank/disabled.
   Calibration still uses its own `letter_keys_region_rect` / key-center targets
   and is not retuned by this metadata region.

## Regression tests (required after implement)

- `tests/unit/test_layout_geometry.py`
- `tests/test_keyboard_geometry_targets.py`
- Suggestion slot hit-test coverage
- Bottom-row Calibrate placement + larger-than-letter hit-test coverage
- `typing_region_rect` contains suggestion row + intended product gaze targets

## Non-product paths preserved

- `python -m tools.preview` layout may differ; product contract applies to
  `python main.py` keyboard only
