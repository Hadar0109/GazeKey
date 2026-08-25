# Data Model: Paged Large-Target Keyboard

**Feature**: `006-paged-large-target-keyboard`  
**Date**: 2026-08-25

Upstream entities from Feature 005 (GazeFollower screen gaze), Feature 002
(dwell / KeyAction / OS), and Feature 003 (TypingContext / suggestions)
remain **unchanged in role**. This document adds keyboard-page entities only.

## Entities

### LetterPage

| Field | Type | Notes |
|-------|------|-------|
| id | `"left"` \| `"right"` | Mutually exclusive visible letter set |
| letters_row1 | list[str] | left: `qwert`; right: `yuiop` |
| letters_row2 | list[str] | left: `asdfg`; right: `hjkl` |
| letters_row3 | list[str] | left: `zxcv`; right: `bnm` |

Only one `LetterPage` is instantiated as widgets at a time. The previous
page is synchronously removed from the inspected tree before export
(research R3).

### PageSwitchTarget

| Field | Type | Notes |
|-------|------|-------|
| key_id | str | `system:page_right` on left page; `system:page_left` on right page |
| label | str | `→` or `←` |
| side | `"left"` \| `"right"` | Visual placement in the letter area |
| direction | `"left"` \| `"right"` | Arrow meaning: reveal that page |
| role | system control | Never OS-bound |

Exported with `objectName="gazeTarget"`. Included in `typing_region_rect`
while visible.

### LetterPageState

| Field | Type | Notes |
|-------|------|-------|
| current | `"left"` \| `"right"` | Hosted on `VirtualKeyboard` |
| default | `"left"` | Launch and post-recalibrate |

**Transitions**:

```text
(current = left)
  -- activate system:page_right --> right
  -- official recalibrate return --> left
  -- minimize / restore --> left (unchanged)

(current = right)
  -- activate system:page_left --> left
  -- official recalibrate return --> left
  -- minimize / restore --> right (unchanged)
```

Page switch does **not** change `TypingContext.prefix`, `prefix_epoch`, or
`TypingSession.shift_oneshot_armed`. After widget rebuild, Shift **visual**
state is copied back from the session.

### VisibleTargetSet

| Field | Type | Notes |
|-------|------|-------|
| letters | set of letter key_ids | Current page only |
| page_switch | PageSwitchTarget | One arrow |
| persistent | suggestions, Shift, Backspace, Calibrate, Space, Enter, chrome | Present on both pages |

**Validation**:

- Hidden-page letters MUST NOT appear in layout export or live hit-test
- Previous-page widgets MUST be synchronously removed from the inspected
  tree before `export_keyboard_layout` (research R3); `deleteLater()` alone
  is not sufficient
- Disabled suggestion slots remain in export (Feature 003 rule) but are not
  dwellable
- Shift/Backspace MUST be in the set on both pages

### PersistentNonLetterControls

Unchanged Feature 003 controls that are not paged:

- `suggestion:0..2`
- `system:calibrate`
- Space, Enter
- Window minimize/close (not dwell typing keys)
- Shift, Backspace (paged-row placement, but available on both pages)

## Relationships

```text
LetterPageState.current
  --> LetterPage (widget tree)
  --> PageSwitchTarget (one)
  --> VisibleTargetSet
        --> live QRect export (_layout_keys)
        --> hit_test_layout_keys
        --> DwellEngine (unchanged)
              --> KeyAction only for OS-bound / suggestion / calibrate paths
              --> page-switch callback (no KeyAction)
```

## Invariants

1. Exactly one letter page visible.
2. Arrow side/direction match the current page (left page → right-side `→`).
3. Mean visible letter-key **width** exceeds letter-area width / 10
   (research R2). This is the SC-001 **area** proxy **only because
   letter-row height is unchanged**; it is not a second stretch factor.
4. After a page switch returns, previous-page letters are already absent
   from export/hit-test (synchronous unparent; not `deleteLater`-only).
5. GazeFollower sample fields and dwell timing are not part of this model.
