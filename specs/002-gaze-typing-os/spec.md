# Feature Specification: Gaze Typing & OS Integration

**Feature Branch**: `002-gaze-typing-os`

**Created**: 2026-08-08

**Status**: Draft

**Input**: User description: "Next GazeKey stage: real gaze-based typing and
operating-system integration. Pipeline extension from mapped gaze through key
detection, dwell selection, key action, and native OS input so GazeKey can type
into external applications. Structural cleanup so `gazekey/` is runtime-product
only; move developer-only evaluation/diagnostics/debug tooling outside the
product package; remove obsolete dormant code and rebuild typing cleanly.
Keep calibration/mapping isolated from typing and OS integration."

**Guidance**: Separate feature from `001-calibration-mapping-mvp`. This stage
runs **in parallel** with continued mapping improvement; typing success is not
gated on `001` key-hit floors. Calibration → mapping → mapped gaze remains the
sealed upstream base.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type Into an External App by Gaze Dwell (Priority: P1)

After calibration has produced a mapped gaze point, the user looks at keys on
the virtual keyboard. Holding gaze on a key for a short dwell period selects
that key and sends its character or action into the **currently focused
external application** (for example a notepad or document window). The user
does not click GazeKey keys with the mouse or use a physical keyboard for those
characters.

**Why this priority**: This is the core product value of this stage — GazeKey
becomes a real input device for other programs, not only an in-app preview.

**Independent Test**: Focus an external text field, calibrate (or use an
existing valid mapping), dwell on keys for a short known word, and confirm the
characters appear only in the external field from gaze dwell.

**Acceptance Scenarios**:

1. **Given** a valid mapped gaze exists and an external text field has OS
   focus, **When** the user dwells on a letter key until selection completes,
   **Then** that letter appears in the external text field.
2. **Given** the user dwells on Space or Backspace (or other keys present on
   the on-screen layout), **When** selection completes, **Then** the matching
   action is delivered to the focused external app.
3. **Given** the user begins dwelling on a key, **When** they look away before
   dwell completes, **Then** no key action is sent and dwell feedback resets.
4. **Given** gaze typing is active, **When** the user completes a dwell
   selection, **Then** GazeKey itself is not the destination that receives the
   typed character as the focused typing target.

---

### User Story 2 - Use GazeKey as an Overlay While Typing Elsewhere (Priority: P2)

While injecting into another application, the user can still see and use the
virtual keyboard. GazeKey stays available as an on-top / overlay keyboard so
the user can keep looking at keys without making GazeKey the OS focus recipient
for injected keystrokes.

**Why this priority**: Without reliable overlay/focus behavior, P1 cannot be
used in practice — focusing the external app would hide or disable the keyboard.

**Independent Test**: Place an external editor in focus, keep GazeKey visible
and usable for dwell selection, and verify injected text continues to land in
the editor.

**Acceptance Scenarios**:

1. **Given** an external app has typing focus, **When** the user interacts with
   GazeKey by gaze for dwell selection, **Then** GazeKey remains visible and
   usable as an overlay keyboard.
2. **Given** GazeKey is shown as an overlay, **When** a key is selected by
   dwell, **Then** the keystroke is delivered to the currently focused external
   app, not absorbed as GazeKey’s own text-entry focus.
3. **Given** the user switches OS focus to a different external text field,
   **When** they dwell-select a key, **Then** input goes to the newly focused
   field.

---

### User Story 3 - Runtime Product Package vs Developer Tooling (Priority: P3)

A developer or reviewer looking at the repository can tell what is required to
**run the keyboard product** versus what exists only for benchmarks,
evaluation, diagnostics, or debug investigation. Product runtime code lives in
the main product package; developer-only functionality is outside that package.
Obsolete dormant typing stacks, unused selection/intent facades, dead
environment flags, and dead runtime branches are removed rather than left as
confusing alternate paths. Existing pieces are reused only when they still fit
the new architecture; otherwise they are deleted and rebuilt cleanly.

**Why this priority**: Cleanup is part of this stage’s deliverable so typing/OS
work does not sit on a tangled product+tooling package.

**Independent Test**: Inventory the product package after cleanup and confirm
(1) evaluation/benchmark/diagnostics are not presented as product pipeline
stages inside it, (2) no dormant alternate typing/intent/selection stacks
remain, and (3) the live path from mapped gaze to OS input is the only typing
path.

**Acceptance Scenarios**:

1. **Given** the repository after this feature’s cleanup, **When** a reviewer
   inspects the product package, **Then** it contains only code required for
   the keyboard to run (sensing, calibration, mapping, live UI, dwell typing,
   OS input).
2. **Given** benchmark, evaluation, or diagnostic tooling still exists for
   developers, **When** a reviewer looks for it, **Then** it lives outside the
   product package and is not implied to be part of the normal typing pipeline.
3. **Given** previously dormant or obsolete typing/intent/selection/facade
   code and unused flags, **When** cleanup completes, **Then** those artifacts
   are gone or replaced by the single new typing architecture — not preserved
   as unused parallel implementations.

---

### User Story 4 - Keep Calibration and Mapping Isolated (Priority: P4)

Calibration and gaze-to-key mapping continue to produce a mapped gaze point as
today. Typing and OS integration **consume** that point; they do not change how
calibration targets are collected, how the mapper is fit, or how mapping quality
is judged for the mapping stage. No typing or OS logic is folded into
calibration or mapping.

**Why this priority**: Protects the `001` pipeline and avoids reintroducing
monolithic “fix typing by tweaking the mapper” entanglement.

**Independent Test**: Run calibration and mapping preview/fit flows and confirm
behavior and responsibilities match the sealed upstream stage; enable typing
and confirm it only attaches after a mapped gaze point exists.

**Acceptance Scenarios**:

1. **Given** the user runs calibration, **When** fixation and fit complete,
   **Then** the outcome is still a mapped gaze capability, with no dwell
   selection or OS input during calibration fixation.
2. **Given** a mapped gaze point is available, **When** typing is active,
   **Then** key detection and dwell selection use that point without modifying
   the calibration/mapping fit path.
3. **Given** mapping improvement work continues separately, **When** this
   feature’s typing path is exercised, **Then** typing success is judged by
   dwell → key action → OS delivery, not by raising `001` key-hit percentage
   floors.

---

### Edge Cases

- What happens when no external app has a text-capable focus (desktop, empty
  focus)? The system MUST NOT crash; the user gets clear feedback that input
  could not be delivered, and no false “typed into GazeKey” success.
- What happens when gaze is unstable / leaves and re-enters a key during dwell?
  Dwell MUST reset or restart per the dwell rules; partial dwells MUST NOT
  emit keystrokes.
- What happens when tracking is lost mid-dwell? Selection MUST cancel; no
  keystroke MUST be sent.
- What happens when the user dwells on a non-typing or unavailable control?
  No OS character MUST be sent for that control.
- What happens if OS input is temporarily blocked by the operating system?
  The user MUST be informed that injection failed; the session MUST remain
  recoverable (recalibrate / continue preview / retry) without corrupting
  calibration state.
- How does the system treat mouse clicks on keys? Mouse-driven in-app buffer
  entry MAY remain as a non-primary convenience; it MUST NOT be required for
  the P1 success path and MUST NOT be confused with OS injection success.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST determine which virtual keyboard key corresponds to
  the current mapped gaze point (key detection).
- **FR-002**: System MUST support dwell-based key selection: continuous gaze on
  a key for a defined dwell period completes selection.
- **FR-003**: System MUST provide visible dwell/selection feedback so the user
  can tell which key is being selected and whether dwell is progressing,
  completed, or cancelled.
- **FR-004**: System MUST cancel or restart dwell when gaze leaves the key
  before dwell completes, without emitting a key action.
- **FR-005**: On successful dwell selection, System MUST perform the key’s
  action as native OS input to the currently focused external application.
- **FR-006**: Native OS input MUST cover the semantics of keys present on the
  current on-screen keyboard layout (letters, Space, Backspace, and other
  layout keys), not a reduced demo-only subset.
- **FR-007**: GazeKey MUST remain usable as an on-top / overlay keyboard while
  OS focus for typing remains on the external application that should receive
  keystrokes.
- **FR-008**: Injected keystrokes MUST NOT treat GazeKey as the focused
  recipient of those characters; the recipient is the currently focused
  external app.
- **FR-009**: Typing and OS integration MUST consume mapped gaze only; they
  MUST NOT alter calibration sample collection, mapper fitting, or mapping
  quality-gate responsibilities.
- **FR-010**: Calibration fixation UI MUST remain free of typing/OS concerns
  (no dwell selection or OS injection during calibration fixation).
- **FR-011**: The product package (`gazekey/`) MUST contain only runtime code
  required for the keyboard to run.
- **FR-012**: Developer-only benchmark, evaluation, diagnostics, and debug
  tooling MUST live outside the product package where appropriate, and MUST NOT
  appear as stages of the normal typing product pipeline.
- **FR-013**: Obsolete dormant typing, intent, selection, and facade modules,
  unused environment flags, and dead runtime branches that conflict with the
  new architecture MUST be removed; reuse is allowed only when existing code
  still fits the new design.
- **FR-014**: This feature MUST NOT require meeting `001` key-hit accuracy
  floors as a prerequisite for accepting typing/OS behavior; mapping quality
  may continue to improve in parallel.
- **FR-015**: System MUST handle lost tracking, failed OS delivery, and missing
  external focus without crashing or corrupting calibration/mapping state.
- **FR-016**: Predictive text, language switching, personalization,
  multi-monitor support, and advanced accessibility polish are out of scope
  for this feature.
- **FR-017**: Reworking or replacing the sealed calibration → PCA4 mapping path
  for the sake of typing is out of scope; mapping changes belong to mapping
  work, not this feature’s typing/OS path.

### Key Entities

- **Mapped Gaze Point**: Screen position produced by the sealed upstream
  calibration/mapping pipeline; input to key detection.
- **Virtual Key**: On-screen key with identity and action semantics (character
  or editing action).
- **Dwell Intent**: Ongoing attempt to select a key by holding gaze; includes
  progress, completion, and cancellation.
- **Key Action**: The meaning of a completed selection (e.g., type “A”, space,
  backspace).
- **OS Input Event**: Delivery of a key action to the currently focused
  external application via native operating-system input.
- **Runtime Product Package**: Code required to run the live keyboard product.
- **Developer Tooling**: Benchmark, evaluation, diagnostics, and debug aids
  kept outside the product package.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a verification session, a user can type a fixed short word
  (at least 4 characters) into an external text field using **only** gaze dwell
  on GazeKey keys (no mouse clicks on keys, no physical keyboard for those
  characters).
- **SC-002**: For every completed dwell selection in that session, the
  character or action delivered to the OS matches the key that showed
  dwell/selection feedback at completion (no mismatch between UI selection and
  OS delivery). This criterion does **not** require meeting `001` key-hit
  percentage floors.
- **SC-003**: Accidental activations are low enough that the short-word task
  can be finished with at most 2 unintended characters requiring correction
  (Backspace or retype).
- **SC-004**: After overlay/focus setup, the external app remains the typing
  recipient for injected characters while GazeKey stays visible for at least
  one continuous short-word attempt without the user needing to click back into
  the editor between every character.
- **SC-005**: A reviewer can separate runtime product code from developer
  tooling without consulting historical flag notes; no dormant alternate
  typing/intent/selection stacks remain inside the product package.
- **SC-006**: Calibration and mapping flows still produce mapped gaze without
  performing dwell selection or OS injection during calibration fixation; typing
  attaches only after mapped gaze is available.

## MVP Scope *(mandatory for GazeKey)*

**In scope**:

- Mapped gaze → key detection → dwell selection → key action → native OS input
- Overlay / on-top keyboard behavior so external apps can remain the typing
  focus recipient
- Visible dwell/selection feedback and cancel-on-leave behavior
- Full on-screen layout key semantics for OS delivery (not a reduced subset)
- Structural cleanup: product package = runtime only; move evaluation /
  diagnostics / debug tooling outside; remove obsolete dormant modules, unused
  flags, and dead branches; rebuild typing cleanly where old code does not fit
- Isolation: typing/OS consume mapped gaze; do not entangle calibration/mapping

**Out of scope**:

- Raising or redefining `001` key-hit / pixel / row accuracy floors as this
  feature’s acceptance gate
- Predictive text / suggestion bar
- Hebrew/English (or other) language switching
- Personalization / user profiles
- Multi-monitor support
- Advanced accessibility polish beyond basic dwell feedback and recoverable
  error messaging
- Redesigning the PCA4 calibration/mapping pipeline inside this feature
- Building a large diagnostics platform or dashboard

## Assumptions

- Users run a single primary display and keep GazeKey visible while focusing an
  ordinary external text editor for verification.
- A valid calibration/mapping result (mapped gaze) is available before dwell
  typing; obtaining that result uses the existing sealed upstream flow from
  feature `001`, improved separately as needed.
- Dwell duration and feedback styling use simple, fixed defaults suitable for
  first usable typing; fine-tuning dwell timing is not a research goal of this
  feature.
- “Currently focused external application” means the OS focus target at the
  moment a dwell selection completes.
- Overlay / always-on-top style behavior is sufficient for MVP verification;
  click-through and advanced windowing polish can wait.
- Mouse click → in-app text buffer may remain as a non-primary convenience for
  developers; it is not the P1 success path.
- Obsolete `future` / unused intent / selection / dormant dwell implementations
  are deleted and replaced rather than preserved as facades for later
  reconnection.
- Developer tooling relocation defaults to a top-level developer area (e.g.
  `tools/`) with offline demos remaining under existing script locations;
  exact layout is a planning detail, not a user-facing requirement.
- OS permission or security prompts, if any, are accepted as an environment
  prerequisite for verification on the target platform.
- Feature `001` remains the specification of record for calibration, mapping,
  and mapping benchmarks; this feature does not amend `001` to include OS
  typing.
