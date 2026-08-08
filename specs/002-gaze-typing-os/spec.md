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

**Guidance**: GazeKey Constitution v1.3.0 (binding). Separate feature from
`001-calibration-mapping-mvp`. Mapping remains an independently validated
foundation; this feature consumes mapped gaze for dwell/typing/OS and MUST NOT
compensate via mapping changes. Typing success is not gated on `001` key-hit
floors. Calibration → mapping → mapped gaze remains the sealed upstream base.

## Clarifications

### Session 2026-08-08

- Q: When does gaze dwell typing become active after a valid mapped gaze exists? → A: **Revised**: Typing auto-starts after calibration when a **usable mapper / mapped-gaze state** is available (normal calibration flow has produced a mapper capable of supplying mapped gaze for runtime use); **not** gated on `001` benchmark thresholds; read-only preview is developer/debug only (not normal product flow); no user “Enable Typing” step
- Q: After a dwell selection fires a key, how should the next selection on the same key work? → A: Same-key lockout until confirmed leave; **5 consecutive off-key frames**; dwell **0.9 s**; **0.20 s** global cooldown after successful dwell activations that change typing state (keys, Shift, Pause, Resume unless evidenced otherwise); **plus** a **0.25 s** continuous key-switch confirmation before changing the active dwell target mid-dwell (selection stability only — not mapping/gaze smoothing)
- Q: What default dwell duration should complete a key selection in typing mode? → A: Balanced: about 0.8–1.0 seconds (plan locks **0.9 s**)
- Q: How should the user pause and resume already-active typing? → A: Dwellable Pause/Resume (primary) + optional mouse; never emits OS action; **Pause clears pending Shift**
- Q: When typing is active, what should a mouse click on a normal typing key do? → A: Mouse clicks produce the same `KeyAction` path as dwell (optional convenience); OS injection only via ActionDispatcher → OsInputAdapter
- Q: Semantic boundary for selection vs OS injection? → A: Selection produces `KeyAction`; OS inject only via ActionDispatcher → OsInputAdapter; observers distinguish requested vs successfully delivered; dwell/UI never call OS APIs
- Q: External typing-target ownership? → A: Preserve fullscreen calib + top-half keyboard; focus is OS/window-only; early inject validation **after** minimal inject skeleton exists
- Q: Cleanup scope? → A: Cleanup/`tools` first; **post-cleanup gate** (launch, fullscreen calib, PCA4 mapped gaze, top-half layout, independent tools benchmark) before new typing; then skeleton → focus check → full dwell/typing; artifact writers outside product; mapping unchanged
- Q: Active typing-key set for this feature? → A: OS-bound A–Z, Space, Backspace, Enter; Shift one-shot for next letter; clear Shift on Pause/recalib/session reset/termination; Ctrl/Alt visible but non-OS; Pause/Resume internal
- Q: Layout / focus? → A: Preserve current UI layout exactly; focus OS/window-only; no keyboard redesign/reposition
- Q: Dispatcher observation? → A: Observers MUST distinguish selected/requested KeyAction from successfully delivered OS injection
- Q: Dev tooling entry? → A: Separate developer entry points for preview/benchmark; `GAZEKEY_*` requires explicit KEEP / MOVE TO TOOLS / DELETE inventory before deletion
- Q: Cleanup / session writers? → A: Only runtime state in product; developer artifact writers/summaries outside `gazekey/`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type Into an External App by Gaze Dwell (Priority: P1)

After calibration, when a **usable mapper / mapped-gaze state** is available
(normal calibration flow has produced a mapper capable of supplying mapped gaze
for runtime use — **not** requiring `001` benchmark thresholds), **typing
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
becomes a real input device for other programs as soon as a usable mapped-gaze
mapper is available after calibration.

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
   dwell completes, **Then** no `KeyAction` is produced until/unless a new key
   selection later completes; brief raw hit-test flicker MUST NOT immediately
   cancel or switch the active dwell target (see FR-004 key-switch confirmation).
4. **Given** a key has just been selected by dwell, **When** the user keeps
   gaze on that same key without a clear/confirmed leave, **Then** no
   additional selection fires; re-arm requires confirmed leave (**5 consecutive
   off-key frames** per plan), return, and a new completed dwell (single-frame
   boundary jitter MUST NOT count as leave).
5. **Given** gaze typing is active after fullscreen calibration returns to the
   existing top-half keyboard, **When** the user completes dwell selections,
   **Then** GazeKey MUST NOT permanently become the typing-target owner; the
   intended external app remains the recipient without requiring focus restore
   between every character (focus treated as OS/window behavior; no layout
   redesign).
6. **Given** typing is active after mapping success, **When** the user pauses
   via the dwellable Pause control (or optional click control), **Then** further
   typing-key dwells/clicks MUST NOT send OS-bound `KeyAction`s until resume,
   and Pause/Resume itself MUST NOT emit any OS character/action.
7. **Given** typing is paused, **When** the user resumes via dwell (primary)
   or optional click, **Then** dwell selection → `KeyAction` → OS input works
   again without recalibration.
8. **Given** a suggestion placeholder, language control, symbols-layout key,
   Ctrl, or Alt is visible, **When** the user dwells or clicks it, **Then** this
   feature MUST NOT require OS delivery of those controls (Ctrl/Alt produce no
   OS input in 002).
9. **Given** Shift then a letter, **When** both selections complete, **Then**
   only the letter is delivered as a one-shot shifted character and Shift does
   not remain armed for further letters.
10. **Given** Shift is armed, **When** the user Pauses, recalibrates, resets the
    mapping/session, or the tracking/mapping session ends, **Then** pending
    Shift MUST be cleared so a later letter is not unexpectedly uppercase.
---

### User Story 2 - Preserve External Typing-Target Ownership (Priority: P2)

While injecting into another application, the user can still see and use the
virtual keyboard in its **existing top-half** layout after **fullscreen
calibration** (layout preserved exactly — no redesign or reposition). The
external app remains usable in the lower half. Interacting with GazeKey (gaze
dwell, optional mouse, and calibration → auto-typing) MUST NOT permanently
replace the intended external typing target. Focus is treated as an
**OS/window-behavior** concern only (validated early after the calib→keyboard
transition).

**Why this priority**: Without preserving the external typing target, P1 cannot
be used in practice.

**Independent Test**: Place an external editor in the lower half, complete
fullscreen calibration, confirm top-half keyboard geometry unchanged, inject
several characters without re-focusing the editor between them.

**Acceptance Scenarios**:

1. **Given** an external app is the intended typing target in the lower half,
   **When** the user interacts with GazeKey by gaze after calib, **Then** the
   keyboard remains in its current top-half position and usable without a layout
   redesign.
2. **Given** GazeKey is shown in its existing geometry, **When** a typing key is
   selected by dwell or optional mouse click, **Then** the resulting `KeyAction`
   is delivered through the OS input boundary to the intended external target.
3. **Given** calibration has completed with a usable mapper/mapped-gaze state and
   typing auto-starts, **When**
   the user immediately dwell-selects keys, **Then** input reaches the external
   target without permanently capturing typing ownership and without requiring
   focus restore between every character (early validation criterion).
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
  focus)? The system MUST NOT crash; provide **simple non-blocking feedback**
  that input could not be delivered; preserve the active calibration/mapping
  session; no false “typed into GazeKey” success; GazeKey MUST NOT permanently
  claim typing-target ownership. Do not add retry loops, target-management
  complexity, or new UI flows for this case.
- What happens when gaze is unstable / leaves and re-enters a key during dwell?
  A brief raw hit-test change away from the current dwell key MUST NOT
  immediately switch targets or cancel progress. Dwell progress MUST **freeze**
  on the current key while a switch is pending; if gaze returns before **0.25 s**
  continuous confirmation on a different key (or continuous off-key), progress
  MUST **resume**. A confirmed switch (one different key held continuously for
  **0.25 s**) MUST cancel the old key’s dwell and start the new key from zero.
  Continuous off-key for **0.25 s**, or continuous away-time of **0.25 s**
  without a confirmed new key (wandering), MUST cancel without a `KeyAction`.
  Tracking/mapped-gaze loss is **not** part of this grace and MUST cancel
  immediately with no `KeyAction`.
- What happens after a successful selection if gaze stays on the same key?
  The system MUST NOT auto-repeat that key; re-arm REQUIRES a **clear/confirmed
  gaze leave** of **5 consecutive off-key frames** (not a single-frame boundary
  jitter), then return and a new completed dwell. Global **0.20 s** cooldown
  applies after successful dwell activations that change typing state (typing
  keys, Shift, Pause, Resume) unless evidence justifies an exception; dwell
  duration default is **0.9 s**; mid-dwell key changes use **0.25 s** switch
  confirmation (separate from post-fire 5-frame leave).
- What happens when tracking is lost mid-dwell? Selection MUST cancel; no
  `KeyAction` MUST be produced.
- What happens when the user dwells on Ctrl, Alt, or other non-OS controls
  (suggestions, language, symbols, chrome)? No OS-bound `KeyAction` MUST be
  produced for those controls in this feature.
- What happens when the user needs to look around without typing? The user
  MUST be able to **pause** typing (primary: dwell on Pause/Resume; optional:
  mouse click). Pause/Resume is an **internal system control** and MUST NEVER
  emit an OS character/action. While paused, typing keys MUST NOT produce
  OS-bound `KeyAction`s until **resume**. Pause MUST NOT require recalibration.
- What happens if OS input is temporarily blocked by the operating system?
  The user MUST be informed that injection failed at the OS input boundary; the
  session MUST remain recoverable (recalibrate / resume typing / retry) without
  corrupting calibration state. Observers MUST still see a requested action as
  distinct from a failed delivery.
- How does the system treat mouse clicks on active typing keys? While typing is
  active (not paused), a mouse click MUST produce the **same `KeyAction`** as a
  completed dwell (optional convenience), consumed only by the OS input
  boundary. Mouse MUST NOT be required for the P1 gaze success path. While
  paused, mouse clicks on typing keys MUST NOT produce OS-bound `KeyAction`s.
- How is the `KeyAction` → OS boundary observed? Future features MUST be able to
  distinguish a **selected/requested** `KeyAction` from one **successfully
  delivered** to the OS, without dwell/UI calling native OS APIs directly.
- How is layout handled? Fullscreen calibration and the existing top-half
  keyboard position MUST be preserved; focus issues MUST NOT be “solved” by
  redesigning or repositioning the keyboard.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST determine which virtual keyboard key corresponds to
  the current mapped gaze point (key detection).
- **FR-001a**: After calibration, when a **usable mapper / mapped-gaze state** is
  available — defined as the normal calibration flow having produced a mapper
  capable of supplying mapped gaze for runtime use — System MUST
  **automatically start typing** (selection → `KeyAction` → OS input boundary)
  as the normal product flow. Auto-start MUST NOT require `001` benchmark
  thresholds. There MUST NOT be a required user “Enable Typing” step. Read-only
  gaze preview orchestration MUST be developer/debug only and MUST NOT be part
  of the normal product flow.
- **FR-001b**: System MUST allow the user to **pause** and **resume**
  already-active typing. Gaze dwell on a Pause/Resume control is the **primary
  hands-free** method; an equivalent mouse-click control MAY exist only as
  optional convenience. Pause/Resume is an **internal system control** and MUST
  NEVER produce an OS-bound `KeyAction` or native OS character/action. While
  paused, selections on typing keys MUST NOT be delivered to the OS input
  boundary; resume MUST restore the path without recalibration. Entering Pause
  MUST clear any pending Shift oneshot arm.
- **FR-001c**: While typing is active (not paused), a mouse click on an
  **active typing key** MUST produce the same `KeyAction` as a completed dwell
  on that key. Mouse interaction is optional convenience only and MUST NOT be
  required for gaze-based success criteria. Optional mouse interaction MUST NOT
  permanently replace the intended external typing target.
- **FR-001d**: Completed dwell or click selection on an OS-bound typing key MUST
  produce a **`KeyAction`**. Native OS injection MUST consume `KeyAction`s only
  through **ActionDispatcher → OsInputAdapter**. Dwell/UI MUST NOT call native
  OS input APIs directly. Observers MUST distinguish a **requested/selected**
  `KeyAction` from one **successfully delivered** to the OS. The boundary MUST
  remain independently testable.
- **FR-001e**: GazeKey interaction (including optional mouse use and the
  calibration-completion → auto-typing transition) MUST NOT permanently replace
  the intended external typing target. Focus is an **OS/window-behavior** issue
  only. Existing **fullscreen calibration** and **top-half keyboard** layout
  MUST be preserved (no redesign or reposition to address focus).
- **FR-002**: While typing is active (not paused), System MUST support
  dwell-based key selection with default **0.9 seconds** dwell, **0.20 seconds**
  global cooldown after successful dwell-based activations that change typing
  state (including OS-bound keys, Shift, Pause, and Resume, unless
  implementation evidence justifies an exception), same-key lockout,
  confirmed leave of **5 consecutive off-key frames** after fire, and
  **0.25 seconds** continuous key-switch confirmation before changing the
  active dwell target mid-dwell.
- **FR-003**: System MUST provide visible dwell/selection feedback on the
  **existing** keyboard layout/geometry (no redesign): the current **active**
  dwell key MUST show a clearly visible colored border/highlight; a
  semi-transparent circular progress ring MUST appear on that key and progress
  over the **0.9 s** dwell; a full circle MUST mean selection/activation;
  confirmed leave/cancel before completion MUST hide/reset the ring with **no**
  selection; during a pending key-switch the visual target MUST remain on the
  current key with frozen progress; a **confirmed** switch (0.25 s continuous
  on a different key) MUST move visuals to the new key and restart dwell from
  zero. The user MUST be able to tell which key is being selected and whether
  dwell is progressing, completed, or cancelled.
- **FR-004**: System MUST NOT treat every single raw off-key / other-key
  hit-test frame as an immediate dwell cancel or target switch. Mid-dwell
  target changes require **0.25 s** continuous confirmation on one different
  key (or continuous off-key / unresolved away-time of 0.25 s to cancel).
  Confirmed cancel/restart MUST NOT produce a `KeyAction`. Tracking or
  mapped-gaze loss MUST cancel immediately (no grace) with no `KeyAction`.
- **FR-004a**: After a successful selection, System MUST NOT fire that same key
  again until mapped gaze has made a **clear/confirmed leave** of **5
  consecutive off-key frames** (single-frame jitter MUST NOT qualify); then
  return and a new completed dwell (no hold-to-repeat).
- **FR-005**: On a successful typing-key selection, System MUST attempt delivery
  of the resulting `KeyAction` through the OS input boundary and report delivery
  outcome distinctly from request.
- **FR-006**: The **OS-bound typing-key set** is: **A–Z**, **Space**,
  **Backspace**, and **Enter**. **Shift** is a **one-shot** modifier for the
  **next letter** only. Pending Shift MUST also clear on **Pause**,
  **recalibration**, **mapping/session reset**, **tracking/mapping session
  termination**, and similar transitions where a stale arm could cause an
  unexpected later uppercase character. **Ctrl** and **Alt** MAY remain visible
  but MUST NOT produce OS input; shortcuts and multi-key combinations are out of
  scope. Suggestions, language toggle, symbols/?123, and chrome are excluded.
  Pause/Resume is internal and excluded from OS-bound actions.
- **FR-007**: GazeKey MUST remain usable in its **existing** geometry (top-half
  after calib) while preserving the intended external typing target.
- **FR-008**: Injected keystrokes MUST NOT treat GazeKey as the permanent
  focused recipient; delivery is to the intended external typing target via the
  OS input boundary.
- **FR-009**: Typing and OS integration MUST consume mapped gaze only; they
  MUST NOT alter calibration sample collection, mapper fitting, or mapping
  quality-gate responsibilities. Calibration/mapping remain isolated and
  unchanged by this feature.
- **FR-010**: Calibration fixation UI MUST remain free of typing/OS concerns
  and MUST keep the current fullscreen calibration presentation.
- **FR-011**: `gazekey/` MUST contain only runtime-product code. Only runtime
  session/calibration **state** truly needed by the product MAY remain;
  developer artifact writers and summaries MUST live outside `gazekey/` where
  appropriate.
- **FR-012**: Benchmark, evaluation, diagnostics, debug, and read-only preview
  MUST live outside `gazekey/` as **separate developer entry points**, not as
  normal product modes. Before deleting or relocating any `GAZEKEY_*` flag,
  System/project MUST maintain an explicit inventory of each flag, where it is
  read, whether tests/docs depend on it, and classification KEEP / MOVE TO TOOLS
  / DELETE — no generic “remove unused flags” without that inventory.
- **FR-013**: Obsolete dormant typing/intent/selection/facade modules, unused
  flags (per inventory), and dead branches MUST be removed. Package-boundary
  cleanup MUST be followed by a **post-cleanup behavior gate** (launch,
  fullscreen calibration, PCA4 mapped gaze, top-half layout preserved,
  independent tools benchmark) before new typing implementation proceeds.
- **FR-013a**: Cleanup MUST be **repository-wide**: audit obsolete `archive/`
  content, scripts, stale tests/docs, unused `GAZEKEY_*` flags, compatibility
  code, and dead artifacts; delete items with no active product or justified
  developer use.
- **FR-014**: This feature MUST NOT require meeting `001` key-hit accuracy
  floors as a prerequisite for accepting typing/OS behavior.
- **FR-015**: System MUST handle lost tracking, failed OS delivery, and **no
  usable external typing target** without crashing or corrupting/ending the
  active calibration/mapping session. Feedback for failed delivery or missing
  target MUST be **simple and non-blocking**. The system MUST NOT add retry
  logic, target-management complexity, or new UI flows solely for these cases.
- **FR-016**: Predictive text, language switching, symbols-layout typing,
  Ctrl/Alt shortcuts, multi-key combinations, personalization, multi-monitor
  support, keyboard redesign/reposition, and advanced accessibility polish are
  out of scope.
- **FR-017**: Reworking or replacing the sealed calibration → PCA4 mapping path
  for typing is out of scope.

### Key Entities

- **Mapped Gaze Point**: Upstream mapping output; typing consumes only.
- **Virtual Key**: On-screen control (OS-bound key, system control, or non-OS UI).
- **OS-Bound Typing Key**: A–Z, Space, Backspace, Enter; Shift as one-shot arm.
- **Dwell Intent**: Progress/cancel/fire/lock with 5-frame confirmed leave.
- **Typing Active / Paused**: Whether OS-bound selections may be requested.
- **Key Action (`KeyAction`)**: Requested semantic action (`CHAR` / `BACKSPACE` /
  `ENTER`). Pause/Resume and Ctrl/Alt never emit OS-bound actions.
- **Action Request / Action Delivery**: Observer-visible requested vs delivered
  (success/failure) outcomes through ActionDispatcher → OsInputAdapter.
- **Intended External Typing Target**: External field that should receive input.
- **Runtime Product Package (`gazekey/`)**: Product runtime only (minimal state).
- **Developer Tooling**: Separate entry points outside `gazekey/` for preview,
  benchmark, debug, and artifact writers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After calibration when a usable mapper/mapped-gaze state is
  available (no enable-typing step; not gated on `001` thresholds), a user can
  type a fixed short word (≥4 characters) into an external field using **only**
  gaze dwell on OS-bound keys.
- **SC-001a**: Using only gaze, pause then resume without recalibrating; Pause
  emits no OS character.
- **SC-002**: For completed dwells on OS-bound keys, delivered OS action matches
  UI selection when delivery succeeds; request vs failed delivery remain
  distinguishable. Not gated on `001` key-hit floors.
- **SC-003**: Short-word task finishes with at most 2 unintended characters
  needing correction.
- **SC-004**: After fullscreen calib → existing top-half keyboard, external
  target receives a continuous short-word attempt without focus restore between
  every character; layout unchanged; mouse optional and must not permanently
  steal the target.
- **SC-005**: Reviewer can separate `gazekey/` from tools entry points; no
  dormant typing stacks in product; preview/benchmark not product modes;
  unjustified flags/artifacts gone.
- **SC-006**: Calibration/mapping unchanged in role; no dwell/OS during
  fixation; typing auto-starts when a usable mapper/mapped-gaze state is
  available after calibration without permanently capturing
  external typing ownership.
- **SC-007**: Tests can observe requested `KeyAction`s without live OS inject and
  can observe delivery success/failure via the adapter boundary.

## MVP Scope *(mandatory for GazeKey)*

**In scope**:

- Mapped gaze → detect → dwell/click → `KeyAction` → ActionDispatcher →
  OsInputAdapter → external target
- Auto-start typing after calib/mapping; Pause/Resume (no OS emit)
- Dwell **0.9 s**; **0.20 s** cooldown after dwell activations that change typing
  state (keys/Shift/Pause/Resume unless evidenced otherwise); same-key lock;
  **5-frame** leave
- Shift one-shot for next letter; clear on Pause/recalib/session reset/termination;
  mouse optional same `KeyAction` path
- Preserve fullscreen calib + top-half keyboard; inject skeleton before focus
  validation; post-cleanup gate before typing work
- Cleanup early with explicit `GAZEKEY_*` inventory; artifact writers outside
  product; calib/mapping isolated/unchanged

**Out of scope**:

- `001` accuracy floors as this feature’s gate
- Preview/benchmark as normal product modes
- Predictive text / suggestions / language / symbols OS set
- Ctrl/Alt shortcuts and multi-key combinations
- Keyboard redesign or reposition
- Personalization, multi-monitor, advanced accessibility polish
- Changing the PCA4 calibration/mapping pipeline
- Diagnostics platform / dashboard

## Assumptions

- Single primary display; external editor usable in the lower half with the
  existing top-half keyboard.
- Upstream `001` mapping flow supplies mapped gaze; this feature does not change
  it.
- Typing auto-starts when a usable mapper/mapped-gaze state is available after
  calibration (usable = normal calib produced a runtime-capable mapper); not
  gated on `001` thresholds; preview/benchmark are separate developer entry
  points.
- Dwell visuals: colored key highlight + semi-transparent circular progress ring
  on existing geometry (no redesign).
- Dwell defaults: 0.9 s / 0.20 s activation cooldown / 5-frame leave (not a tuning
  study).
- Shift is one-shot; clears on letter consume and on Pause/recalib/session
  reset/termination; Ctrl/Alt visible but non-OS.
- Implementation order: cleanup → post-cleanup gate → inject skeleton → focus
  validation → full dwell/typing; `GAZEKEY_*` changes require KEEP/MOVE/DELETE
  inventory first.
- Focus issues are OS/window-only; early validation after calib→keyboard using
  the minimal inject path: validate → minimal OS/window-only fix if needed →
  rerun → **PASS** before full typing; if still failing after the minimal fix,
  stop for review (do not expand scope automatically).
- In-app text buffer is not the success destination.
- Obsolete future/intent/selection/dormant dwell deleted in cleanup; developer
  writers live in tools.
- Feature `001` remains SoT for calibration/mapping benchmarks.

