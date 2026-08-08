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

## Clarifications

### Session 2026-08-08

- Q: When does gaze dwell typing become active after a valid mapped gaze exists? → A: **Revised**: Typing auto-starts after successful calibration/mapping; read-only preview is developer/debug only (not normal product flow); no user “Enable Typing” step
- Q: After a dwell selection fires a key, how should the next selection on the same key work? → A: Same-key lockout until gaze leaves that key, then a new dwell can start; leave MUST be a clear/confirmed leave (not single-frame boundary jitter); exact threshold deferred to planning
- Q: What default dwell duration should complete a key selection in typing mode? → A: Balanced: about 0.8–1.0 seconds
- Q: How should the user pause and resume already-active typing? → A: Both a dwellable Pause/Resume key (primary, hands-free) and an optional mouse-click Pause/Resume control (convenience only); Pause/Resume is an internal system control and MUST NEVER emit an OS character/action
- Q: When typing is active, what should a mouse click on a normal typing key do? → A: Mouse clicks produce the same `KeyAction` path as dwell (optional convenience); OS injection only via the dedicated input boundary
- Q: Semantic boundary for selection vs OS injection? → A: Completed dwell/click MUST produce a `KeyAction`; OS injection MUST consume that action only through a dedicated input adapter/boundary; dwell/UI MUST NOT call native OS input APIs directly; boundary remains independently testable and does not block future observation of the `KeyAction` stream
- Q: External typing-target ownership? → A: GazeKey interaction MUST NOT permanently replace the intended external typing target (including optional mouse use and calibration→auto-typing transition); exact Windows focus mechanics deferred to planning
- Q: Cleanup scope? → A: `gazekey/` = runtime-product only (shared primitives required by product may remain); developer benchmark/evaluation/diagnostics/debug/read-only preview orchestration live outside `gazekey/`; cleanup planning is repository-wide (obsolete archive, scripts, stale tests/docs, unused `GAZEKEY_*` flags, compatibility code, dead artifacts)
- Q: Active typing-key set for this feature? → A: Letters A–Z (case via Shift), Space, Backspace, Enter, and modifiers Shift/Ctrl/Alt on the letters keyboard; NOT suggestion placeholders, language toggle, symbols/?123 layout keys, or window chrome; Pause/Resume is internal (not an OS `KeyAction`)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type Into an External App by Gaze Dwell (Priority: P1)

After successful calibration/mapping produces a mapped gaze point, **typing
auto-starts** as the normal product flow. Looking at an **active typing key**
and holding gaze for a short dwell period completes selection, which produces a
**`KeyAction`**. A dedicated OS input boundary consumes that action and delivers
it to the **intended external typing target** (for example a notepad or document
window). Dwell/UI selection MUST NOT talk to native OS input APIs directly.
There is no separate “Enable Typing” step. Read-only gaze preview (show mapped
position without key activation) is **developer/debug tooling only**, not part
of the normal user journey. The primary success path uses gaze only (no mouse
required).

**Why this priority**: This is the core product value of this stage — GazeKey
becomes a real input device for other programs immediately after mapping is
ready.

**Independent Test**: Focus an external text field, complete successful
calibration/mapping, dwell on active typing keys for a short known word without
any enable step, and confirm characters appear only in the external field from
gaze dwell via the `KeyAction` → OS input boundary.

**Acceptance Scenarios**:

1. **Given** calibration/mapping has just succeeded and an external text field
   is the intended typing target, **When** the user dwells on a letter key until
   selection completes (with no prior “enable typing” action), **Then** a
   `KeyAction` is produced and the letter appears in the external text field
   via the OS input boundary.
2. **Given** the user dwells on Space, Backspace, or Enter (active typing keys)
   after mapping success, **When** selection completes, **Then** the matching
   `KeyAction` is delivered through the OS input boundary to the external
   typing target.
3. **Given** the user begins dwelling on a key, **When** they look away before
   dwell completes, **Then** no `KeyAction` is produced and dwell feedback
   resets.
4. **Given** a key has just been selected by dwell, **When** the user keeps
   gaze on that same key without a clear/confirmed leave, **Then** no
   additional selection fires; re-arm requires confirmed leave, return, and a
   new completed dwell (single-frame boundary jitter MUST NOT count as leave).
5. **Given** gaze typing is active, **When** the user completes a dwell
   selection, **Then** GazeKey MUST NOT permanently become the typing-target
   owner; the intended external app remains the recipient of injected input.
6. **Given** typing is active after mapping success, **When** the user pauses
   via the dwellable Pause control (or optional click control), **Then** further
   typing-key dwells/clicks MUST NOT produce OS-bound `KeyAction`s until resume,
   and Pause/Resume itself MUST NOT emit any OS character/action.
7. **Given** typing is paused, **When** the user resumes via dwell (primary)
   or optional click, **Then** dwell selection → `KeyAction` → OS input works
   again without recalibration.
8. **Given** a suggestion placeholder, language control, or symbols-layout key
   is visible, **When** the user dwells or clicks it, **Then** this feature
   MUST NOT require OS delivery of those controls as part of the active
   typing-key set.

---

### User Story 2 - Preserve External Typing-Target Ownership (Priority: P2)

While injecting into another application, the user can still see and use the
virtual keyboard. GazeKey stays available as an on-top / overlay keyboard.
Interacting with GazeKey (gaze dwell, optional mouse, and the transition from
calibration completion into auto-started typing) MUST NOT permanently replace
the intended external typing target. Exact operating-system focus mechanics are
deferred to planning; the product requirement is ownership of the typing
destination, not a specific Windows API recipe.

**Why this priority**: Without preserving the external typing target, P1 cannot
be used in practice — interacting with GazeKey would steal or strand focus.

**Independent Test**: Place an external editor as the intended typing target,
complete calibration→auto typing, use gaze (and optionally mouse) on GazeKey,
and verify injected text continues to land in the editor without permanently
making GazeKey the typing destination.

**Acceptance Scenarios**:

1. **Given** an external app is the intended typing target, **When** the user
   interacts with GazeKey by gaze for dwell selection, **Then** GazeKey remains
   visible/usable as an overlay and does not permanently replace that target.
2. **Given** GazeKey is shown as an overlay, **When** a typing key is selected
   by dwell or optional mouse click, **Then** the resulting `KeyAction` is
   delivered through the OS input boundary to the intended external target, not
   absorbed as GazeKey’s own lasting text-entry focus.
3. **Given** calibration has just completed and typing auto-starts, **When**
   the user immediately dwell-selects a key, **Then** input goes to the
   intended external typing target (calibration UI transition MUST NOT
   permanently capture typing ownership).
4. **Given** the user switches the intended external typing target to a
   different text field, **When** they dwell-select a key, **Then** input goes
   to the newly intended field.

---

### User Story 3 - Runtime Product Package and Repository Cleanup (Priority: P3)

A developer or reviewer looking at the repository can tell what is required to
**run the keyboard product** versus what exists only for benchmarks,
evaluation, diagnostics, debug investigation, or read-only preview
orchestration. Product runtime code lives in `gazekey/`; developer-only
functionality lives outside `gazekey/` (only shared primitives actually required
by product runtime may remain inside). Cleanup is **repository-wide**: obsolete
`archive/` content, scripts, stale tests/docs, unused `GAZEKEY_*` flags,
compatibility shims, and dead artifacts with no active product or justified
developer use are removed. Obsolete dormant typing stacks are deleted and
rebuilt cleanly where they do not fit.

**Why this priority**: Cleanup is part of this stage’s deliverable so typing/OS
work does not sit on a tangled product+tooling tree.

**Independent Test**: Inventory `gazekey/` and the wider repository after
cleanup and confirm (1) evaluation/benchmark/diagnostics/debug/preview
orchestration are not product pipeline stages inside `gazekey/`, (2) no dormant
alternate typing stacks remain in product code, (3) obsolete repo-wide artifacts
and unused flags are gone or justified, and (4) the live path is mapped gaze →
selection → `KeyAction` → OS input boundary.

**Acceptance Scenarios**:

1. **Given** the repository after this feature’s cleanup, **When** a reviewer
   inspects `gazekey/`, **Then** it contains only runtime-product code
   (sensing, calibration, mapping, live UI, dwell typing, `KeyAction` path, OS
   input boundary) plus shared primitives required by that runtime.
2. **Given** benchmark, evaluation, diagnostic, debug, or read-only preview
   orchestration still exists for developers, **When** a reviewer looks for it,
   **Then** it lives outside `gazekey/` and is not implied to be part of the
   normal typing pipeline.
3. **Given** obsolete archive content, unused scripts, stale tests/docs, unused
   `GAZEKEY_*` flags, compatibility code, or dead artifacts with no justified
   use, **When** cleanup completes, **Then** those items are deleted (or moved
   only when still justified as developer tooling outside the product package).
4. **Given** previously dormant typing/intent/selection/facade code, **When**
   cleanup completes, **Then** those artifacts are gone or replaced by the
   single new typing architecture — not preserved as unused parallel
   implementations.

---

### User Story 4 - Keep Calibration and Mapping Isolated (Priority: P4)

Calibration and gaze-to-key mapping continue to produce a mapped gaze point as
today. Typing and OS integration **consume** that point; they do not change how
calibration targets are collected, how the mapper is fit, or how mapping quality
is judged for the mapping stage. No typing or OS logic is folded into
calibration or mapping. Selection produces `KeyAction`s; the OS input boundary
is separate from mapping.

**Why this priority**: Protects the `001` pipeline and avoids reintroducing
monolithic “fix typing by tweaking the mapper” entanglement.

**Independent Test**: Run calibration and mapping fit flows and confirm
behavior and responsibilities match the sealed upstream stage; after success,
confirm typing auto-attaches and only consumes the mapped gaze point through
key detection → selection → `KeyAction` → OS boundary.

**Acceptance Scenarios**:

1. **Given** the user runs calibration, **When** fixation and fit complete,
   **Then** the outcome is still a mapped gaze capability, with no dwell
   selection or OS injection during calibration fixation; after success, typing
   becomes active automatically for the normal product flow without permanently
   stealing external typing-target ownership.
2. **Given** a mapped gaze point is available, **When** typing is active,
   **Then** key detection and dwell selection use that point without modifying
   the calibration/mapping fit path.
3. **Given** mapping improvement work continues separately, **When** this
   feature’s typing path is exercised, **Then** typing success is judged by
   dwell → `KeyAction` → OS delivery, not by raising `001` key-hit percentage
   floors.

---

### Edge Cases

- What happens when no external app has a usable typing target (desktop, empty
  focus)? The system MUST NOT crash; the user gets clear feedback that input
  could not be delivered; no false “typed into GazeKey” success; GazeKey MUST
  NOT permanently claim typing-target ownership.
- What happens when gaze is unstable / leaves and re-enters a key during dwell?
  Dwell MUST reset or restart per the dwell rules; partial dwells MUST NOT
  produce a `KeyAction`.
- What happens after a successful selection if gaze stays on the same key?
  The system MUST NOT auto-repeat that key; re-arm REQUIRES a **clear/confirmed
  gaze leave** (not a single-frame boundary jitter), then return and a new
  completed dwell. Exact leave-confirmation threshold is deferred to planning.
- What happens when tracking is lost mid-dwell? Selection MUST cancel; no
  `KeyAction` MUST be produced.
- What happens when the user dwells on a non-active control (suggestions,
  language, symbols layout, chrome)? No OS-bound `KeyAction` for those controls
  is required by this feature.
- What happens when the user needs to look around without typing? The user
  MUST be able to **pause** typing (primary: dwell on Pause/Resume; optional:
  mouse click). Pause/Resume is an **internal system control** and MUST NEVER
  emit an OS character/action. While paused, typing keys MUST NOT produce
  OS-bound `KeyAction`s until **resume**. Pause MUST NOT require recalibration.
- What happens if OS input is temporarily blocked by the operating system?
  The user MUST be informed that injection failed at the OS input boundary; the
  session MUST remain recoverable (recalibrate / resume typing / retry) without
  corrupting calibration state.
- How does the system treat mouse clicks on active typing keys? While typing is
  active (not paused), a mouse click MUST produce the **same `KeyAction`** as a
  completed dwell (optional convenience), consumed only by the OS input
  boundary. Mouse MUST NOT be required for the P1 gaze success path. While
  paused, mouse clicks on typing keys MUST NOT produce OS-bound `KeyAction`s.
- How is the `KeyAction` → OS boundary tested? The boundary MUST be
  independently testable (selection can be verified to emit `KeyAction`s without
  requiring a live OS inject; the adapter can be verified to consume
  `KeyAction`s). Future features MUST be able to observe the `KeyAction` stream
  without changing this boundary contract.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST determine which virtual keyboard key corresponds to
  the current mapped gaze point (key detection).
- **FR-001a**: After successful calibration/mapping, System MUST
  **automatically start typing** (selection → `KeyAction` → OS input boundary)
  as the normal product flow. There MUST NOT be a required user “Enable Typing”
  step. Read-only gaze preview orchestration MUST be developer/debug only and
  MUST NOT be part of the normal product flow.
- **FR-001b**: System MUST allow the user to **pause** and **resume**
  already-active typing. Gaze dwell on a Pause/Resume control is the **primary
  hands-free** method; an equivalent mouse-click control MAY exist only as
  optional convenience. Pause/Resume is an **internal system control** and MUST
  NEVER produce an OS-bound `KeyAction` or native OS character/action. While
  paused, selections on typing keys MUST NOT be delivered to the OS input
  boundary; resume MUST restore the path without recalibration.
- **FR-001c**: While typing is active (not paused), a mouse click on an
  **active typing key** MUST produce the same `KeyAction` as a completed dwell
  on that key. Mouse interaction is optional convenience only and MUST NOT be
  required for gaze-based success criteria. Optional mouse interaction MUST NOT
  permanently replace the intended external typing target.
- **FR-001d**: Completed dwell or click selection on an active typing key MUST
  produce a **`KeyAction`**. Native OS injection MUST consume `KeyAction`s only
  through a **dedicated OS input adapter/boundary**. Dwell/UI selection code
  MUST NOT call native OS input APIs directly. This boundary MUST remain
  independently testable and MUST NOT prevent future features from observing the
  `KeyAction` stream.
- **FR-001e**: GazeKey interaction (including optional mouse use and the
  calibration-completion → auto-typing transition) MUST NOT permanently replace
  the intended external typing target. Exact Windows focus mechanics are
  deferred to planning.
- **FR-002**: While typing is active (not paused), System MUST support
  dwell-based key selection: continuous gaze on a key for a defined dwell
  period of about **0.8–1.0 seconds** (fixed default for this feature)
  completes selection.
- **FR-003**: System MUST provide visible dwell/selection feedback so the user
  can tell which key is being selected and whether dwell is progressing,
  completed, or cancelled.
- **FR-004**: System MUST cancel or restart dwell when gaze leaves the key
  before dwell completes, without producing a `KeyAction`.
- **FR-004a**: After a successful selection, System MUST NOT fire that same key
  again until mapped gaze has made a **clear/confirmed leave** of that key
  (single-frame boundary jitter MUST NOT qualify); a subsequent same-key
  character requires confirmed leave, return, and a new completed dwell (no
  hold-to-repeat). Exact leave-confirmation threshold is deferred to planning.
- **FR-005**: On a successful typing-key selection, System MUST deliver the
  resulting `KeyAction` through the OS input boundary to the intended external
  typing target.
- **FR-006**: For this feature, the **active typing-key set** whose selections
  MUST produce OS-bound `KeyAction`s is: letter keys **A–Z** (case affected by
  Shift), **Space**, **Backspace**, **Enter**, and modifiers **Shift**,
  **Ctrl**, and **Alt** as presented on the letters keyboard. This set
  explicitly EXCLUDES suggestion placeholders, language-toggle controls,
  symbols/?123 layout keys, and non-typing window chrome. Pause/Resume is
  internal and excluded from OS-bound actions.
- **FR-007**: GazeKey MUST remain usable as an on-top / overlay keyboard while
  preserving the intended external typing target for injected keystrokes.
- **FR-008**: Injected keystrokes MUST NOT treat GazeKey as the permanent
  focused recipient of those characters; delivery is to the intended external
  typing target via the OS input boundary.
- **FR-009**: Typing and OS integration MUST consume mapped gaze only; they
  MUST NOT alter calibration sample collection, mapper fitting, or mapping
  quality-gate responsibilities.
- **FR-010**: Calibration fixation UI MUST remain free of typing/OS concerns
  (no dwell selection or OS injection during calibration fixation).
- **FR-011**: The product package (`gazekey/`) MUST contain only runtime-product
  code required for the keyboard to run. Only shared primitives actually
  required by that product runtime MAY remain in `gazekey/`.
- **FR-012**: Developer-only benchmark, evaluation, diagnostics, debug
  workflows, and read-only preview orchestration MUST live outside `gazekey/`
  and MUST NOT appear as stages of the normal typing product pipeline.
- **FR-013**: Obsolete dormant typing, intent, selection, and facade modules,
  unused environment flags, and dead runtime branches that conflict with the
  new architecture MUST be removed from product code; reuse is allowed only when
  existing code still fits the new design.
- **FR-013a**: Cleanup planning MUST be **repository-wide**, not limited to
  `gazekey/`: audit obsolete `archive/` content, scripts, stale tests/docs,
  unused `GAZEKEY_*` flags, compatibility code, and dead artifacts; delete items
  with no active product or justified developer use.
- **FR-014**: This feature MUST NOT require meeting `001` key-hit accuracy
  floors as a prerequisite for accepting typing/OS behavior; mapping quality
  may continue to improve in parallel.
- **FR-015**: System MUST handle lost tracking, failed OS delivery, and missing
  external typing target without crashing or corrupting calibration/mapping
  state.
- **FR-016**: Predictive text, language switching, symbols-layout typing,
  personalization, multi-monitor support, and advanced accessibility polish are
  out of scope for this feature.
- **FR-017**: Reworking or replacing the sealed calibration → PCA4 mapping path
  for the sake of typing is out of scope; mapping changes belong to mapping
  work, not this feature’s typing/OS path.

### Key Entities

- **Mapped Gaze Point**: Screen position produced by the sealed upstream
  calibration/mapping pipeline; input to key detection.
- **Virtual Key**: On-screen control with identity; may be an active typing key,
  an internal system control (e.g. Pause/Resume), or out-of-scope UI.
- **Active Typing Key**: A key in this feature’s explicit typing-key set
  (A–Z, Space, Backspace, Enter, Shift, Ctrl, Alt on the letters keyboard).
- **Dwell Intent**: Ongoing attempt to select a key by holding gaze; includes
  progress, completion, cancellation, and confirmed-leave re-arm rules.
- **Typing Active / Paused**: Whether selections on active typing keys may be
  delivered to the OS input boundary; pause/resume toggles this without ending
  the mapped-gaze session.
- **Key Action (`KeyAction`)**: Semantic result of a completed selection on an
  active typing key (e.g., type “a”, space, backspace, modifier). Produced by
  selection; consumed by the OS input boundary. Pause/Resume MUST NOT emit a
  `KeyAction` for OS delivery.
- **OS Input Boundary**: Dedicated adapter that consumes `KeyAction`s and
  performs native OS injection. Independently testable; selection/UI MUST NOT
  bypass it. Future features may observe the `KeyAction` stream without changing
  this contract.
- **Intended External Typing Target**: The external application/field that
  should receive injected input; GazeKey MUST NOT permanently replace it.
- **Runtime Product Package (`gazekey/`)**: Code required to run the live
  keyboard product (plus shared primitives required by that runtime).
- **Developer Tooling**: Benchmark, evaluation, diagnostics, debug workflows,
  and read-only preview orchestration kept outside `gazekey/`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a verification session, after successful calibration/mapping
  (with no separate enable-typing step), a user can type a fixed short word
  (at least 4 characters) into an external text field using **only** gaze dwell
  on GazeKey active typing keys (no mouse clicks on keys, no physical keyboard
  for those characters).
- **SC-001a**: Using only gaze (no mouse required), a user can pause typing so
  that subsequent typing-key dwells produce no OS input, then resume and
  continue typing without recalibrating; Pause/Resume itself produces no OS
  character.
- **SC-002**: For every completed dwell selection on an active typing key in
  that session, the character or action delivered via the OS input boundary
  matches the key that showed dwell/selection feedback at completion (no
  mismatch between UI selection, `KeyAction`, and OS delivery). This criterion
  does **not** require meeting `001` key-hit percentage floors.
- **SC-003**: Accidental activations are low enough that the short-word task
  can be finished with at most 2 unintended characters requiring correction
  (Backspace or retype).
- **SC-004**: After overlay setup, the intended external typing target remains
  the recipient for injected characters while GazeKey stays visible for at least
  one continuous short-word attempt without the user needing to re-establish the
  external target between every character; optional mouse use on GazeKey MUST
  NOT permanently steal that target.
- **SC-005**: A reviewer can separate `gazekey/` runtime-product code from
  developer tooling outside it without consulting historical flag notes; no
  dormant alternate typing stacks remain in product code; read-only preview is
  not a required normal-product step; obsolete repo-wide dead artifacts and
  unused flags without justified use are gone.
- **SC-006**: Calibration and mapping flows still produce mapped gaze without
  performing dwell selection or OS injection during calibration fixation;
  typing auto-starts only after mapped gaze is successfully available without
  permanently capturing external typing-target ownership.
- **SC-007**: Selection can be verified to produce `KeyAction`s independently of
  live OS injection, and the OS input boundary can be verified to consume
  `KeyAction`s (boundary remains independently testable).

## MVP Scope *(mandatory for GazeKey)*

**In scope**:

- Mapped gaze → key detection → dwell/click selection → `KeyAction` → dedicated
  OS input boundary → intended external typing target
- Typing auto-starts after successful calibration/mapping (no enable-typing step)
- Pause/resume of active typing: primary via gaze-dwell control; optional mouse
  click convenience; Pause/Resume never emits OS input
- Optional mouse clicks on active typing keys produce the same `KeyAction` path
  as dwell
- Default dwell duration about 0.8–1.0 seconds (fixed; not a tuning research goal)
- Same-key re-arm only after clear/confirmed gaze leave (threshold in planning)
- Overlay keyboard while preserving external typing-target ownership (focus
  mechanics deferred to planning)
- Active typing-key set: A–Z (Shift for case), Space, Backspace, Enter, Shift,
  Ctrl, Alt on the letters keyboard
- Structural cleanup: `gazekey/` = runtime only (+ required shared primitives);
  developer benchmark/evaluation/diagnostics/debug/preview orchestration outside
  `gazekey/`; repository-wide audit/delete of obsolete archive, scripts, stale
  tests/docs, unused `GAZEKEY_*` flags, compatibility code, and dead artifacts;
  remove obsolete dormant modules and rebuild typing cleanly where old code does
  not fit
- Isolation: typing/OS consume mapped gaze; do not entangle calibration/mapping

**Out of scope**:

- Raising or redefining `001` key-hit / pixel / row accuracy floors as this
  feature’s acceptance gate
- Read-only preview as a required step in the normal product flow
- Predictive text / suggestion bar (including OS delivery of suggestion
  placeholders)
- Hebrew/English (or other) language switching
- Symbols/?123 layout as required OS typing keys for this feature
- Personalization / user profiles
- Multi-monitor support
- Advanced accessibility polish beyond basic dwell feedback and recoverable
  error messaging
- Exact Windows focus API mechanics (deferred to planning)
- Exact confirmed-leave threshold numerics (deferred to planning)
- Redesigning the PCA4 calibration/mapping pipeline inside this feature
- Building a large diagnostics platform or dashboard

## Assumptions

- Users run a single primary display and keep GazeKey visible while an ordinary
  external text editor remains the intended typing target for verification.
- A valid calibration/mapping result (mapped gaze) is available before dwell
  typing; obtaining that result uses the existing sealed upstream flow from
  feature `001`, improved separately as needed.
- After mapping succeeds, typing auto-starts; there is no user “Enable Typing”
  gate. Read-only preview orchestration is developer/debug only and lives outside
  `gazekey/` (or equivalent non-product placement).
- Pause/resume is available for already-active typing; gaze is the primary
  hands-free control, mouse click is optional convenience only; Pause/Resume
  never emits OS input.
- While typing is active, mouse clicks on active typing keys share the same
  `KeyAction` → OS input boundary path as dwell; they are optional and not
  required for acceptance of gaze typing.
- Default dwell duration is about **0.8–1.0 seconds**; fine-tuning dwell timing
  beyond that fixed default is not a research goal of this feature.
- Confirmed gaze-leave for same-key re-arm uses a durable leave signal, not
  single-frame jitter; numeric threshold belongs in planning.
- “Intended external typing target” is preserved across GazeKey interaction;
  exact OS focus implementation belongs in planning.
- Overlay / always-on-top style behavior is a starting assumption for MVP
  verification; click-through and advanced windowing polish can wait.
- In-app-only text buffer as the destination for key actions is not the product
  success path; key actions target native OS input via the dedicated boundary
  (gaze primary, mouse optional).
- Obsolete `future` / unused intent / selection / dormant dwell implementations
  are deleted and replaced rather than preserved as facades for later
  reconnection.
- Developer tooling relocation defaults to a top-level developer area (e.g.
  `tools/`) with offline demos remaining under existing script locations only
  when still justified; exact layout is a planning detail.
- Repository-wide cleanup may delete obsolete `archive/` content, unused
  scripts, stale tests/docs, unused `GAZEKEY_*` flags, compatibility code, and
  dead artifacts that have no active product or justified developer use.
- OS permission or security prompts, if any, are accepted as an environment
  prerequisite for verification on the target platform.
- Feature `001` remains the specification of record for calibration, mapping,
  and mapping benchmarks; this feature does not amend `001` to include OS
  typing.
