# Feature Specification: Predictive Text & Keyboard UX

**Feature Branch**: `003-predictive-text-keyboard-ux`

**Created**: 2026-08-08

**Status**: Draft

**Input**: User description: "Next GazeKey stage: automatic word completion /
predictive word suggestions together with virtual keyboard UI improvements.
While the user types through the existing gaze-based external-app typing flow,
the system should offer useful word suggestions based on typed so far, display
them on the keyboard, and allow gaze-based selection to complete the word via
the existing typing path. Maintain enough typing context for consistent
suggestion behavior across character entry, deletion, word completion, and
suggestion selection. Simplify the keyboard UI by removing controls and
elements that are no longer relevant or not implemented, and add a clear
suggestion area suitable for gaze interaction. Keep prediction modular and
decoupled from keyboard UI and OS input. Preserve gaze tracking, calibration,
mapping, external typing, and unrelated evaluation tooling. Keep the
specification high-level; defer prediction method, ranking, state design,
libraries, and module boundaries to research/planning."

**Guidance**: GazeKey Constitution v1.3.0 (binding). Separate feature from
`001-calibration-mapping-mvp` and `002-gaze-typing-os`. Mapping remains an
independently validated foundation; this feature consumes the working typing
path (mapped gaze → selection → external delivery) and MUST NOT compensate via
mapping changes. Predictive text and keyboard UX MUST NOT replace or bypass the
existing external typing mechanism.

## Clarifications

### Session 2026-08-10

- Q: Where should the in-progress word prefix come from? → A: **Internal tracking only** — derive prefix from GazeKey's own dispatched keystrokes (characters, Backspace, Space, suggestion accept); do not read or sync from the external application.
- Q: What should GazeKey deliver when a suggestion is accepted? → A: **Remaining letters + Space** — dispatch only the suffix not yet typed, then Space (e.g. prefix `hel` + suggestion `hello` → deliver `lo ` via the existing KeyAction path).
- Q: Which unimplemented or non-product controls should be removed from the gaze keyboard? → A: **Product keyboard removals**: Pause button; Preview button; EN/language button; gaze-status text (`Gaze active | …%`); typed-text display/bar (user sees text in the external app). **Keep and improve** the existing suggestion bar — reposition/fix layout so it is fully visible and not clipped; make it an active part of Feature 003. **Cleanup**: remove unused UI/controller wiring and dead code for removed product elements; do not leave inactive product interfaces behind. **Preview preservation**: remove only the product Preview button/wiring; before removal, verify whether underlying preview is still used by developer/tools flows (`python -m tools.preview` or flags). If still used non-productively, preserve that functionality; if genuinely unused everywhere, remove as dead code. Do not remove shared functionality still used by tools/debug flows.
- Q: What should happen to symbols layout and Ctrl/Alt on the product keyboard? → A: **Remove symbols toggle and Ctrl/Alt** from the product keyboard and clean up their product wiring.
- Q: How many word suggestions should be shown at once on the product keyboard? → A: **At most 3** word suggestions.
- Q: How should freed keyboard space be used after removing inactive controls? → A: **No empty gaps** — reorganize active controls into a clean, efficient layout; where appropriate, use freed space to **increase letter/editing key target size** for gaze usability. Resizing/repositioning is a **functional geometry change**: visible key bounds and gaze hitboxes must stay synchronized; gaze selection and external typing must still hit intended keys; calibration/mapping must **not** be retuned to compensate for UI redesign. Planning must choose the safest layout redistribution and verify with geometry/gaze regression tests.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete a Word From Suggestions (Priority: P1)

While gaze-typing into an external application, the user begins a word (for
example typing the start of "hel"). The keyboard shows useful word suggestions
that update as typing continues. The user selects a suggestion with the same
gaze-based interaction used for keys. The selected word is completed in the
external application through the existing working typing path—not a separate
input channel.

**Why this priority**: Reducing gaze key selections per word is the core value
of this feature; suggestion display without selectable completion does not
deliver that value.

**Independent Test**: Focus an external text field, type a recognizable prefix
by gaze, confirm suggestions appear and update, select one by gaze, and verify
the completed word appears only in the external field via the existing typing
path.

**Acceptance Scenarios**:

1. **Given** the user has typed a word prefix such as "hel" into the external
   app via GazeKey, **When** suggestions are available, **Then** the keyboard
   shows one or more completion candidates related to that prefix (for example
   "hello" or "help").
2. **Given** suggestions are visible, **When** the user selects a suggestion via
   gaze-based interaction, **Then** the intended word is completed in the
   external application using the existing typing delivery path.
3. **Given** the user continues typing characters after a prefix, **When** the
   current prefix changes, **Then** suggestions refresh to match the updated
   prefix.
4. **Given** a suggestion has been selected, **When** delivery succeeds,
   **Then** the external text reflects the completed word plus a trailing Space
   (e.g. prefix `hel` + suggestion `hello` → `hello ` in the external app).

---

### User Story 2 - Keep Typing When Suggestions Are Unused (Priority: P1)

The user may ignore suggestions entirely, or none may be available for the
current prefix. Character-by-character gaze typing into the external application
continues to work as it does today.

**Why this priority**: Predictions must extend—not replace—the working typing
product; regression of basic typing is unacceptable.

**Independent Test**: Type a full word by individual keys without selecting any
suggestion (including cases with empty suggestion lists) and confirm external
text matches expected character entry, including Space, Backspace, and Enter
behavior already supported by the product.

**Acceptance Scenarios**:

1. **Given** typing is active and no useful suggestions are shown, **When** the
   user dwells on letter and editing keys as today, **Then** characters and
   edits still reach the external application.
2. **Given** suggestions are visible, **When** the user ignores them and keeps
   typing keys, **Then** normal typing continues and suggestions stay consistent
   with the evolving prefix.
3. **Given** the user deletes characters with Backspace, **When** the current
   word prefix shortens or clears, **Then** suggestions update accordingly (or
   clear when there is no prefix).

---

### User Story 3 - Simplified Keyboard With a Clear Suggestion Area (Priority: P2)

The virtual keyboard is simplified so the product surface shows only controls
and information that belong in the live typing experience. Removed from the
**product keyboard**: Pause, Preview, language toggle, symbols layout toggle,
Ctrl, Alt, gaze-status text, and the local typed-text bar (the user already sees
text in the focused external app).
The existing suggestion bar is kept, repositioned, and fixed so it is fully
visible (not clipped), then activated for word completion (at most **3**
suggestions). Freed space from removals MUST NOT leave unused empty gaps;
active controls are reorganized into a clean layout, and where appropriate
freed space increases letter/editing key target size. Unused product UI
wiring and dead code for removed elements are cleaned up. Developer preview
remains available through non-product entry points (e.g. `python -m tools.preview`)
when still in use — only the product Preview button is removed.

**Why this priority**: Suggestions need a usable, uncluttered home on the
keyboard; leftover placeholders and redundant status/text chrome distract from
gaze interaction and waste screen space.

**Independent Test**: Launch the product keyboard after this feature’s UI work,
confirm removed elements are absent, confirm the suggestion region is fully
visible and gaze-selectable when suggestions exist, and confirm existing key
typing and hit-testing still work after layout changes.

**Acceptance Scenarios**:

1. **Given** the updated product keyboard is shown, **When** the user inspects
   the chrome, **Then** Pause, Preview, language toggle, symbols layout toggle,
   Ctrl, Alt, gaze-status text, and the local typed-text bar are not present.
2. **Given** word suggestions are available, **When** the user looks at the
   suggestion area, **Then** at most three suggestions are labeled in the fixed
   three-slot bar (fully visible, not clipped), clearly readable, and
   individually selectable with gaze-sized targets; unused slots stay
   blank/disabled and not dwellable without reflow.
3. **Given** inactive controls were removed, **When** the user views the
   keyboard, **Then** no unused empty gaps remain and active controls form a
   clean, efficient layout.
4. **Given** keyboard layout changes to redistribute space, **When** the user
   types by gaze on letter/editing keys, **Then** visible key bounds and gaze
   hitboxes remain synchronized and external typing selects the intended keys.
5. **Given** developer preview is still used via tools entry points, **When**
   `python -m tools.preview` (or equivalent) is run, **Then** preview
   functionality still works even though the product keyboard has no Preview
   button.
6. **Given** removed product UI elements, **When** the codebase is reviewed,
   **Then** their product-only wiring is removed and no inactive product
   interfaces remain unnecessarily; shared code still used by tools/debug flows
   is preserved.
7. **Given** the product keyboard is shown after the recalibration-target
   follow-up, **When** the user inspects the bottom row, **Then** Calibrate/
   Recalibrate appears left of Space as a noticeably larger gaze target than a
   normal letter key, Space is reduced/centered, Enter remains balanced, and
   Calibrate is absent from the slim top chrome.

---

### User Story 4 - Consistent Suggestion Behavior Across Typing Actions (Priority: P2)

As the user types characters, deletes characters, completes a word (for example
with Space), or accepts a suggestion, the system keeps a **`TypingContext`** so
that suggestions remain coherent with what was actually sent to the
external application.

**Why this priority**: Inconsistent context (stale suggestions after delete or
after completing a word) would make predictions untrustworthy and slow users
down.

**Independent Test**: Perform a short scripted sequence—type prefix, accept or
ignore suggestions, backspace, type again, complete a word—and verify suggestion
lists always match the current in-progress word context.

**Acceptance Scenarios**:

1. **Given** an in-progress word prefix, **When** the user types or deletes
   characters, **Then** suggestions reflect the updated prefix.
2. **Given** the user completes the current word (for example by Space or by
   accepting a suggestion that finishes the word and appends Space), **When**
   suggestions refresh, **Then** they no longer treat the finished word as the
   active prefix.
3. **Given** mixed actions (type, delete, suggestion accept, word boundary),
   **When** each action finishes, **Then** suggestion behavior remains
   internally consistent with the text flow being produced externally.

---

### Edge Cases

- No dictionary/model match for the current prefix → blank/disabled suggestion
  slots (fixed geometry); typing continues normally (FR-012).
- Very short prefixes (empty or single character) → **no suggestions** (min
  prefix length **2**; research R3 / FR-013); typing unaffected.
- Rapid successive key selections → stale accepts blocked by `prefix_epoch`
  (research R6); mid-dwell prefix change cancels pending suggestion dwell.
- Suggestion selected when external delivery fails → stop batch; `TypingContext`
  matches characters actually delivered only (research R5); no post-batch clear.
- Word list load failure or `WordProvider.suggest()` exception → fail open:
  suggestion area empty/unavailable; normal gaze typing continues; product MUST
  NOT crash (FR-012).
- Keyboard geometry change with active mapping/typing session → hit-testing and
  dwell targets remain aligned with on-screen keys; no requirement to change
  calibration or mapping models (FR-011; research R7).
- Suggestion bar clipped or partially off-screen → layout MUST follow research
  R7 acceptance layout so all three fixed suggestion slots are fully visible.
- Fewer than three candidates → unused slots remain in fixed positions,
  blank/disabled, not dwellable; **do not** resize or reflow the suggestion bar.
- User edits text directly in the external app (keyboard/mouse outside GazeKey)
  → internal prefix may diverge from external content; GazeKey does not reconcile
  via readback; suggestions reflect `TypingContext` until the next GazeKey
  typing action resets or updates context.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide word suggestions based on the user’s current
  in-progress typed prefix while GazeKey typing into an external application is
  active.
- **FR-002**: Suggestions MUST update as the in-progress prefix changes through
  normal typing and deletion.
- **FR-003**: System MUST display suggestions as part of the virtual keyboard
  interface in a dedicated, gaze-usable suggestion area. The product keyboard
  MUST keep **exactly 3** suggestion slots in **fixed positions and fixed
  geometry**. At most 3 words may be labeled at once; unused slots MUST remain
  blank/disabled and not dwellable. The suggestion bar MUST NOT resize or reflow
  based on how many suggestions are available.
- **FR-004**: Users MUST be able to select a displayed suggestion through the
  existing gaze-based interaction system (same interaction family as key
  selection).
- **FR-005**: Selecting a suggestion MUST complete the intended word in the
  external application by extending the existing working typing delivery path
  (not a separate parallel input mechanism). Delivery MUST dispatch only the
  **remaining suffix** not yet typed, followed by **Space** (e.g. prefix `hel` +
  suggestion `hello` → `lo ` via dispatched KeyActions).
- **FR-006**: System MUST maintain a **`TypingContext`** so that character entry,
  deletion, word completion, and suggestion acceptance produce consistent
  suggestion behavior.
- **FR-006a**: The in-progress word prefix MUST be derived from **internal
  tracking only** via `TypingContext` — GazeKey's record of successfully
  dispatched keystrokes and suggestion accepts (characters, Backspace, Space,
  suggestion completion). The system MUST NOT read or sync prefix state from the
  external application's text field.
- **FR-007**: Normal character-by-character typing MUST continue to work when no
  suggestions are available and when the user chooses not to use suggestions.
- **FR-008**: The product keyboard UI MUST be simplified by **removing** Pause,
  Preview, language toggle, symbols layout toggle, Ctrl, Alt, gaze-status text,
  and the local typed-text bar.
  Obsolete or unimplemented product controls MUST NOT remain as inactive
  placeholders. Unused product UI wiring and dead code for removed elements MUST
  be cleaned up without deleting shared functionality still used by
  tools/debug flows.
- **FR-008a**: The existing suggestion bar MUST be kept, repositioned, and laid
  out so it is **fully visible** (not clipped) and activated for gaze-based word
  completion in this feature (three fixed slots; see FR-003).
- **FR-008b**: Removing the product Preview button MUST NOT break developer
  preview when it is still reachable via non-product entry points (e.g.
  `python -m tools.preview`); verify usage before deleting underlying preview
  code.
- **FR-008c**: After removing inactive product controls, the keyboard MUST follow
  the research **R7 acceptance layout**: no unused empty/dead gaps; suggestion
  bar fully visible; reclaimed space redistributed appropriately to active
  letter/editing keys. Key enlargement is a gaze-usability layout goal, **not**
  a mapping-accuracy requirement, and MUST NOT justify mapping retune.
- **FR-008d**: The Calibrate/Recalibrate control MUST be placed on the **bottom
  keyboard row immediately left of Space**, as a gaze-selectable recovery target
  that is **noticeably larger** than a normal letter key (and taller when
  vertical space allows). Top chrome MUST NOT host Calibrate; slim that row and
  reclaim vertical space into letter-key rows when appropriate. Space MUST be
  reduced/centered and Enter may shrink slightly so the bottom row stays
  balanced while preserving QWERTY. The larger recalibration target improves
  **recovery tolerance** when mapping feels inaccurate; it MUST NOT be treated
  as improving mapper accuracy and MUST NOT justify mapping/calibration retune
  (FR-010, FR-011).
- **FR-009**: Prediction behavior MUST remain modular: UI, gaze-selection, and
  typing code MUST depend on the **`WordProvider`** abstraction, not on a
  concrete trie implementation. Suggestion generation MUST NOT be tightly coupled
  to keyboard rendering or OS-level input delivery. Instantiation of the concrete
  provider MUST occur in one composition/setup location (compatible with a future
  personalized provider without implementing personalization in this feature).
- **FR-010**: This feature MUST NOT unnecessarily modify gaze tracking,
  calibration, gaze-to-screen mapping, the existing external typing mechanism, or
  unrelated benchmark/evaluation tooling.
- **FR-011**: UI or keyboard-layout changes are **functional geometry changes**,
  not visual-only. Visible key/suggestion bounds and gaze hitboxes MUST remain
  synchronized. Gaze selection and external typing MUST still select the
  intended keys/suggestions. Calibration/mapping logic MUST NOT be retuned simply
  to compensate for the UI redesign. Layout/export/semantic geometry alignment
  updates are allowed only as required by the new keyboard surface.
- **FR-012**: When suggestions cannot be produced — including empty match sets,
  word-list load failure, or `WordProvider.suggest()` failure — the system MUST
  **fail open** to normal typing. The suggestion area MUST become safely
  empty/unavailable; the product MUST NOT crash. There is no hard dependency on
  prediction availability.
- **FR-013**: Suggestions MUST be offered only when the in-progress prefix length
  is **≥ 2** characters (research R3). Shorter prefixes MUST yield no labeled
  suggestions.
- **FR-014**: Suggestion completion casing MUST interact safely with one-shot
  Shift. If Shift is armed and the current prefix is non-empty (already typed
  lowercase), Shift MUST be cleared and MUST NOT be applied only to the suffix
  (must not produce mixed results such as `helLo`). See research R5.

### Key Entities

- **In-progress word prefix**: The portion of the current word the user has
  typed so far, used as the basis for suggestions (held in `TypingContext`).
- **Word suggestion**: A candidate completion offered for the current prefix,
  shown in a suggestion slot and selectable by gaze when that slot is enabled.
- **TypingContext**: Internal session state derived from GazeKey-dispatched
  actions (not external-app readback) that tracks the current in-progress word
  prefix, `prefix_epoch`, and word-boundary events (see
  `data-model.md` / research R4).
- **Suggestion set**: Up to **3** labeled suggestions bound to **three fixed
  slots**; unused slots stay blank/disabled (never more than three labels).
- **Keyboard surface**: The on-screen gaze keyboard including keys, supported
  product controls, and the suggestion area; geometry must stay consistent with
  hit-testing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a scripted prefix scenario (for example after typing a short
  recognizable stem such as "hel"), at least one appropriate completion
  candidate appears in the suggestion area before the user finishes the word by
  individual keys.
- **SC-002**: Selecting a visible suggestion completes the intended word in the
  focused external application in a single suggestion-selection action (suffix
  + trailing Space), without requiring the remaining letters or a separate Space
  key selection.
- **SC-003**: After each character typed or deleted in an in-progress word,
  suggestions refresh to match the new prefix within one interaction cycle of
  the keyboard UI (no persistent stale list from a previous prefix).
- **SC-004**: Users can still type a full short word into an external app using
  only individual keys with suggestions ignored or empty, with no regression
  versus the pre-feature typing path for supported keys.
- **SC-005**: After keyboard UI simplification, the product keyboard no longer
  shows Pause, Preview, language toggle, symbols layout toggle, Ctrl, Alt,
  gaze-status text, or the local typed-text bar; no unused empty/dead gaps
  remain (R7 acceptance layout); the suggestion area keeps three fixed slots
  fully visible, with at most three labels when available.
- **SC-006**: After any keyboard geometry change for this feature, visible
  key/suggestion bounds and gaze hitboxes remain synchronized; gaze hit-testing
  still selects the intended on-screen key/suggestion target; external typing for
  supported keys continues to work without recalibration or mapping retuning.
- **SC-007**: Mapping/calibration quality is not treated as acceptance for this
  feature; existing independent mapping benchmarks remain unchanged and are not
  retuned to “fix” prediction or keyboard UX issues.

## MVP Scope *(mandatory for GazeKey)*

**In scope**:

- Automatic word suggestions based on the current typed prefix during active
  GazeKey external typing
- Display of suggestions on the virtual keyboard in a gaze-usable area
- Gaze-based selection of a suggestion that completes the word via the existing
  typing delivery path
- TypingContext sufficient for consistent suggestions across type, delete,
  word completion, and suggestion accept
- Keyboard UI simplification and redistribution per research **R7 acceptance
  layout**: remove listed inactive product controls; no empty dead gaps;
  reorganize active controls; redistribute reclaimed space appropriately to
  letter/editing keys; three fixed suggestion slots fully visible; geometry/gaze
  regression via tests (key enlargement is not a mapping-accuracy requirement)
- Modular separation between suggestion generation, keyboard UI, and OS/external
  typing delivery
- Preservation of existing gaze tracking, calibration, mapping, external typing,
  and unrelated evaluation tooling

**Out of scope** (unless later shown to be directly required for word
completion during planning):

- Changing calibration, mapper fitting, or mapping benchmarks
- Replacing or reimplementing the existing external typing delivery path
- Product Pause/Resume control (removed from product keyboard in this feature)
- Removing developer preview entirely (only the product button is removed;
  tools entry points preserved when still in use)
- Personalized learning from long-term user history (unless a minimal approach is
  chosen later in planning)
- Full language switching / multilingual prediction productization
- Multi-monitor layout redesign
- Accessibility polish beyond what is needed for clear gaze targets on
  suggestions
- Phrase-level or sentence-level prediction beyond current-word completion
- Unrelated new product features not required for word completion or the
  keyboard simplification described above

## Assumptions

- GazeKey can already type successfully into external desktop applications via
  the current `002` typing flow; this feature extends that flow.
- Primary interaction for suggestions is gaze-based, consistent with key
  selection; optional mouse parity may follow existing product conventions if
  already present for keys.
- English word completion is sufficient for the first version; the product
  language toggle is removed because language switching is not implemented.
- An empty suggestion list is an acceptable and expected state.
- Accepting a suggestion dispatches the remaining suffix plus a trailing Space
  through the existing KeyAction path (see FR-005).
- Constitution v1.3.0 applies: do not alter calibration/mapping to compensate for
  prediction or UI issues.

## Resolved Planning Decisions

The following were open at specify time and are now **resolved** in
[`research.md`](./research.md) / [`plan.md`](./plan.md). Spec consumers MUST
treat those documents as normative for these items:

| Topic | Resolution |
|-------|------------|
| Prediction method | Bundled licensed English list + in-memory prefix trie (`WordProvider` / `TrieWordProvider`) — research **R1** |
| Ranking (max 3) | Frequency-ordered top-3 with efficient retrieval (not prefix-node alone) — **R2** |
| TypingContext design | Delivery-only updates (`on_action_delivered` ok); no post-batch clear — **R4** |
| Module boundaries | `gazekey/prediction/` + KeyAction path; UI depends on `WordProvider` only — **R11**, FR-009 |
| Libraries / data | No new pip deps; documented open-license `words_en.txt` — **R1** |
| Short prefixes | Min length **2** — **R3**, FR-013 |
| Layout redistribution | Research **R7** is the acceptance layout — FR-008c |
| Stale / race rules | `prefix_epoch` + cancel mid-dwell — **R6** |
| Delivery / Shift failure | Suffix batch stop on failure; Shift-armed + non-empty prefix clears Shift (no `helLo`) — **R5**, FR-014 |
| Provider load / suggest failure | Fail open; empty suggestions; typing continues — FR-012 |

These resolved items must not block agreement on the user-facing outcomes above.
