# Feature Specification: Paged Large-Target Keyboard

**Feature Branch**: `006-paged-large-target-keyboard`

**Created**: 2026-08-25

**Status**: Draft

**Input**: User description: "Improve practical gaze typing accuracy by
increasing the size of the keyboard targets, without changing the GazeFollower
backend. Instead of displaying the full QWERTY keyboard at once, split the
letter keys into two switchable pages: Left side QWERT / ASDFG / ZXCV; Right
side YUIOP / HJKL / BNM. Each page should contain a large vertical arrow
target for switching to the other page. Fewer visible keys should allow the
remaining keys to become significantly larger. Keep the existing
keyboard/external-app behavior, predictive suggestions, dwell typing, OS
input, and live QRect-based hit testing unchanged. GazeFollower, calibration,
gaze mapping, filtering, origin/DPR conversion, dwell behavior, and prediction
logic are out of scope and must not be modified."

**Guidance**: GazeKey Constitution **v1.4.0** (binding). This is a
**post-mapping keyboard-surface** feature. It consumes sealed screen-space
gaze from the Feature 005 GazeFollower backend and MUST NOT retune, filter,
remap, or otherwise compensate mapping to “fix” typing. Practical typing
improvement MUST come from **larger visible targets** and paging, not from
backend changes. Feature 004 remains a closed historical record and MUST
NOT be resumed, deleted, renumbered, or rewritten. Independent mapping
benchmarks MUST NOT be replaced or weakened by this feature’s acceptance.

Product condition remains **chin/head support** for any practical typing
checks defined here.

## Clarifications

### Session 2026-08-25

- Q1: How should visible letters and the page-switch arrow share the letter
  area? → A: **Expand letters; tall arrow strip toward the hidden page.**
  Visible letters fill most of the letter area. The arrow is a tall
  vertical strip on the side toward the other page: on the **left-letter
  page**, a tall right-pointing arrow on the **right**; on the
  **right-letter page**, a tall left-pointing arrow on the **left**. Exact
  arrow width and key-sizing ratios are a **planning** decision from the
  current available letter area. This specification MUST NOT hard-code
  pixel dimensions or fixed stretch ratios.
- Q2: Where do Shift and Backspace live? → A: **Visible on both pages**,
  still on the **third letter row** with that page’s letters (left: Shift |
  Z X C V | Backspace; right: Shift | B N M | Backspace). Suggestion slots,
  Calibrate, Space, Enter, and window chrome stay visible on both pages.
- Q3: Default page and persistence? → A: **Start on the left page**; keep
  the current page until the user switches; **reset to left** after launch
  and after recalibration; **keep the current page** across
  minimize/restore.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type On Larger Letter Targets (Priority: P1)

After calibration, the user sees the **left** letter page (not the full
QWERTY letter set). Those visible letter keys are substantially larger than
today’s all-at-once letter keys. The user dwells on a visible letter and it
is typed into the focused external application through the existing typing
path.

**Why this priority**: Larger targets are the reason for this feature.
Paging without a real size gain would not improve practical gaze typing.

**Independent Test**: Launch the product keyboard after calibration, confirm
the left letter page is shown, confirm those letter keys are clearly larger
than the current full-QWERTY letters, dwell on several visible letters, and
confirm they appear in the external application.

**Acceptance Scenarios**:

1. **Given** the product keyboard is shown after successful calibration or
   launch, **When** the user inspects the letter area, **Then** the **left**
   letter page is visible and the full QWERTY letter set is not shown at
   once.
2. **Given** the left letter page is visible, **When** the user inspects
   letter keys, **Then** the visible letters are Q, W, E, R, T on the first
   row; A, S, D, F, G on the second row; and Z, X, C, V on the third row.
3. **Given** the right letter page is visible, **When** the user inspects
   letter keys, **Then** the visible letters are Y, U, I, O, P on the first
   row; H, J, K, L on the second row; and B, N, M on the third row.
4. **Given** a letter page is visible, **When** the user compares those letter
   keys with the current full-QWERTY letter keys, **Then** the visible letter
   keys are significantly larger (see SC-001).
5. **Given** mapped gaze typing is active, **When** the user dwells on a
   visible letter key until selection completes, **Then** that letter is
   delivered to the focused external application through the existing typing
   path.

---

### User Story 2 - Switch Pages With a Large Arrow (Priority: P1)

Each letter page includes one large vertical arrow target. On the left page
it sits on the right and points right; on the right page it sits on the left
and points left. Dwelling on that arrow switches to the other page so the
user can reach the hidden letters. The arrow is a keyboard-page control: it
must be easy to hit by gaze and must not type a character into the external
application.

**Why this priority**: Without a reliable, large page-switch target, half of
the alphabet is unreachable.

**Independent Test**: From the left starting page, dwell on the right-side
arrow, confirm the right letter page appears with a left-side left-pointing
arrow, dwell on a right-page letter, then switch back and type a left-page
letter.

**Acceptance Scenarios**:

1. **Given** the left letter page is visible, **When** the user inspects the
   letter area, **Then** a tall vertical right-pointing arrow occupies the
   right side of that area, and the left-page letters occupy the remaining
   letter space to its left.
2. **Given** the right letter page is visible, **When** the user inspects the
   letter area, **Then** a tall vertical left-pointing arrow occupies the
   left side of that area, and the right-page letters occupy the remaining
   letter space to its right.
3. **Given** the left page is visible, **When** the user completes gaze dwell
   on the page-switch arrow, **Then** the right page becomes visible and the
   left-page letters are no longer shown or selectable.
4. **Given** the right page is visible, **When** the user completes gaze dwell
   on the page-switch arrow, **Then** the left page becomes visible and the
   right-page letters are no longer shown or selectable.
5. **Given** the user dwells on the page-switch arrow, **When** selection
   completes, **Then** no character or editing key is delivered to the
   external application.
6. **Given** optional mouse convenience is used on the arrow, **When** the
   user clicks it, **Then** the page switches with the same result as a
   completed dwell and still does not type into the external application.

---

### User Story 3 - Keep Existing Typing, Suggestions, And External-App Behavior (Priority: P1)

The paged keyboard is still the same GazeKey typing product: dwell typing,
OS delivery into the focused external application, three predictive
suggestion slots, Shift / Backspace / Space / Enter, and Calibrate remain
available. The user can ignore paging complexity for non-letter controls and
can still complete words with suggestions.

**Why this priority**: Larger letters must not regress the working Feature
002/003 product. A paged keyboard that breaks suggestions or OS typing is a
failure.

**Independent Test**: Type a short word that uses letters from both pages,
use Backspace and Space, accept a suggestion when one appears, and confirm
the external application receives the same kind of input as today.

**Acceptance Scenarios**:

1. **Given** typing is active, **When** the user dwells on Space, Backspace,
   Enter, or uses one-shot Shift then a letter, **Then** those actions behave
   as they do today and reach the external application through the existing
   typing path.
2. **Given** the user types a prefix of at least two letters, **When**
   suggestions are available, **Then** the three fixed suggestion slots still
   appear, update with the prefix, and can be selected by gaze to complete
   the word (remaining suffix + Space) in the external application.
3. **Given** suggestions are empty or ignored, **When** the user types only
   with letter and editing keys, including keys that required a page switch,
   **Then** character-by-character typing continues to work.
4. **Given** the user needs to recover calibration, **When** they select
   Calibrate/Recalibrate, **Then** the existing official GazeFollower
   recalibration flow still runs; this feature does not replace it.
5. **Given** the keyboard is shown over the top portion of the screen,
   **When** the user types, **Then** GazeKey still does not permanently steal
   the external typing target, and the lower-screen application remains the
   intended destination.

---

### User Story 4 - Only Visible Keys Are Live Targets (Priority: P2)

After a page switch, gaze must hit the keys that are actually on screen.
Hidden letters from the other page must not be selectable. Visible key bounds
and gaze hitboxes must stay synchronized, using the same live rectangle-based
hit testing the product already uses.

**Why this priority**: Stale or hidden hitboxes would type the wrong letter
and would look like a mapping failure even though mapping did not change.

**Independent Test**: Switch pages, confirm hidden letters cannot be selected
by gaze or click, confirm each visible letter/arrow/editing/suggestion target
selects only that control, and confirm a layout/geometry check still agrees
with the on-screen keys after the switch.

**Acceptance Scenarios**:

1. **Given** the left page is visible, **When** the user gazes at the screen
   region where a right-page letter would have been on the full QWERTY,
   **Then** that hidden letter is not selected; focus/dwell follows only
   currently visible enabled targets (including the arrow if it occupies
   that region).
2. **Given** a page switch has just completed, **When** dwell or click
   selection is used, **Then** visible key bounds and gaze hitboxes refer to
   the new page’s controls, not the previous page.
3. **Given** suggestion slots, Calibrate, Space, Enter, Shift, and Backspace
   are shown, **When** the letter page changes, **Then** those persistent
   controls remain gaze-selectable if they are still on screen, with
   synchronized hitboxes.
4. **Given** a dwell is in progress on a letter, **When** the user instead
   confirms gaze on the page-switch arrow, **Then** the in-progress letter
   dwell is handled by the existing dwell leave/switch rules; the completed
   arrow selection switches page and does not type the previous letter.

---

### Edge Cases

- Word that needs both pages (for example `hello`: H on the right page, E on
  the left page) → the user must switch pages mid-word; extra page-switch
  actions are the accepted cost of larger targets; typing and suggestions
  must remain consistent with dispatched keys.
- Page switch while a suggestion dwell is in progress → existing mid-dwell
  target-switch/cancel rules apply; a completed arrow selection must not
  accept a suggestion.
- Page switch while one-shot Shift is armed → Shift remains armed across the
  page change; the next completed letter still receives the one-shot shift.
- Rapid repeated arrow selections → same-target lockout and existing dwell
  cooldown apply so the keyboard does not flip pages twice from one hold.
- Minimize then restore → keyboard returns as a usable product keyboard
  on the **same letter page** that was showing before minimize.
- Recalibrate then return to the keyboard → GazeFollower calibration is
  unchanged; the keyboard returns on the **left** letter page.
- Hidden letter must never remain in the live hit-test set after a switch.
- Page-switch arrow must never inject a character, Space, Enter, or
  Backspace.
- No useful dictionary match / empty suggestions → blank/disabled suggestion
  slots as today; paging still works.
- User looks between two now-larger neighboring letters → existing dwell
  focus/switch confirmation applies; this feature must not add extra gaze
  smoothing or mapping correction to “help” boundary cases.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product keyboard MUST split English QWERTY **letter** keys
  into exactly **two** switchable pages rather than showing the full letter
  set at once.
- **FR-002**: The **left** page MUST show letter keys **Q W E R T** / **A S
  D F G** / **Z X C V** and MUST NOT show Y U I O P, H J K L, or B N M.
- **FR-003**: The **right** page MUST show letter keys **Y U I O P** / **H J
  K L** / **B N M** and MUST NOT show Q W E R T, A S D F G, or Z X C V.
- **FR-004**: Each page MUST include a **large vertical arrow** gaze target
  that switches to the other page. The arrow MUST span the letter-key rows
  vertically rather than appearing as a small chrome icon. On the
  **left-letter page**, the arrow MUST sit on the **right** side of the
  letter area and point **right**. On the **right-letter page**, the arrow
  MUST sit on the **left** side of the letter area and point **left**. The
  specification does not fix the arrow’s width in pixels; planning MUST
  choose a width from the live letter area so the arrow is a large,
  easy-to-hit gaze target while still leaving enough width for
  significantly larger letters.
- **FR-005**: Completing a page-switch (dwell or optional click) MUST change
  only which letter page is shown. It MUST NOT deliver OS input and MUST NOT
  alter prediction context by itself.
- **FR-006**: Visible letter keys MUST become **significantly larger** than
  the current full-QWERTY letter keys because fewer letters are shown.
  Enlargement MUST come from redistributing the existing letter-area space
  among the visible letters and the large arrow, **not** from enlarging the
  keyboard window, moving it, or changing screen coverage. Exact key-size
  and arrow-width **ratios** MUST be chosen during planning from the current
  available letter area. This specification MUST NOT hard-code pixel
  dimensions or fixed stretch ratios.
- **FR-007**: Visible letters MUST expand to fill most of the letter area
  beside the arrow. They MUST NOT be confined to a native QWERTY half that
  leaves the unused half empty. The arrow remains a distinct tall strip
  (FR-004) and MUST stay visually distinguishable from letter keys.
- **FR-008**: Shift and Backspace MUST remain visible on **both** letter
  pages, on the **third letter row** with that page’s letters (left: Shift |
  Z X C V | Backspace; right: Shift | B N M | Backspace). Suggestion slots,
  Calibrate, Space, Enter, and window chrome (minimize/close) MUST also
  remain visible on both pages. Users MUST NOT need a page switch only to
  reach Shift or Backspace.
- **FR-009**: The product keyboard MUST show the **left** letter page on
  launch and after returning from recalibration. The current page MUST
  persist until the user switches pages. Minimize then restore MUST restore
  the page that was showing before minimize. Recalibration MUST reset the
  page to **left**.
- **FR-010**: Hidden-page letters MUST NOT be visible, dwellable, clickable,
  or present in the live hit-test set. After every page switch, live
  hit-testing MUST use the currently visible enabled targets only.
- **FR-011**: Visible control bounds and gaze hitboxes MUST stay
  synchronized after layout, page switch, restore, and recalibrate-return.
  This is a **functional geometry** change: the existing live
  rectangle-based hit testing MUST continue to resolve gaze against the
  on-screen controls that are actually shown.
- **FR-012**: Existing dwell interaction MUST be reused for letters, the
  page-switch arrow, suggestions, and other already-dwellable controls.
  Dwell duration, same-key lockout, leave confirmation, global cooldown, and
  mid-dwell switch confirmation MUST NOT be redesigned in this feature.
- **FR-013**: Existing OS typing behavior MUST be unchanged for supported
  keys: letters, Space, Backspace, Enter, and one-shot Shift still go through
  the existing selection → action → OS delivery path into the focused
  external application.
- **FR-014**: Predictive suggestions MUST keep current behavior: three fixed
  slots, prefix length ≥ 2, fail-open when empty or unavailable, gaze
  selection completes the remaining suffix plus Space, and internal typing
  context continues to follow dispatched keystrokes only. Prediction ranking
  and word-list logic MUST NOT be modified.
- **FR-015**: Keyboard window placement and overall size policy MUST remain
  the current top-of-screen product keyboard (not a new full-screen keyboard
  and not a moved/resized overlay to “make keys bigger”).
- **FR-016**: This feature MUST NOT modify GazeFollower, calibration,
  gaze-estimation, gaze mapping, filtering, origin/DPR conversion, or any
  post-backend mapping correction. Practical accuracy gains MUST come from
  larger visible targets, not from retuning the backend.
- **FR-017**: Independent mapping/calibration benchmarks and Feature 004
  historical records MUST remain untouched. This feature MUST NOT treat
  mapping pixel-error or Feature 004 thresholds as its acceptance gate, and
  MUST NOT retune mapping to make the new layout look better.
- **FR-018**: Feature 003 product simplifications remain in force: no Pause,
  Preview, language toggle, symbols layout, Ctrl, Alt, gaze-status text, or
  local typed-text bar on the product keyboard.
- **FR-019**: Page switching MUST preserve already-armed one-shot Shift and
  MUST NOT reset typing context, suggestion prefix, or in-progress word
  state.
- **FR-020**: The page-switch arrow MUST use the same interaction family as
  other gaze keys (dwell primary, optional click convenience) and MUST be
  included in live geometry export/hit-testing while it is visible.

### Key Entities

- **Letter page**: One of two mutually exclusive views of QWERTY letters
  (left: QWERT / ASDFG / ZXCV; right: YUIOP / HJKL / BNM).
- **Page-switch target**: The large vertical arrow on the current page that
  reveals the other letter page and never types into the external app.
  Left page: right-side, right-pointing. Right page: left-side,
  left-pointing.
- **Visible target set**: The on-screen, enabled controls that live
  hit-testing may select after the latest page switch (visible letters,
  arrow, and persistent non-letter controls).
- **Persistent non-letter controls**: Suggestion slots, Calibrate, Space,
  Enter, window chrome, and Shift/Backspace (present on both pages; Shift
  and Backspace share the third letter row with that page’s letters).
- **In-progress word prefix / suggestion set / typing context**: Unchanged
  Feature 003 entities; paging must not fork a second prediction path.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On each page, visible letter keys are **clearly larger** than
  the current full-QWERTY letter keys when compared on the same display and
  the same keyboard window. Mean letter-key on-screen area MUST exceed the
  current full-QWERTY mean. Planning sets the arrow-width and key-size
  ratios from the live letter area so the gain is usable for gaze; this spec
  does not prescribe pixels or a numeric stretch factor.
- **SC-002**: A user can switch from one letter page to the other with a
  **single** completed gaze selection on the arrow, without any character
  appearing in the external application.
- **SC-003**: A user can type a short mixed-page word (for example `hello`)
  into the focused external application using only gaze, including the
  required page switches, with suggestions unused.
- **SC-004**: Suggestion accept still completes a word in **one** suggestion
  selection (remaining suffix + Space) after prefixes that involved a page
  switch.
- **SC-005**: After every page switch, 100% of gaze selections land on
  currently visible enabled controls; hidden-page letters produce **zero**
  selections in a scripted hit-test of those former positions.
- **SC-006**: In chin/head-support sessions with suggestions unused and
  GazeFollower left unchanged, practical **intended-key / focus** errors
  among **visible** letter keys are lower than on the current full-QWERTY
  layout under the same calibration condition. The improvement is attributed
  to larger targets, not to mapping retune. Independent mapping benchmarks
  remain unchanged and are not the acceptance gate for this feature.
- **SC-007**: Existing dwell timing feel is unchanged: users still complete
  a key selection in the same dwell interaction as today; this feature adds
  page switches, not a new selection method.
- **SC-008**: Space, Backspace, Enter, one-shot Shift, and
  Calibrate/Recalibrate remain usable without an extra letter-page step:
  Shift and Backspace are on both pages, and the other controls stay
  persistently visible.

## MVP Scope *(mandatory for GazeKey)*

**In scope**:

- Split product-keyboard letter keys into the two specified pages
- Large vertical page-switch arrow on each page
- Enlarge visible letter keys using space freed by hiding the other page
- Keep live visible-bounds ↔ hitbox synchronization after page changes
- Preserve existing dwell typing, OS delivery, suggestions, Shift/editing,
  Calibrate, and top-of-screen keyboard placement
- Practical typing checks on the new surface under chin/head support

**Out of scope**:

- Any change to GazeFollower (camera, Preview, Calibration, estimation,
  filtering, sample handoff)
- Calibration protocol, mapping, origin/DPR conversion, extra smoothing, or
  post-backend remapping
- Dwell duration, lockout, cooldown, or switch-confirmation redesign
- Prediction method, ranking, dictionary, or TypingContext rules
- Replacing or bypassing the existing OS typing path
- Changing keyboard window size, screen half, or multi-monitor layout
- Restoring Feature 003-removed chrome (Pause, Preview, language, symbols,
  Ctrl/Alt, typed-text bar, gaze-status text)
- Hebrew / language switching
- Feature 004 resume, rewrite, deletion, or use as a live acceptance gate
- Personalization, profiles, or accessibility work beyond larger gaze
  targets

## Assumptions

- Feature 005 GazeFollower is the production gaze/calibration backend and
  remains sealed upstream: `calibrated/filtered screen gaze → live keyboard
  geometry → focus/dwell`.
- The current product keyboard (Feature 003 R7 + bottom-row Calibrate) is
  the baseline: full QWERTY letters, three suggestion slots, Shift /
  Backspace on the third row, Calibrate | Space | Enter on the bottom row,
  slim minimize/close chrome, top-of-screen window at the existing height
  policy.
- “Left side” / “Right side” names both the **letter contents** of each
  page (QWERTY split at T/Y, G/H, V/B) and the **arrow placement**: left
  page has letters with a right-side right-pointing arrow; right page has
  letters with a left-side left-pointing arrow.
- Shift and Backspace remain on both pages in the third letter row so
  editing never requires hunting for a letter page.
- Default page is left. Page state persists until the user switches,
  survives minimize/restore, and resets to left on launch and after
  recalibration.
- Optional mouse click parity already exists for keys and SHOULD apply to
  the arrow; gaze remains the primary success path.
- Larger keys improve practical hit/focus tolerance. They are **not** a
  mapping-quality claim and MUST NOT justify backend or filter changes
  (Constitution I–III, V).
- Extra page-switch actions per word are an accepted usability cost.
- Chin/head support remains the product condition for practical checks
  defined in this spec.
- Feature 004 free-head A/B and T060 commits remain `eval_before` citations
  only if a later mapping experiment needs them; this feature should not
  run mapping experiments.
- Arrow width and letter-key size ratios are planning inputs derived from
  the live letter area; they are not specification constants.
