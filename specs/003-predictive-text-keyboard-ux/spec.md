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
   **Then** the external text reflects a completed word consistent with the
   selected suggestion (relative to the prefix already typed).

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

The virtual keyboard is reviewed and simplified so visible controls match
functionality that actually exists. Obsolete or unimplemented controls and
clutter are removed or no longer presented as active. A clear, usable area for
word suggestions is added. Interaction targets remain large and uncluttered
enough for reliable gaze use. Any geometry changes stay synchronized with
gaze hit-testing and the existing typing flow.

**Why this priority**: Suggestions need a usable home on the keyboard, and the
current UI still exposes placeholders/controls that confuse the product surface;
both are required for a coherent predictive-typing experience.

**Independent Test**: Launch the product keyboard after this feature’s UI work,
confirm only intentional controls are active/visible, confirm a dedicated
suggestion region is present and gaze-selectable when suggestions exist, and
confirm existing key typing and hit-testing still work after layout changes.

**Acceptance Scenarios**:

1. **Given** the updated keyboard is shown, **When** the user inspects available
   controls, **Then** controls that are not implemented or no longer relevant
   are not presented as working product actions.
2. **Given** word suggestions are available, **When** the user looks at the
   suggestion area, **Then** suggestions are clearly visible and individually
   selectable with gaze-sized targets.
3. **Given** keyboard layout or key sizes change to make room for suggestions,
   **When** the user types by gaze on letter/editing keys, **Then** hit-testing
   and external typing remain correct for the new geometry.
4. **Given** the simplified keyboard, **When** the user uses Pause/Resume and
   other still-supported product controls, **Then** those controls continue to
   work as in the current product.

---

### User Story 4 - Consistent Suggestion Behavior Across Typing Actions (Priority: P2)

As the user types characters, deletes characters, completes a word (for example
with Space), or accepts a suggestion, the system keeps enough typing-context
information that suggestions remain coherent with what was actually sent to the
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
   accepting a suggestion that finishes the word), **When** suggestions refresh,
   **Then** they no longer treat the finished word as the active prefix.
3. **Given** mixed actions (type, delete, suggestion accept, word boundary),
   **When** each action finishes, **Then** suggestion behavior remains
   internally consistent with the text flow being produced externally.

---

### Edge Cases

- No dictionary/model match for the current prefix → show no suggestions (or an
  empty suggestion area); typing continues normally.
- Very short prefixes (empty or single character) → system may show no
  suggestions or broader suggestions; behavior must remain predictable and not
  block typing.
- Rapid successive key selections → suggestions must not lag in a way that
  causes selection of a stale candidate after the prefix has already changed
  (exact freshness rules deferred to planning).
- Suggestion selected when the external app rejects or fails delivery → user
  can observe failure consistently with existing typing delivery feedback
  patterns; typing context and suggestions must not silently diverge from what
  was actually delivered (details deferred to planning).
- Keyboard geometry change with active mapping/typing session → hit-testing and
  dwell targets remain aligned with on-screen keys; no requirement to change
  calibration or mapping models.
- User pauses typing → suggestions must not cause unintended external input
  while paused (align with existing pause semantics).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide word suggestions based on the user’s current
  in-progress typed prefix while GazeKey typing into an external application is
  active.
- **FR-002**: Suggestions MUST update as the in-progress prefix changes through
  normal typing and deletion.
- **FR-003**: System MUST display suggestions as part of the virtual keyboard
  interface in a dedicated, gaze-usable suggestion area.
- **FR-004**: Users MUST be able to select a displayed suggestion through the
  existing gaze-based interaction system (same interaction family as key
  selection).
- **FR-005**: Selecting a suggestion MUST complete the intended word in the
  external application by extending the existing working typing delivery path
  (not a separate parallel input mechanism).
- **FR-006**: System MUST maintain sufficient typing-flow context so that
  character entry, deletion, word completion, and suggestion acceptance produce
  consistent suggestion behavior.
- **FR-007**: Normal character-by-character typing MUST continue to work when no
  suggestions are available and when the user chooses not to use suggestions.
- **FR-008**: The virtual keyboard UI MUST be simplified so that visible product
  controls reflect functionality that actually exists; obsolete or unimplemented
  controls MUST NOT be presented as active product actions.
- **FR-009**: Prediction behavior MUST remain modular: suggestion generation MUST
  NOT be tightly coupled to keyboard rendering or OS-level input delivery.
- **FR-010**: This feature MUST NOT unnecessarily modify gaze tracking,
  calibration, gaze-to-screen mapping, the existing external typing mechanism, or
  unrelated benchmark/evaluation tooling.
- **FR-011**: UI or keyboard-layout changes MUST preserve correct gaze
  hit-testing and external typing; if key positions or sizes change, all
  geometry-dependent interaction behavior MUST remain synchronized.
- **FR-012**: When suggestions cannot be produced, the system MUST fail open to
  normal typing (no hard dependency on prediction availability).

### Key Entities

- **In-progress word prefix**: The portion of the current word the user has
  typed so far, used as the basis for suggestions.
- **Word suggestion**: A candidate completion offered for the current prefix,
  shown in the suggestion area and selectable by gaze.
- **Typing flow context**: The minimal session information needed to keep
  suggestions aligned with typing, deletion, word boundaries, and suggestion
  acceptance (exact structure deferred to planning).
- **Suggestion set**: The current list of suggestions shown for the active
  prefix (may be empty).
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
  focused external application in a single suggestion-selection action, without
  requiring the remaining letters to be typed individually.
- **SC-003**: After each character typed or deleted in an in-progress word,
  suggestions refresh to match the new prefix within one interaction cycle of
  the keyboard UI (no persistent stale list from a previous prefix).
- **SC-004**: Users can still type a full short word into an external app using
  only individual keys with suggestions ignored or empty, with no regression
  versus the pre-feature typing path for supported keys.
- **SC-005**: After the keyboard UI simplification, unimplemented or obsolete
  controls are not offered as active actions, and a dedicated suggestion area is
  present and usable when suggestions exist.
- **SC-006**: After any keyboard geometry change for this feature, gaze
  hit-testing still selects the intended on-screen key/suggestion target, and
  external typing for supported keys continues to work without recalibration or
  mapping changes.
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
- Typing-flow context sufficient for consistent suggestions across type, delete,
  word completion, and suggestion accept
- Keyboard UI simplification (remove/hide obsolete or unimplemented controls)
  and addition of a clear suggestion area
- Modular separation between suggestion generation, keyboard UI, and OS/external
  typing delivery
- Preservation of existing gaze tracking, calibration, mapping, external typing,
  and unrelated evaluation tooling

**Out of scope** (unless later shown to be directly required for word
completion during planning):

- Changing calibration, mapper fitting, or mapping benchmarks
- Replacing or reimplementing the existing external typing delivery path
- Full language switching / multilingual prediction productization
- Personalized learning from long-term user history (unless a minimal approach is
  chosen later in planning)
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
- English word completion is sufficient for the first version unless planning
  explicitly expands language scope.
- An empty suggestion list is an acceptable and expected state.
- Suggestion acceptance should produce a completed word outcome in the external
  app; exact trailing-space / word-boundary conventions are left to planning if
  not fixed during clarification.
- Constitution v1.3.0 applies: do not alter calibration/mapping to compensate for
  prediction or UI issues.

## Open Research / Planning Decisions

The following are intentionally **not** decided in this specification. They
MUST be researched and chosen during `/speckit-clarify` and/or `/speckit-plan`:

1. **Prediction method** — how candidates are generated (dictionary, n-gram,
   language model, OS/IME APIs, hybrid, etc.).
2. **Ranking strategy** — how candidates are ordered and how many are shown.
3. **Typing-state design** — exact structure and ownership of typing-flow
   context; how it stays aligned with delivered external text.
4. **Module boundaries and interfaces** — concrete separation between prediction,
   keyboard UI, and OS/input delivery without over-designing upfront.
5. **Libraries, models, and data sources** — what assets or dependencies are
   appropriate for GazeKey’s desktop constraints.
6. **Suggestion UX details** — exact layout, target sizes, maximum visible
   suggestions, and behavior for very short prefixes.
7. **Completion semantics** — whether accepting a suggestion also inserts a
   trailing space or other word-boundary character.
8. **Stale-suggestion / race rules** — precise freshness guarantees under rapid
   typing.
9. **Failure handling details** — how suggestion acceptance interacts with
   delivery failure while keeping context consistent.

These open items must not block agreement on the user-facing outcomes above.
