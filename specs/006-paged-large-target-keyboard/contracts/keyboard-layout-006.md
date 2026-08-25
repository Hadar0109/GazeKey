# Contract: Product keyboard layout (006)

**Version**: 1.2.0  
**Feature**: `006-paged-large-target-keyboard`

## Purpose

Functional geometry for the paged large-target product keyboard (FR-001–
FR-011, FR-015). Supersedes Feature 003 letter-region layout
(`keyboard-layout-003.md`) for the **letter area only**. Suggestion bar,
bottom-row Calibrate/Space/Enter, and chrome rules from 003 remain in force.

## Product surface

| Region | key_id | Notes |
|--------|--------|-------|
| Control | window chrome only | Minimize/close; no Calibrate in chrome |
| Suggestions | `suggestion:0..2` | Three fixed slots; fully visible; unused blank/disabled |
| Left letters | `r{row}c{col}:{char}` | Q W E R T / A S D F G / Z X C V plus Shift + Backspace |
| Right letters | `r{row}c{col}:{char}` | Y U I O P / H J K L / B N M plus Shift + Backspace |
| Page switch | `system:page_right` or `system:page_left` | One tall `gazeTarget` spanning the **first two** letter rows |
| Bottom actions | `system:calibrate`, Space, Enter | Full width under the letter area |

## Acceptance layout (research R1–R2)

Left page (default):

```text
[ minimize | close ]
[ suggestion_0 | suggestion_1 | suggestion_2 ]
[ Q W E R T |    →     ]   ← arrow is one strip beside the first two rows
[ A S D F G |          ]
[ Shift Z X C V ⌫      ]   ← third row full letter-area width
[ Calibrate (large) | Space | Enter ]
```

Right page:

```text
[ minimize | close ]
[ suggestion_0 | suggestion_1 | suggestion_2 ]
[     | Y U I O P ]
[  ←  | H J K L   ]
[ Shift B N M ⌫   ]
[ Calibrate (large) | Space | Enter ]
```

Relative sizing (not pixels):

- Letter pane : arrow pane stretch **5:1** on the first two rows (~17% of
  letter-area width for the arrow; test band 12–22%)
- Mean visible letter-key width **>** letter-area width / 10
- Arrow taller than a single letter key and spans the **first two** letter
  rows only (does not cover the third row)
- Keyboard is a top-of-screen overlay at **~70%** of available screen height
  (external app remains visible below; not full-screen)

## Geometry invariants

1. `inspect_keyboard_layout` bounds match on-screen buttons for the **visible**
   page.
2. `hit_test_layout_keys` agrees with those exported rects at key centers.
3. After a page switch, previous-page letters are absent from export and
   produce zero hits. Removal from the inspected widget tree MUST be
   **synchronous** and MUST complete **before** `export_keyboard_layout`.
   Do **not** rely solely on deferred Qt `deleteLater()`.
4. `typing_region_rect` includes visible letters, the arrow, suggestions,
   Shift/Backspace, and bottom Calibrate/Space/Enter.
5. Top-of-screen placement; ~70% available height; lower screen free for the
   external app (FR-015).
6. No empty dead rows.
7. Layout/export/semantic updates only — **no** GazeFollower/mapping retune.
8. `system:page_*` and `system:calibrate` are enabled `gazeTarget`s.

## Regression tests (required after implement)

- `tests/unit/test_layout_geometry.py` (extend)
- `tests/unit/test_paged_keyboard.py` (new): both pages’ letter sets, arrow
  id/side/direction, relative size band, Shift present on both pages,
  **immediate** hidden-letter isolation as a **rebuild checkpoint** (tasks
  T013 — switch then assert previous-page letters absent from export/hit-test
  without waiting on `deleteLater`)
- Suggestion slots still exported when blank/disabled

## Non-product paths

- `python -m tools.preview` may differ; this contract applies to
  `python main.py`
