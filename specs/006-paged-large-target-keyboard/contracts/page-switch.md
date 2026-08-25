# Contract: Page switch

**Version**: 1.2.0  
**Feature**: `006-paged-large-target-keyboard`

## Purpose

Gaze/mouse selection of the letter-page arrow without OS typing (FR-004,
FR-005, FR-012, FR-019, FR-020).

## Layout targets

| Current page | key_id | Label | Side | Effect |
|--------------|--------|-------|------|--------|
| left | `system:page_right` | `→` | right of letter area | show right page |
| right | `system:page_left` | `←` | left of letter area | show left page |

- `objectName`: `gazeTarget`
- Exactly **one** arrow widget, spanning the **first two** letter rows
- Not a letter `keyboardKey`

## Selection flow

```text
dwell/mouse complete on system:page_right or system:page_left
  -> no KeyAction, no OS injection, no TypingContext update
  -> apply existing activation cooldown (same family as Calibrate)
  -> cancel in-progress dwell
  -> synchronously remove previous-page letter-area widgets from the
     inspected tree (unparent / takeAt). Do not rely solely on deleteLater()
  -> drop host refs for previous-page letters / old arrow
  -> rebuild letter-area widgets for the destination page
  -> restore Shift visual state from TypingSession
  -> export_keyboard_layout in this same switch (refresh _layout_keys)
```

When the switch function returns, previous-page letters MUST already be
absent from `inspect_keyboard_layout` and `hit_test_layout_keys`.

## Dwell parameters

Same as keys: **0.9 s** dwell, **0.20 s** cooldown, same-key lockout,
**5-frame** leave, **0.25 s** key-switch confirmation.

`gazekey/typing/dwell_engine.py` MUST NOT change. Page-switch is another
dwellable control id, not a new dwell mode.

## Producer rules

- `GazeTypingRuntime` handles `system:page_*` like Calibrate: callback, no
  dispatcher OS path
- Optional mouse click uses the same callback
- Armed one-shot Shift is preserved across the rebuild
- Suggestion prefix/epoch is preserved
- Rapid re-activation of the new page’s arrow is gated by existing lockout +
  cooldown (no double-flip from one hold)
- In-progress letter **or suggestion** dwell is cancelled; a completed
  arrow MUST NOT publish the previous letter and MUST NOT dispatch a
  suggestion
- Automated test MUST switch page and **immediately** verify previous-page
  letters are absent from export/hit-test (tasks T013 checkpoint)

## Isolation

- MUST NOT import or call GazeFollower internals
- MUST NOT change prediction ranking or `TypingContext` transition rules
- MUST NOT deliver Space, Backspace, Enter, or a character
