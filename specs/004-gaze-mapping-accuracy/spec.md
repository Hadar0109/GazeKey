# Feature Specification: Gaze Mapping Accuracy

**Feature Branch**: `004-gaze-mapping-accuracy`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "Create a new feature specification for
004-gaze-mapping-accuracy. GazeKey already has a complete product flow from
camera through calibration, mapping, virtual keyboard, dwell, OS typing, and
predictive text. Feature 003 is the current product baseline. The blocker is
gaze-to-key accuracy: during real use the user tried to type `hadar` but mapped
gaze frequently focused and activated the wrong keys. The error is visible at
the gaze-to-key stage, before prediction or OS input can compensate. Feature
004 must make user gaze → correct virtual-keyboard key accurate, stable, and
repeatable enough for practical gaze typing. Focus the active path from
tracking through calibration, mapping, runtime prediction, keyboard
coordinates, and key hit detection. The developer benchmark is evaluation
infrastructure only and must not participate in calibration, fitting, runtime
correction, key selection, dwell, enabling typing, or normal product
execution. Audit findings are investigation areas, not predetermined fixes.
Improve the existing simple mapping pipeline before adding mapper complexity.
Preserve Feature 003 product behavior. Do not prescribe calibration-point
count, mapper replacement, smoothing, regularization, or correction layers in
this specification."

**Guidance**: GazeKey Constitution v1.3.0 (binding). This is a **mapping
foundation** feature: calibration quality, feature consistency, training vs
live prediction alignment, keyboard geometry, and gaze-to-key accuracy.
Downstream Feature 003 capabilities (dwell typing, OS input, predictive text)
MUST continue to **consume mapped gaze only** and MUST NOT be retuned to hide
mapping error. Mapping accuracy MUST remain independently measurable.

## Clarifications

### Session 2026-08-16

- **Fresh baseline first**: Capture **two** current-state mapping sessions
  (baseline A and B) before any accuracy-related product/mapping code
  change, so later experiments compare against a known reference and
  session-to-session variability is visible. A later **3-session** protocol
  on the kept stack is the final repeatability check (SC-004), not a
  substitute for those two baselines.
- **Developer evaluation fidelity**: Evaluation stays out of the product
  path, but must measure the same mapper, geometry, and key-hit behavior the
  runtime uses as closely as possible.
- **67% is a reference floor**: Historical intended-key thresholds are an
  initial comparison bar, not automatically Feature 004’s final definition of
  practical typing success. Final acceptance is resolved later from baseline,
  held-out accuracy, key geometry, and real typing.
- **Targets are spatial coordinates**: Calibration targets are screen
  positions. A target may sit on a key center, but key labels, key IDs, and
  row semantics must not affect mapper fitting unless explicitly justified.
- **Calibration layout is open**: Placement and coverage of calibration
  points must be investigated. The current key-centered layout is not assumed
  optimal. Calibration domain and required prediction domain are distinct.
- **Error vs key size**: Pixel error alone may be insufficient; planning
  should also consider error relative to actual key dimensions and
  boundaries.
- **Focus vs dwell**: Wrong mapped-key focus is already a mapping failure,
  even if dwell never activates a key.
- **Continued diagnosis**: Known audit findings are hypotheses. If they are
  fixed or ruled out and accuracy is still insufficient, investigation
  continues (coverage, mapping assumptions, feature sufficiency, or the
  mapper itself). Unproven experimental changes must not be stacked.
- **Word checks vs baseline**: Practical typing checks compare **wrong-focus
  outcomes** to the same words on the two-session baseline (not only
  “typical” / “frequent”). Development uses `hadar`; final accept adds
  2–3 short words that were not used during development.
- **KEEP checkpoints**: Each accepted `keep` is recorded with a Git commit
  so later work can revert to the last proven state.
- **Layout candidates**: More than one calibration-layout candidate MAY be
  tested, but only one per experiment. A failed or inconclusive first
  candidate does not prove the current key-centered layout is optimal.

### Session 2026-08-20

- **Product condition is head-stabilized**: The delivered system is used
  **with the chin/head support**. The product goal is a stable head and the
  highest achievable mapping accuracy under that condition. All accuracy
  evaluation, `hadar` word checks, and repeatability runs are therefore
  captured **with** the support. Free-head sessions remain useful diagnostic
  context but MUST NOT become the optimization target, even when they pass
  more easily. Baseline A and B were captured free-head; they stay the
  mandatory pre-change reference (SC-011), and a product-condition reference
  pair is captured once sessions can pass under the support.
- **Accuracy must not depend on head motion**: If mapping accuracy is found
  to rely on head movement correlated with target position (for example head
  pitch leaking into a vertical eye feature), that dependency is a **defect
  to remove**, not a signal to preserve. A product that needs the user's head
  to move contradicts the stabilized product condition and is not repeatable.
- **Gates must measure what mapping uses**: A blocking calibration
  quality check MUST score a representation the mapper actually consumes.
  A check that scores a derived or clamped proxy can reject sessions whose
  mapper-relevant signal is better than accepted sessions, which blocks
  measurement rather than protecting the user. Fixing *what* such a check
  measures is not the same as loosening pass/fail, and does not relax
  FR-004, FR-005, or SC-009.
- **Passing the gates is necessary, not sufficient**: Baseline A and B both
  passed the current calibration gates and were still not practically
  typeable. Gate pass MUST NOT be reported as mapping success.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Look at a Key and Hit That Key (Priority: P1)

After calibration, the user looks at a letter on the virtual keyboard in order
to type. Mapped gaze must already identify that key (**mapped-key / focus
accuracy**). Existing dwell may then activate the same key (**dwell activation
accuracy**). Wrong focus is already a mapping failure, even if dwell never
fires. This must work for ordinary typing — for example looking at H, A, D, A,
R in sequence to type `hadar` — not only when looking at calibration-dot
locations. Practical word checks MUST be done **without predictive suggestions
masking mapping errors**.

**Why this priority**: Wrong-key focus and activation is the current product
blocker. If gaze does not land on the intended key, dwell, OS typing, and
predictive text cannot produce the intended text.

**Independent Test**: Calibrate, then look at intended letter **and**
editing/control keys (including locations that were not calibration
targets). Confirm that **focus** matches the intended keys even before
dwell fires. Disable or ignore suggestions. Compare `hadar` wrong-focus
to the two-session baseline.

**Acceptance Scenarios**:

1. **Given** calibration has completed and typing is available, **When** the
   user looks steadily at an intended letter key, **Then** mapped gaze focuses
   that key rather than a neighboring or different-row key — this is already
   success or failure of mapping, before dwell.
2. **Given** mapped gaze is focused on the intended key and the user holds
   gaze long enough for the existing dwell behavior, **When** the key
   activates, **Then** the activated key is that same intended key.
3. **Given** the user attempts a short intended word such as `hadar` by looking
   at each letter in order **with suggestions unused / not masking errors**,
   **When** they finish the sequence, **Then** wrong-key **focus** letters
   are recorded and compared to the same word on the two-session baseline
   (fewer or equal wrong-focus letters is the comparison; wrong focus is
   still a mapping failure even if dwell never fires).
4. **Given** the user looks at keys whose centers were **not** calibration
   target positions as well as locations that were — including
   **editing/control keys** in the required prediction domain — **When**
   mapping is evaluated, **Then** intended-key accuracy is assessed on
   those slices. Success is not claimed from calibration locations or
   letter keys alone. Feature 003 suggestion / prediction-bar keys are
   **not** a 004 mapped-key acceptance surface (preservation only).

---

### User Story 2 - Calibration Captures the Gaze That Mapping Will Use (Priority: P1)

The user completes calibration by looking at each **spatial target** (a
screen position, which may or may not sit on a key center). The system
accepts only observations that are stable for the **same gaze representation
later used to predict keyboard position**. Samples that represent one target
are built from observations that still belong together — they must reflect
the user actually looking at that position, not a mixed or silently unstable
gaze.

**Why this priority**: Mapping cannot be more accurate than the calibration
data it is taught from. Unstable or incoherent target samples make later
parameter changes guesswork.

**Independent Test**: Run a calibration session and inspect (via developer
logs or evaluation records, not on-screen during fixation) that accepted
samples for each target are stable in the mapping representation, that
rejected/unstable observations are not silently kept, and that a target sample
preserves relationships among eye signals captured together.

**Acceptance Scenarios**:

1. **Given** the user is fixating a calibration target, **When** gaze is
   unstable in the representation used for mapping, **Then** those observations
   are not silently accepted as valid samples for that target.
2. **Given** several observations are accepted for one target, **When** they
   are combined into the sample used for mapping, **Then** the combined sample
   still represents a coherent look at that target (relationships among eye
   signals from the same observations are preserved).
3. **Given** left and right eye signals are used, **When** calibration and
   later prediction run, **Then** each eye’s signals have the same meaning in
   both stages (no silent swap, inversion, or one-sided treatment unless
   explicitly justified).
4. **Given** calibration finishes, **When** the outcome is reported, **Then**
   the user sees pass or fail only after the session ends, and the fixation
   screen itself stayed limited to the target and optional simple progress.

---

### User Story 3 - Training and Live Prediction Speak the Same Language (Priority: P1)

The user calibrates, then types. The mapping that was learned from calibration
samples is applied to live gaze without an accidental mismatch in preparation
(smoothing, averaging, missing-eye handling, signal order, or left/right
treatment). Any remaining difference is intentional, documented, and justified
by accuracy evidence.

**Why this priority**: A mapper taught on one kind of input and queried with
another will miss keys even when calibration “felt” stable.

**Independent Test**: Compare the prepared gaze representation used to teach
the mapping with the prepared representation used during live prediction for
the same look at a key; confirm they are compatible, and that any difference
is recorded as an intentional choice.

**Acceptance Scenarios**:

1. **Given** a successful calibration, **When** the user looks at a known
   keyboard location during typing, **Then** live prediction uses a gaze
   representation compatible with the one used to teach the mapping.
2. **Given** a difference exists in smoothing, averaging, missing-value
   handling, signal order, or left/right treatment, **When** that difference is
   reviewed, **Then** it is either removed or kept only with a written
   justification tied to measured mapping accuracy.
3. **Given** one eye’s signal is missing or invalid, **When** calibration or
   live prediction runs, **Then** handling is the same policy in both stages
   (accept, reject, or degrade) rather than silently diverging.

---

### User Story 4 - Keyboard Geometry Matches What Mapping Was Taught (Priority: P2)

Calibration targets, the positions the mapper is taught, the visible key
centers, live mapped gaze, and the regions used to decide which key is hit
all refer to the **same keyboard geometry**. Fullscreen calibration, the
restored top-half keyboard, window resize or move, and screen scaling must not
leave mapping aimed at a stale or different layout than the user sees.
This includes the current Feature 003 keyboard layout.

**Why this priority**: Accurate gaze prediction onto the wrong rectangle still
selects the wrong key. Feature 003 changed keyboard layout without intending
to retune mapping; 004 must verify that geometry stayed consistent.

**Independent Test**: After calibration, compare target positions, visible key
centers, and hit regions in the restored typing layout; repeat after a
resize/restore if the product allows it; confirm mapped gaze and key hits use
those same coordinates.

**Acceptance Scenarios**:

1. **Given** calibration targets were shown as screen positions, **When**
   typing resumes on the product keyboard, **Then** those taught coordinates
   still refer to the same restored-layout geometry used for live prediction
   and key hit regions (a target may coincide with a key center, but it is
   not defined by a key label).
2. **Given** the user looks at a visible key, **When** mapped gaze is hit-tested,
   **Then** the hit region is the same geometry the user sees (no systematic
   offset from local vs screen coordinates, stale layout, or scaling mismatch).
3. **Given** the Feature 003 keyboard layout (including enlarged keys and the
   current bottom-row controls), **When** mapping and hit detection run,
   **Then** they use that layout’s actual positions — not an older layout’s
   coordinates.
4. **Given** a **supported** keyboard resize, reposition, or scaling path
   exists, **When** mapping continues, **Then** geometry is refreshed to
   match the new positions or typing is not left using stale coordinates.
   **If no such user-facing path exists** (as-built: frameless fixed
   overlay; overlay close/restore is the layout transition), that
   unsupported case MUST be recorded and FR-014 treated as closed for
   user-driven resize — overlay-vs-restored-keyboard geometry still MUST
   hold.

---

### User Story 5 - Measure Mapping Independently, Then Change One Thing (Priority: P2)

Developers (and the user during accuracy work) can tell whether mapping
improved without changing how the product types. Evaluation is separate from
calibration, fitting, and live key selection, but it must still be a
**trustworthy measurement** of the same mapping path the product uses. Before
the first accuracy-related code change, a **fresh current-state baseline** is
captured. Accuracy work then follows: observe a failure pattern, form a
hypothesis, change one logical area, measure against that baseline, then
**keep**, **revert**, or mark **inconclusive**. Unproven changes are not
stacked.

**Why this priority**: Combined experimental changes and in-product evaluation
shortcuts hide the real cause. Constitution requires independent mapping
metrics; this feature requires that those metrics not leak into the product.

**Independent Test**: Record **two** pre-change baseline sessions with
developer evaluation only; confirm the product typing path does not call or
depend on that evaluation; apply one focused change; compare the same
evaluation to both baselines; record keep / revert / inconclusive; on
`keep`, record a Git checkpoint.

**Acceptance Scenarios**:

1. **Given** calibration has finished, **When** a developer mapping evaluation
   runs, **Then** it reports mapped-key (focus) hits separately from dwell
   activation, including horizontal/vertical error, error relative to key
   size when useful, and row correctness, and it distinguishes repeating
   calibration locations from mapping other usable keys.
2. **Given** the product is used for normal typing, **When** no developer
   evaluation is requested, **Then** calibration, mapping, key selection,
   dwell, and typing enablement do not consult the evaluation.
3. **Given** no accuracy-related code change has been made yet, **When**
   Feature 004 measurement starts, **Then** **two** fresh current-state
   baseline sessions are recorded (A and B) so later comparison can see
   session variability.
4. **Given** an accuracy experiment, **When** a change is made, **Then** it
   addresses one documented failure pattern and one hypothesis, is measured
   against those baselines (or the last kept state), and ends with keep,
   revert, or inconclusive — unproven changes are not left stacked under
   later experiments. A `keep` includes a Git checkpoint of that state.
5. **Given** an evaluation run finishes, **When** a tester reads the run
   summary, **Then** they can state pass/fail and the primary mapping metrics
   without reading verbose logs.

---

### Edge Cases

- Calibration observations that look stable in a simplified average but are
  unstable in the full representation used for mapping
- One eye missing, blinking, or inconsistent with the other eye during
  calibration or live prediction
- Combining accepted observations in a way that would no longer correspond to
  any single look at the target
- User looks at keys that were never calibration targets (interiors, edges,
  adjacent letters)
- Fullscreen calibration overlay vs restored top-half product keyboard
- Keyboard resize, reposition, or screen scaling after mapping was taught
  (close as **unsupported** if no user-facing path exists; overlay close vs
  restored keyboard still applies)
- Two current-state baseline sessions that disagree (session noise must be
  visible before the first mapping change; it does not skip the later
  3-session final protocol)
- Final word checks on short words that were **not** practiced during
  development experiments
- Repeated calibrations on the same setup with different mapping quality
- Mapping that is accurate on calibration locations but wrong on nearby keys
- Wrong mapped-key focus with no dwell activation (still a mapping failure)
- Practical word checks where suggestions would complete the word despite
  wrong-key mapping
- Existing dwell, suggestions, or OS delivery continuing while mapping is wrong
  (must not be “fixed” by changing those stages)
- Developer evaluation unavailable or not run — product typing must still
  function using mapping alone
- Identified collection/geometry issues corrected or ruled out, yet mapping
  still misses intended keys (diagnosis must continue)
- Calibration quality gates that **warn** rather than block, so a session
  that would fail historical LOOCV / train-pixel / region checks still
  enables typing (investigate correlation with held-out / practical typing;
  do not assume gates must be hardened)
- A **blocking** gate that rejects a session whose mapper-relevant signal is
  measurably better than sessions the same gate accepted (gate scores a
  derived/clamped proxy instead of the representation the mapper fits) —
  measurement is blocked, so no experiment under that condition is decidable
- A vertical or horizontal gaze signal that is only usable because head
  motion happened to correlate with target position (accuracy that
  disappears once the head is stabilized)
- Predictions that fall **outside** the prediction-domain clip rect and are
  **clamped** onto the AABB (investigate whether that pins edge keys; do not
  assume clamp must be removed)
- Spatial row/column tags used by quality checks that group Space or other
  non-letter controls with letter-row peers (investigate metadata vs
  `screen_x/y` clusters; do not assume retagging)
- Auto-alpha selecting the **largest** ridge alpha among near-best LOOCV
  scores (investigate only if mapper diagnosis is reached; do not assume
  the rule must change)

## Requirements *(mandatory)*

### Functional Requirements

**Calibration data quality**

- **FR-001**: System MUST collect calibration data that represents the user's
  actual gaze at each calibration target.
- **FR-002**: System MUST NOT silently accept observations that are unstable
  for the gaze representation later used to predict keyboard position.
- **FR-003**: When accepted observations for a target are combined into the
  sample used for mapping, the system MUST preserve meaningful relationships
  among eye signals captured from the same observations.
- **FR-004**: During target fixation, the calibration screen MUST show only
  the target and an optional simple progress indicator; metrics, sample
  counts, quality scores, and debug text MUST NOT appear while the user is
  expected to look at the target (Constitution Principle XI). Quality-gate
  policy experiments MUST NOT add on-screen metrics during fixation.
- **FR-005**: Calibration pass or fail MUST be reported only after the
  session ends.

**Feature consistency**

- **FR-006**: The gaze representation used to teach the mapping and the
  representation used for live prediction MUST be clearly defined and
  consistent.
- **FR-007**: Repeated gaze at the same keyboard location MUST produce
  sufficiently repeatable features for mapping; gaze at different keyboard
  regions MUST remain distinguishable. Feature 004 operationalizes this
  with existing **held-out inside-key** and **focus-stability** scores — not
  a new feature-space metrics framework.
- **FR-008**: Left-eye and right-eye signals MUST have clear, consistent
  semantics during calibration and during live prediction.

**Calibration / runtime synchronization**

- **FR-009**: The mapper MUST receive compatible data during training and
  during live prediction.
- **FR-010**: Any difference in smoothing, normalization, averaging, signal
  order, missing-value handling, or left/right eye handling MUST be
  intentional and justified by mapping-accuracy evidence. Unjustified
  differences MUST be treated as defects.
- **FR-011**: Missing or invalid eye signals MUST follow the same acceptance
  policy in calibration and in live prediction.

**Geometry consistency**

- **FR-012**: Calibration targets, mapper teaching positions, visible key
  centers, live mapped gaze coordinates, and key hit regions MUST refer to
  the same coordinate geometry. Calibration targets are **spatial screen
  coordinates**, not keyboard characters: a target MAY coincide with a key
  center, but that coincidence does not make the target a character, key ID,
  or row label.
- **FR-013**: System MUST verify that geometry remains consistent across
  fullscreen calibration, restored top-half keyboard, screen vs window
  coordinates, resize/reposition (**when a supported user-facing path
  exists**), screen scaling, and the current Feature 003 keyboard layout.
  If user-driven resize/reposition/scaling is **not** a supported product
  path, that fact MUST be recorded and those cases MUST NOT be treated as
  open mapping defects.
- **FR-014**: If geometry becomes stale or mismatched after a **supported**
  layout change, the system MUST NOT continue mapping as if the old layout
  were still current.
- **FR-030**: Key labels, key IDs, and row semantics MUST NOT affect mapper
  fitting unless that use is explicitly justified. Fitting teaches
  gaze-representation → spatial position `(features → x, y)`. A unit or
  contract test MUST pin that the fitter does not take `key_id`, label, or
  row semantics as regression inputs.
- **FR-031**: Placement and coverage of calibration points MUST themselves
  be investigated. The current key-centered layout MUST NOT be assumed
  optimal. Planning MAY consider points distributed across the keyboard
  region, beyond its edges, or across a larger / full-screen region,
  depending on the actual prediction domain — without this spec freezing a
  count or layout. More than one layout candidate MAY be tested if needed;
  each candidate is its **own** experiment. A failed or inconclusive first
  candidate MUST NOT be taken as proof that the current key-centered layout
  is optimal.
- **FR-032**: The **calibration domain** (where targets are placed) MUST be
  distinguished from the **required prediction domain** (where accurate gaze
  prediction is actually needed). Target placement MUST be chosen according
  to the required prediction domain, not by treating key characters as the
  training set.

**Mapping accuracy**

- **FR-015**: Feature 004 MUST start from the **existing simple mapping
  approach** already used in the product baseline. It MUST improve that
  pipeline (data quality, consistency, geometry, then mapping behavior)
  before introducing additional mapping complexity.
- **FR-016**: Broad mapper comparisons or multiple competing mapping models
  MUST NOT be the starting work of this feature.
- **FR-017**: Changes to mapping parameters or extra correction layers MUST
  be considered only after calibration data quality, training/live
  synchronization, geometry, and calibration coverage have been
  investigated.
- **FR-018**: Downstream typing (dwell, OS input, predictive text) MUST
  consume mapped gaze only and MUST NOT be changed to compensate for
  mapping error, unless a confirmed synchronization bug in those stages
  directly causes incorrect gaze-to-key selection.
- **FR-019**: Internal fit-quality numbers MAY supplement diagnosis but MUST
  NOT be the sole acceptance criteria for mapping (Constitution Principle II).
- **FR-033**: Mapping evaluation and planning MUST consider error relative
  to actual key dimensions and boundaries, not pixel distance to a point
  alone. Pixel error MAY be reported; it is not sufficient by itself to
  declare practical typing success.
- **FR-034**: **Mapped-key (focus) accuracy** MUST be distinguished from
  **dwell activation accuracy**. Mapped gaze on the wrong key is already a
  mapping failure, even if dwell never activates a key.
- **FR-035**: If currently identified issues are corrected or ruled out and
  accuracy is still insufficient, Feature 004 MUST continue diagnosis into
  calibration coverage, mapping assumptions, feature sufficiency, and/or
  the current mapper itself. The first investigation list is not the end of
  the feature.

**Evaluation vs product**

- **FR-020**: Developer mapping evaluation is **infrastructure only**. It MAY
  be used during development to measure whether a change improved accuracy.
- **FR-021**: Mapping evaluation MUST NOT participate in calibration
  decisions, mapper fitting, runtime corrections, key selection, dwell
  behavior, enabling or disabling typing, or normal product execution.
- **FR-022**: The user-facing product MUST NOT depend on the evaluation
  running or on evaluation results.
- **FR-023**: Mapping evaluation MUST measure intended **mapped-key (focus)**
  accuracy on the usable keyboard surface. The evaluated set MUST include:
  (a) calibration-target locations (repeatability), (b) **held-out letter
  keys** whose centers were not those locations, and (c) **editing/control
  keys** in the required prediction domain (Shift, Backspace, Space, Enter,
  Calibrate — Space may sit in slice (a) when it is a calibration
  coordinate). Feature 003 **suggestion / prediction-bar** keys remain
  product gaze targets but are **not** a 004 mapped-key acceptance surface
  (SC-010 preservation only; they MUST NOT be used to judge mapping).
  Dwell activation MAY be reported separately; it MUST NOT be the only
  mapping metric.
- **FR-024**: Each calibration and mapping-evaluation run MUST produce a
  simple pass/fail summary with primary mapping metrics (Constitution
  Principles VII and X). Normal product use MUST keep terminal output
  minimal; optional verbose output is for investigation only.
- **FR-028**: Before the first accuracy-related product/mapping code change,
  Feature 004 MUST capture **two** fresh current-state baseline sessions
  (same evaluation method later experiments will use) so every later
  experiment can be compared against a known reference **and** session
  variability is visible. A later 3-session protocol on the kept stack
  (SC-004) does not replace these two baselines.
- **FR-029**: Developer evaluation MUST remain a trustworthy measurement
  tool: it SHOULD use the same mapper, the same geometry, and the same
  key-hit behavior as the real runtime as closely as possible. Differences
  (for example averaging many frames vs per-frame product focus) MUST be
  documented so they cannot be mistaken for product accuracy.

**Development discipline**

- **FR-025**: Accuracy work MUST follow observe → diagnose → change one
  logical area → measure again. Multiple accuracy-related changes MUST NOT
  be combined in one experimental iteration.
- **FR-026**: Each experimental change MUST have a documented failure
  pattern, a clear hypothesis, one focused modification, a repeatable
  developer-side evaluation against the two-session baseline (or last kept
  state), and a recorded outcome of **keep**, **revert**, or
  **inconclusive**. Unproven changes MUST NOT be stacked under later
  experiments. Each accepted **keep** MUST have a **Git checkpoint**
  (commit of that proven state) so a later revert can restore it.

**Product preservation**

- **FR-027**: Feature 004 MUST preserve Feature 003 product behavior:
  predictive text, suggestion selection, dwell-based typing, OS input
  integration, and current keyboard UX, except where a confirmed
  synchronization bug in those areas directly causes wrong gaze-to-key
  selection. Preservation of suggestions MUST NOT be used to hide mapping
  error during mapping validation (see SC-006).

### Key Entities

- **Calibration target**: A **spatial screen coordinate** the user is asked
  to look at while the system learns gaze-to-position. It is not a keyboard
  character. It MAY be placed on a key center, off a key, near an edge, or
  elsewhere in the chosen calibration domain.
- **Calibration domain**: The screen region in which calibration targets are
  placed.
- **Required prediction domain**: Feature 003 letter keys plus editing /
  control keys (Shift, Backspace, Space, Enter, Calibrate). Suggestion /
  prediction-bar keys are **outside** this 004 acceptance surface
  (preservation only). The calibration domain may differ.
- **Current-state baseline**: **Two** mapping evaluation sessions (A and B)
  recorded on the unchanged Feature 003 mapping path **before** the first
  accuracy-related product/mapping change. Later experiments compare to
  both. Distinct from the 3-session final repeatability protocol on the
  kept stack.
- **Calibration observation**: One moment of gaze signals captured while a
  target is shown, including whether it was accepted as stable.
- **Target sample**: The combined representation of accepted observations for
  one target, used to teach mapping (gaze representation → that target’s
  spatial position).
- **Gaze representation**: The defined set of eye signals (including left and
  right) used both to teach mapping and to predict live position.
- **Mapped gaze**: The predicted keyboard/screen position produced from live
  gaze representation.
- **Mapped key (focus)**: The keyboard control identified from mapped gaze
  via key-hit geometry, before dwell.
- **Key hit**: The keyboard control selected from mapped gaze using the
  visible key’s hit region (same geometry as mapped-key focus).
- **Mapping evaluation run**: A developer-only measurement of mapped-key
  accuracy, error (including vs key size), row correctness, and
  repeatability. Not part of product execution.

## Success Criteria *(mandatory)*

The numbers in SC-001–SC-004 are the **historical independent mapping floors**
from the calibration/mapping foundation. They are an **initial / reference
bar** for comparing against the fresh baseline — **not** automatically the
final definition of practical typing success for Feature 004.

Final Feature 004 acceptance MUST be resolved later (in planning, after
baseline and experiments) from:

- the two-session current-state baseline (session variability visible)
- held-out letter **and** editing/control mapped-key accuracy
- error relative to actual key dimensions and boundaries
- the **3-session** final repeatability protocol (SC-004) on the kept stack
- real typing: `hadar` compared to baseline wrong-focus, then 2–3 additional
  short words not used during development, suggestions unused

All of these are measured under the **product condition** (chin/head
support, Clarifications 2026-08-20). Free-head runs MUST NOT be substituted
for a product-condition result.

Developer evaluation may be used to measure these outcomes; it remains
outside the product runtime.

### Measurable Outcomes

- **SC-001**: **Mapped-key accuracy (primary, reference floor)** — On a
  single mapping evaluation after calibration, mapped gaze identifies the
  **intended key** for **≥ 67%** of evaluated locations. The evaluated set
  MUST include calibration-target locations, held-out **letter** keys, and
  **editing/control** keys in the required prediction domain (FR-023).
  Suggestion / prediction-bar keys are excluded from this percentage.
  Stretch (non-gating): ≥ 80%. This 67% figure is a **reference floor for
  early comparison**, not the automatic final acceptance bar.
- **SC-002**: **Spatial error** — Median distance from mapped gaze to the
  intended key center is **≤ 55 pixels** on that same evaluation set as a
  **reference floor**. Planning MUST also consider error relative to actual
  key dimensions and boundaries (whether mapped gaze falls inside the
  intended key). Pixel error alone MUST NOT be treated as sufficient for
  practical typing success.
- **SC-003**: **Row accuracy** — **≥ 80%** of evaluated locations map to the
  correct keyboard row (reference floor).
- **SC-004**: **Session repeatability (final protocol)** — After the kept
  mapping stack is chosen, run **3** fresh calibration + evaluation
  sessions on the same setup, **all with the chin/head support** (product
  condition), and not the two current-state baselines. Every
  session meets a **≥ 53%** mapped-key reference floor, and the spread
  between best and worst session is **≤ 20 percentage points**. This is
  the final repeatability check. It does **not** replace the mandatory
  two-session baseline before the first accuracy-related code change
  (SC-011).
- **SC-005**: **Generalization, not only repeatability** — Accuracy on
  locations that were **not** calibration targets is reported separately
  from accuracy on calibration locations. A run MUST NOT be treated as a
  mapping success if it only repeats calibration locations well and fails
  on other usable keys.
- **SC-006**: **Practical short-word typing** — After a passing calibration,
  word checks run on the product typing path **with suggestions unused**.
  **During development**, the comparison word is `hadar`: record which
  letters had wrong **focus** (vs dwell) and compare that set/count to the
  same word on baseline A and B. Improvement is fewer wrong-focus letters
  than the worse of the two baselines (ties vs both are allowed only with
  notes); more wrong-focus letters than both baselines is a mapping
  regression. **At final accept**, repeat `hadar` and add **2–3 additional
  short words not used during development**, covering different rows /
  keyboard regions, still with suggestions unused. Frequent wrong-key
  **focus** on those words is a mapping failure even if calibration-location
  evaluation looks acceptable.
- **SC-007**: **Run clarity** — After each calibration and mapping
  evaluation, a tester can state pass/fail and the primary metrics without
  reading verbose logs or many files.
- **SC-008**: **Product independence** — Normal product typing works with
  evaluation infrastructure disabled or unused; mapping, key selection, and
  dwell do not require an evaluation run.
- **SC-009**: **Calibration UX** — No on-screen text distractions beyond the
  target and optional progress during active fixation.
- **SC-010**: **Feature 003 preserved** — Predictive text, suggestion
  selection, dwell typing, OS input, and current keyboard UX still work
  after mapping-accuracy work, except for fixes of confirmed
  gaze-to-key synchronization bugs. Predictive text remaining available
  does not relax SC-006 (suggestions stay off during mapping word checks).
- **SC-011**: **Fresh two-session baseline** — Two current-state mapping
  evaluations (A and B) exist from the unchanged product mapping path
  **before** the first accuracy-related product/mapping code change.
  Later experiments compare to **both**. Session spread between A and B is
  diagnostic noise, not a reason to skip either session or the later
  3-session final protocol.

## MVP Scope *(mandatory for GazeKey)*

**In scope**:

- Active path: tracking → gaze features → calibration collection → mapping
  → live prediction → keyboard coordinates → key hit detection
- Calibration data quality (stability vs the mapping representation; coherent
  target samples)
- Feature consistency, including left/right eye semantics
- Training vs live prediction synchronization
- Keyboard geometry consistency after Feature 003 layout, including
  fullscreen calibration vs restored typing keyboard
- Investigation of calibration-point **placement and coverage**, including
  distinguishing calibration domain from required prediction domain (layout
  choice is a planning decision; not frozen here)
- Improving the **existing simple mapping approach** after data quality,
  synchronization, geometry, and coverage are investigated
- Developer-only mapping evaluation that is a trustworthy measurement of
  the runtime mapper, geometry, and key-hit behavior, including
  non-calibration locations and mapped-key vs dwell distinction, without
  participating in product runtime
- A fresh current-state baseline before the first accuracy-related code
  change
- Simple run summaries for calibration and mapping evaluation
- Targeted cleanup only where it removes confusion on the active
  calibration/mapping path
- Disciplined one-area accuracy iterations with keep / revert / inconclusive
- Continued diagnosis if first confirmed fixes are not enough

**Out of scope**:

- Redesigning predictive-text ranking, dictionaries, or suggestion UX
- Changing dwell duration as an accuracy substitute
- Changing the OS input adapter
- Visual styling unrelated to geometry correctness
- Language support / Hebrew-English switching
- Personalization, saved profiles, multi-monitor support
- Unrelated architecture or full-repository cleanup
- Broad mapper bake-offs or new competing mapping models as the first step
- Prescribing in this spec a calibration-point count, smoothing value,
  regularization value, mapper replacement, or extra correction layer
  (those are later planning decisions, evidence-based)
- Making developer evaluation part of calibration, fitting, or live typing
- Treating historical 67% / 55 px figures as automatically sufficient for
  practical typing success

## Investigation Areas *(not predetermined fixes)*

A code review of the Feature 003 baseline identified possible sources of
mapping error. Feature 004 MUST investigate them systematically. They are
**hypotheses**, not a required patch list and not the complete search space.
Planning and implementation MUST confirm or reject each with evidence before
changing that area.

If these items are corrected or **ruled out** and mapped-key accuracy is
still insufficient, Feature 004 MUST **continue diagnosis** — including
calibration coverage, mapping assumptions, whether the current gaze
representation is sufficient, and whether the current mapper itself is the
limit. Stopping after the first list is not allowed while practical typing
still fails.

Initial hypotheses (not a fixed patch list):

1. Whether calibration stability checks use the same full gaze representation
   the mapper uses
2. Whether left and right eye signals are handled with consistent assumptions
3. Whether accepted calibration observations are combined in a way that
   breaks relationships among signals from the same moment
4. Whether calibration-time and live prediction preparation (smoothing,
   averaging, and related steps) are fully aligned
5. Whether calibration quality checks still match the current target layout
   without treating targets as keyboard characters
6. Whether keyboard geometry and coordinates stayed consistent after Feature
   003 UI/layout changes
7. Whether calibration-point placement and coverage match the required
   prediction domain (current key-centered layout is a starting reference,
   not assumed optimal)
8. Whether calibration **quality / pass-fail gates** that currently warn
   rather than block still allow mappings that fail held-out mapped-key or
   practical typing (warnings-only LOOCV, train-pixel, and region checks
   are hypotheses — not a mandate to harden them)
9. Whether **clip/clamp** of predictions outside the required prediction
   domain pins gaze onto edge keys and hides extrapolation error
10. Whether **spatial row/column metadata** used by quality checks is
    correct for the current target set — especially Space and other
    non-letter controls grouped with letter rows/columns
11. Whether the current mapping configuration needs change — **only after**
    calibration data quality, geometry, and coverage are verified —
    including, if that stage is reached, the existing **auto-alpha
    selection rule** as a mapper-diagnosis item (not a predetermined retune)

## Assumptions

- **Product baseline**: Feature 003 (predictive text and simplified keyboard)
  is the current user-facing product. 004 improves mapping underneath it.
- **Starting mapping approach**: The current simple gaze-to-key mapping
  already in the product is the starting point, not a replacement program.
- **Calibration targets are spatial**: Teaching data is gaze representation
  paired with screen coordinates. Current product placement may put some
  targets on key centers; that is a layout choice, not a definition of a
  target as a character.
- **Calibration layout is open**: Point count and placement (across the
  keyboard, beyond edges, or a larger/full-screen region) are planning
  decisions driven by the required prediction domain. This spec does not
  freeze the current key-centered product layout.
- **Calibration domain vs prediction domain**: Targets are placed to support
  accurate prediction where typing actually needs it; the two regions are
  not assumed identical.
- **Single user, single monitor**: One primary user, consistent seating,
  lighting, and one display; glasses and small setup variation are tolerated.
- **Head stabilization is part of the setup**: The user sits with the
  chin/head support in place. Accuracy work targets that condition
  (Clarifications 2026-08-20). Mapping MUST NOT require head motion to
  produce a usable vertical or horizontal signal.
- **Per-session calibration**: The user calibrates at launch (existing
  product behavior); this feature does not add saved-profile mapping.
- **Numeric floors are reference only**: SC-001–SC-004 reuse historical
  independent mapping floors (67% mapped-key, 55 px median, 80% row,
  3-session repeatability) as an **initial comparison bar** against the
  two-session baseline. They are **not** automatically Feature 004’s final
  practical-typing acceptance. Final acceptance uses those floors plus
  held-out mapped-key, editing/control slice, key geometry, 3-session
  protocol on the kept stack, `hadar` vs baseline wrong-focus, and hold-out
  words (SC-005, SC-006, SC-011).
- **Evaluation set composition**: Planning names default slices (held-out
  letters; editing/control keys; calibration locations). Suggestion /
  prediction-bar keys are out of 004 mapped-key accept. Exact counts are
  not frozen; slices are recomputed if calibration layout changes.
- **KEEP Git checkpoints**: Each accepted keep is a Git commit of that
  state. Revert restores the last keep commit.
- **Layout candidates**: One candidate per experiment; further candidates
  allowed after revert/inconclusive; first failure does not prove
  `keyboard15` optimal.
- **Dwell and suggestions stay as-is**: Existing dwell timing and predictive
  text remain unless a confirmed synchronization bug in those stages causes
  the wrong key to be selected. Mapping word checks still run with
  suggestions unused.
- **Audit findings are not a backlog of mandatory patches**: Each
  investigation area may result in a fix, a justified keep, or a later
  mapping-parameter experiment. If that set is exhausted and accuracy is
  still insufficient, diagnosis continues.
- **Unproven changes are not stacked**: An experiment that is inconclusive
  or unproven is reverted (or otherwise not carried forward) before the next
  accuracy change.
- **Platform**: Windows desktop remains the primary environment.
- **Camera and tracking**: Existing webcam tracking remains the input;
  this feature does not replace the camera or face-tracking stack unless
  investigation proves it is the mapping-quality bottleneck and a mapping
  evaluation justifies a narrowly scoped change.
