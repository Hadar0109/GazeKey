# Feature Specification: Calibration & Gaze Mapping MVP

**Feature Branch**: `001-calibration-mapping-mvp`

**Created**: 2026-06-09

**Status**: Draft (revised)

**Input**: First practical MVP for the GazeKey redesign — a simple, reliable
calibration and gaze-to-key mapping flow that answers whether the user's gaze
maps to the correct key on the virtual keyboard.

**Guidance**: GazeKey Constitution v1.2.0 (binding). Repository context:
`docs/current-status.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete a Distraction-Free Calibration (Priority: P1)

A user launches GazeKey, positions themselves in front of the webcam, and
completes a calibration session by looking at each **calibration target** shown
on the virtual keyboard. Calibration teaches the system how gaze features map to
screen positions — it is separate from later accuracy testing.

During fixation, the screen shows only the dot and a simple progress indicator
— no instructions, metrics, or debug text that would pull their gaze away. When
calibration finishes, they see a clear pass or fail result.

**Why this priority**: Without trustworthy calibration data, no mapping or
benchmark can be meaningful. This is the foundation of the entire MVP.

**Independent Test**: Run a full calibration session and verify that samples
are collected for all calibration targets, fixation UI stays minimal, and a
pass/fail outcome is reported with a readable run summary.

**Acceptance Scenarios**:

1. **Given** the app has started and the camera is working, **When** the user
   begins calibration, **Then** each calibration target appears as a fixation
   dot at a defined screen position on or aligned to the keyboard, with no
   distracting on-screen text during fixation.
2. **Given** the user completes all calibration targets, **When** the session
   ends, **Then** the system reports calibration pass or fail and records what
   happened in a simple run summary (outcome and enough context to understand
   failure if applicable).
3. **Given** calibration fails quality checks, **When** the session ends,
   **Then** the user sees fail status after calibration ends (not during
   fixation) and can start a new calibration attempt.

---

### User Story 2 - Preview Gaze on the Keyboard (Priority: P2)

After successful calibration, the user enters a **read-only preview** mode: a
gaze indicator shows where their eyes are mapped on screen. Preview displays
position only — it does not select keys, activate keys, update the text buffer,
or trigger typing behavior of any kind.

They can move their gaze across keys and visually confirm whether the indicator
lands on the key they are looking at.

**Why this priority**: Preview is the fastest way to judge mapping quality
before running a formal benchmark. It answers the core question: "Is my gaze
on the right key?"

**Independent Test**: After calibration, look at known keys and observe whether
the gaze indicator tracks the intended key with no key activation, dwell
selection, or text changes.

**Acceptance Scenarios**:

1. **Given** calibration has passed, **When** the user looks at a key on the
   virtual keyboard, **Then** a read-only gaze preview indicator appears at the
   mapped screen position.
2. **Given** preview mode is active, **When** the user holds gaze on a key,
   **Then** no key is selected, highlighted as active, or typed into the text
   buffer.
3. **Given** calibration has not passed or was not completed, **When** the user
   expects preview, **Then** preview is not offered until a valid mapping
   exists.

---

### User Story 3 - Validate Mapping with a Key-Accuracy Benchmark (Priority: P3)

A user (or tester) runs a structured **benchmark** after calibration. The
benchmark uses its own set of **test keys** — chosen to validate mapping
quality, not necessarily the same points used during calibration. For each test
key, the user looks at the key and the system records whether the mapped gaze
position corresponds to the correct key.

The run ends with a simple pass or fail against defined accuracy targets and a
readable summary.

**Why this priority**: Subjective preview alone is insufficient. The MVP must
prove mapping accuracy with an objective, repeatable test. Benchmark keys and
calibration targets serve different purposes and may differ in count and
placement.

**Independent Test**: Complete calibration, run the benchmark on its defined
test keys, and verify the summary reports key-hit accuracy, row accuracy,
gaze-to-target error, and overall pass/fail.

**Acceptance Scenarios**:

1. **Given** calibration has passed, **When** the user starts the benchmark,
   **Then** the system prompts gaze at each benchmark test key in sequence and
   records whether the mapped position hits the correct key.
2. **Given** a benchmark completes, **When** results are available, **Then** a
   run summary states pass or fail, key-hit accuracy, row accuracy, and
   median gaze-to-target error.
3. **Given** a benchmark fails, **When** the user reviews the outcome, **Then**
   the summary indicates failure clearly enough to decide whether to
   recalibrate or adjust setup.

---

### User Story 4 - Know What Happened in a Run (Priority: P4)

After calibration or benchmark, the user or developer can understand what
happened without verbose terminal spam or hunting through many files. Each run
produces a **simple, lightweight summary** — readable pass/fail, primary
metrics, and a brief failure reason when needed.

**Why this priority**: Iteration depends on knowing whether changes helped.
Run clarity should support progress, not create clutter.

**Independent Test**: Complete one calibration and one benchmark; confirm
normal use stays quiet and each run leaves enough recorded detail to understand
pass/fail and primary metrics.

**Acceptance Scenarios**:

1. **Given** a normal app session, **When** calibration and benchmark run,
   **Then** terminal output shows only essential status (no per-frame spam).
2. **Given** any calibration or benchmark completes, **When** the run ends,
   **Then** the outcome and primary metrics are available in a simple,
   human-readable form (terminal and/or a lightweight saved record — format
   chosen during planning, not prescribed here).
3. **Given** a developer needs more detail, **When** verbose or debug mode is
   enabled, **Then** additional diagnostic output is available without changing
   the default minimal experience.

---

### Edge Cases

- **Camera unavailable or face not detected**: Calibration cannot start or
  pauses with a clear message after the session ends or before fixation begins
  — not as text on the fixation dot.
- **User moves head excessively during a target**: That target's samples are
  rejected or the session fails; reason appears in run summary, not on the
  fixation screen.
- **Blinking or brief tracking loss**: System tolerates short gaps without
  corrupting the whole session; prolonged loss fails the current target or
  session with recoverable retry.
- **Calibration abandoned mid-session**: No partial mapping is used for preview
  or benchmark; user must complete or restart calibration.
- **Benchmark started without passing calibration**: Benchmark is blocked with
  a clear message.
- **Benchmark keys overlap calibration targets**: Allowed, but benchmark and
  calibration remain logically separate; overlap is a planning choice, not a
  requirement.
- **Repeat runs in one sitting**: Each calibration and benchmark should be
  distinguishable so sessions can be compared.
- **Legacy or experimental code paths**: Only the designated MVP
  calibration/mapping path is reachable from the normal user flow.
- **Preview confused with typing mode**: Preview MUST remain read-only even if
  dwell or typing features exist elsewhere in the codebase.

## Requirements *(mandatory)*

### Functional Requirements

**Calibration (learning the mapping)**

- **FR-001**: System MUST provide **one active calibration path** in the normal
  user flow at runtime; legacy or experimental calibration flows MUST NOT be
  reachable from that flow.
- **FR-002**: System MUST collect gaze samples at a defined set of **calibration
  targets** aligned to known screen positions on or near the virtual keyboard.
  Target **count and placement are planning decisions** — not fixed in this
  spec. The repository's current 15-point keyboard-aligned layout is a starting
  reference, not a requirement; fewer, better-distributed, or differently
  placed targets MAY be chosen if planning shows they improve mapping quality.
- **FR-003**: During target fixation, the calibration screen MUST show only the
  target dot and an optional simple progress indicator (e.g., target 3 of N).
- **FR-004**: System MUST NOT display instructions, metrics, sample counts,
  quality scores, or debug text on the calibration screen while the user is
  expected to fixate on a target.
- **FR-005**: System MUST report calibration pass or fail only after the
  calibration session ends.
- **FR-006**: System MUST require calibration at application start before
  preview or benchmark are available (per-session calibration for this MVP).

**Gaze mapping**

- **FR-007**: At runtime the MVP MUST use **one active mapping approach** —
  not a stack of undocumented correction layers. **Which** approach becomes
  active is chosen during **planning** after evaluating candidates against
  benchmark results; this spec does not lock the model before that evaluation.
- **FR-008**: System MUST provide **read-only gaze preview** after successful
  calibration: a position indicator only. Preview MUST NOT trigger key
  selection, dwell activation, text buffer updates, or typing.
- **FR-009**: Internal model quality metrics (e.g., cross-validation error)
  MAY inform calibration pass/fail but MUST NOT be the sole acceptance criteria
  for the MVP.

**Benchmark (validating the mapping)**

- **FR-010**: System MUST provide a structured **benchmark** separate from
  calibration that tests whether mapped gaze hits the correct key for each
  **benchmark test key**. Benchmark keys are for validation; they are defined
  independently of calibration targets (may partially overlap, but serve a
  different purpose).
- **FR-011**: Benchmark test key count and placement are **planning decisions**.
  The repository's historical 15-key evaluation is a useful baseline reference;
  the plan SHOULD justify the chosen benchmark set (coverage across rows/columns,
  independence from calibration layout where possible).
- **FR-012**: Each benchmark MUST record key-hit accuracy, row accuracy, and
  median gaze-to-target error.
- **FR-013**: Benchmark MUST produce a pass/fail verdict against the success
  criteria defined in this spec.

**Run clarity & logging**

- **FR-014**: Each calibration and benchmark run MUST make pass/fail and
  primary metrics easy to understand — via concise terminal output and/or a
  lightweight saved summary. No prescribed file format, directory layout, or
  artifact count.
- **FR-015**: Normal operation MUST keep terminal output minimal; a single
  verbose or debug option MAY expose additional detail when needed.
- **FR-016**: System MUST NOT introduce a multi-mode logging framework,
  dashboards, or many parallel artifact types for the MVP.

**Architecture & targeted cleanup**

- **FR-017**: Tracking, calibration, mapping, evaluation, and UI feedback MUST
  be separable enough to test independently (bounded modules or clear
  interfaces).
- **FR-018**: MVP cleanup MUST focus **only** on simplifying the active
  calibration/mapping path — e.g., one reachable flow, placeholder features
  removed from that flow, legacy paths not mistaken for supported. It MUST NOT
  expand into a full repository cleanup or rewrite.
- **FR-019**: Any file deletion or archival MUST be a dedicated approved task;
  no undeclared removals.

**Explicitly out of scope**

- **FR-020**: System MUST NOT include predictive text, language switching,
  OS-level typing injection, personalization, multi-monitor support, or
  advanced accessibility polish in this MVP.
- **FR-021**: Dwell-based key activation and intent-scoring tuning MUST NOT be
  optimized in this MVP; read-only preview and benchmark are the primary
  validation surfaces.

### Key Entities

- **Calibration Target**: A screen position where the user fixates during
  calibration so the system can learn gaze-to-position mapping. Set defined at
  planning time.
- **Calibration Session**: One calibration run from first target through
  pass/fail; includes collected samples, outcome, and summary.
- **Gaze Mapping**: The fitted relationship from eye features to screen
  coordinates; one active mapping per successful calibration session.
- **Benchmark Test Key**: A key (or screen position) used only to **validate**
  mapping accuracy after calibration — independent from the calibration target
  set in purpose, and defined at planning time.
- **Benchmark Run**: Structured evaluation over benchmark test keys; produces
  per-key results and overall pass/fail.
- **Run Summary**: Human-readable record of what happened in a calibration or
  benchmark run — pass/fail, primary metrics, brief failure reason when needed.
  Lightweight by design; format not fixed in this spec.

### Deferred to planning and clarification

The following are intentionally **not locked** in this spec:

| Topic | Spec stance |
|-------|-------------|
| Calibration target count and placement | Planning evaluates options; current 15-point layout is reference only |
| Benchmark test key count and placement | Separate from calibration; planning defines validation set |
| Active mapping model | One at runtime; choice made after planning compares candidates |
| Run summary format | Simple and readable; no required file structure |
| Numeric success thresholds | Initial targets below; refine in `/speckit-clarify` if needed |

## Success Criteria *(mandatory)*

Historical baseline (repository evidence): archived **15-key benchmark** sessions
showed **20%–60%** key-hit accuracy, high session-to-session variance, and poor
correlation between internal quality gates and real key-hit accuracy.

The numeric targets below are **initial MVP goals** for `/speckit-clarify` and
planning. They MAY be tightened or adjusted with documented rationale before
implementation — but key-hit benchmark accuracy remains the primary gate.

### Measurable Outcomes

- **SC-001**: **Key-hit accuracy** — On a single benchmark run immediately
  after calibration, **initial target: ≥ 67% correct keys** (e.g., 10 of 15 if
  the benchmark uses 15 test keys). Stretch direction: ≥ 80%.
- **SC-002**: **Pixel error** — **Initial target: median gaze-to-target error
  ≤ 55 pixels** on the benchmark set (repository best ~47 px mean error on
  passing sessions).
- **SC-003**: **Row accuracy** — **Initial target: ≥ 80%** of benchmark test
  keys map to the correct keyboard row.
- **SC-004**: **Session repeatability** — Across **3 calibration+benchmark
  sessions** on the same setup: every session meets a **minimum floor** (initial
  target: ≥ 53% key-hit accuracy) and the spread between best and worst session
  is **≤ 20 percentage points**. Exact floor refinable in clarification.
- **SC-005**: **Run clarity** — After each calibration and benchmark, a user or
  tester can state pass/fail and primary metrics without reading verbose logs or
  many files.
- **SC-006**: **Calibration UX** — No on-screen text distractions (beyond dot
  and progress indicator) during active fixation.
- **SC-007**: **Read-only preview** — Preview never activates keys or typing;
  verified by attempting fixation on keys and confirming no selection or text
  change.

## MVP Scope *(mandatory for GazeKey)*

**In scope**:

- Webcam-based eye tracking (reuse existing pipeline)
- Virtual keyboard shell with calibration targets at defined screen positions
- One active calibration path and one active mapping approach (chosen in plan)
- Minimal calibration UI (dot + optional progress; pass/fail after session)
- Read-only gaze preview after calibration
- Separate benchmark flow to validate mapping accuracy
- Simple run summaries for calibration and benchmark
- **Targeted** cleanup of the calibration/mapping path only
- Optional verbose/debug output for developers

**Out of scope** (deferred until mapping meets success criteria):

- Predictive text and suggestion bar functionality
- Hebrew/English language switching
- OS-level typing injection
- Personalization and saved user profiles
- Multi-monitor support
- Advanced accessibility polish
- Dwell typing optimization, intent scoring, and cross-row hysteresis tuning
- Full repository cleanup or rewrite
- Diagnostics platform, dashboards, or extensive artifact sprawl

## Assumptions

- **Single user, fixed setup**: One primary user at a consistent distance,
  lighting, and monitor arrangement; glasses and minor setup variation are
  tolerated but not multi-user generalization.
- **Platform**: Windows desktop (current development environment); cross-platform
  support is not required for this MVP.
- **Camera**: Standard webcam; face visible and reasonably stable during
  calibration.
- **Keyboard layout**: Full QWERTY letter region on the existing virtual
  keyboard; calibration targets and benchmark keys should cover spread across
  rows and columns — exact sets decided in planning.
- **Calibration vs benchmark**: Calibration teaches mapping; benchmark tests it.
  They are separate concerns and may use different point sets.
- **Per-session calibration**: User calibrates at each application launch for
  this MVP; persistence across launches may be addressed in a later spec.
- **Head movement**: Small natural movement is expected; excessive head drift
  during a target invalidates that target or the session.
- **Validation priority**: Key-hit benchmark is the primary acceptance test;
  internal statistical gates supplement but do not replace it.
- **Current 15-point layout**: Present in the repository as a reference point;
  its density or placement may contribute to accuracy problems and SHOULD be
  questioned during planning rather than assumed correct.
- **Reuse**: Existing tracking, keyboard UI, calibration overlay concept, and
  benchmark infrastructure are preferred starting points; redesign simplifies the
  active path, not a from-scratch rewrite.
- **Documentation**: Spec Kit documents supersede the legacy PDF and outdated
  README for this implementation phase.
