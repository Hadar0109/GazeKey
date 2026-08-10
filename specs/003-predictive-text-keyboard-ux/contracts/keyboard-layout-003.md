# Contract: Product keyboard layout (003)

**Version**: 1.0.0  
**Feature**: `003-predictive-text-keyboard-ux`

## Purpose

Functional geometry for simplified product keyboard (FR-008, FR-011).

## Product surface (required regions)

| Region | key_id prefix | Notes |
|--------|---------------|-------|
| Control | `system:calibrate`, window chrome | No gaze-status text |
| Suggestions | `suggestion:0..2` | Max 3; fully visible |
| Letters | `r{row}c{col}:{char}` | Enlarged vs 002 |
| Editing | Shift, Backspace, Space, Enter | OS-bound per 002 |

## Removed from product (MUST NOT appear)

- `system:pause_resume`, Preview, lang, symbols, Ctrl, Alt
- Typed-text display row
- Symbols layout (`switch_layout('symbols')` product path deleted)
- Gaze-status label in chrome

## Geometry invariants

1. `inspect_keyboard_layout(root)` rows match on-screen `QPushButton` bounds
2. `KeyHitTester.hit_test` and `hit_test_layout_keys` agree on centers
3. Calibration semantic rows updated: drop `control` clutter keys; keep
   `suggestions`, `letters1-3`, `actions` aligned with export
4. Top-half window placement unchanged (002 geometry policy)
5. No empty layout rows after removals

## Regression tests (required after implement)

- `tests/unit/test_layout_geometry.py`
- `tests/test_keyboard_geometry_targets.py`
- New: suggestion slot hit-test coverage

## Non-product paths preserved

- `python -m tools.preview` layout may differ; product contract applies to
  `python main.py` keyboard only
