<!--
Sync Impact Report
Version change: 1.1.0 → 1.2.0
Modified principles:
  - VII Debuggability and Reproducibility → lighter run-clarity focus (no artifact clutter)
  - IX Active Codebase Cleanup → targeted first-MVP cleanup, not full rewrite
  - X Controlled Logging → simple readable logs; no debug framework or many modes
Added sections: (none)
Removed sections: (none)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ updated
  - .specify/templates/spec-template.md ✅ updated
  - .specify/templates/tasks-template.md ✅ updated
Follow-up TODOs: None
-->

# GazeKey Constitution

## Project Context

GazeKey is a webcam-based virtual keyboard controlled by eye gaze. The long-term
product vision includes webcam eye tracking, a virtual keyboard overlay,
calibration, gaze-to-key mapping, dwell-time selection, OS-level typing
integration, Hebrew/English support, and predictive text.

The current engineering priority is the **core MVP**: accurate calibration and
accurate gaze-to-key mapping on the virtual keyboard. The repository already
contains substantial implementation (PySide6 UI, OpenCV capture, MediaPipe
tracking, calibration v2, mapper experiments, dwell selection, logging, and
tests). The active blocker is **reliability**: calibration and gaze-to-key
mapping are not accurate or stable enough. Historical 15-key benchmark sessions
achieved only 20%–60% accuracy, and quality gates such as LOOCV/RMS do not
reliably predict real key-hit accuracy.

This constitution governs the Spec Kit–driven redesign phase. Instrumentation,
logging, and cleanup MUST stay **light and practical** for this first MVP —
enough to judge progress, not enough to become a project of their own.

## Core Principles

### I. Accuracy First (NON-NEGOTIABLE)

No feature is considered useful until gaze-to-key mapping is reliable.
Dwell-time tuning, predictive text, language switching, OS injection, and
accessibility polish MUST NOT be prioritized before mapping accuracy is
measurable and acceptable.

**Rationale**: Prior work layered runtime compensations atop an unstable mapping
foundation, increasing complexity without solving the core failure mode.

### II. Measurable Progress Only (NON-NEGOTIABLE)

Every calibration or mapping change MUST be evaluated using objective metrics:

- **key-hit accuracy** (primary acceptance metric)
- **pixel error**
- **row accuracy**
- **repeatability across sessions**

Subjective feel, anecdotal demos, and internal-only model metrics (e.g., LOOCV,
RMS) MUST NOT be the sole acceptance criteria. They may supplement but not
replace end-to-end key-hit benchmarks.

**Rationale**: Quality gates that do not correlate with real typing accuracy have
masked regressions and blocked principled iteration.

### III. Simple Pipeline Before Layered Compensation

Prefer a clear, testable pipeline:

`tracking → feature extraction → calibration → mapping → preview → benchmark`

Correction layers, fallback models, heuristic patches, and per-region
compensations MUST NOT be added unless a controlled benchmark demonstrates
improved key-hit accuracy over the simpler baseline.

**Rationale**: The current runtime path is monolithic and layered; additional
complexity must earn its place with evidence.

### IV. Spec Before Code (NON-NEGOTIABLE)

No implementation work MUST begin before these artifacts exist and are approved
for the feature:

1. Feature specification (`spec.md`)
2. Clarification answers (resolved `NEEDS CLARIFICATION` items)
3. Technical plan (`plan.md`)
4. Task list (`tasks.md`)

**Rationale**: Restarts without gated design reproduce accidental scope creep
and untestable changes.

### V. MVP Scope Control

The current MVP INCLUDES only what is required for reliable calibration and
gaze-to-key mapping on the in-app virtual keyboard, plus the minimum UI and
instrumentation needed to measure them.

The current MVP EXCLUDES until calibration and mapping are stable:

- predictive text
- Hebrew/English switching
- OS-level typing injection
- personalization
- multi-monitor support
- advanced accessibility polish

Excluded items MAY return only after mapping accuracy meets success thresholds
defined in the active feature spec.

**Rationale**: Scope discipline keeps effort on the reliability blocker.

### VI. Testable Architecture

Code MUST be organized so tracking, calibration, mapping, evaluation, and UI
feedback can be tested independently. Monolithic modules that mix UI,
calibration, mapping, runtime selection, and debug behavior MUST be split or
bounded behind clear interfaces as part of approved redesign tasks.

**Rationale**: Large mixed modules and tangled calibration/mapping paths impede
isolated diagnosis.

### VII. Run Clarity (Debuggability Without Clutter)

Each calibration and benchmark run MUST make it easy to answer: **what happened,
and did calibration/mapping pass or fail?**

Acceptance requires a simple, readable run summary — for example, concise
terminal output plus one lightweight persisted record per run (such as an
existing CSV summary or a short log file). The summary MUST include pass/fail,
primary accuracy metrics, and a brief failure reason when applicable.

The MVP does NOT require a diagnostics platform, dashboards, or many parallel
artifact types. Add detail only when a benchmark shows it improves understanding
of accuracy — not preemptively.

**Rationale**: Progress depends on knowing whether a change helped. That does not
require a heavy debug system or file sprawl.

### VIII. Documentation Hierarchy

The original project specification (PDF) remains the **long-term product
vision**. For the next implementation phase, Spec Kit documents under `specs/`
and `.specify/` are the **source of truth** for scope, design, and acceptance.

When the PDF and Spec Kit conflict on MVP scope, Spec Kit and this constitution
prevail. When implementing post-MVP features, reconcile with the PDF explicitly
in a new spec.

### IX. Targeted Codebase Cleanup

The first MVP MUST begin clarifying the **active path** — carefully, not as a
full rewrite. The goal is one unambiguous calibration/mapping flow, not a
repository-wide purge.

Code MUST be distinguishable as:

- **active MVP code**
- **reusable infrastructure**
- **deprecated legacy code**
- **experimental code**
- **debug-only tools**
- **future product features**

First-MVP cleanup SHOULD address only what causes confusion today, such as:

- multiple active calibration/mapping paths
- placeholder features in the active user flow
- experimental or legacy code that looks like the supported path

Broader archival or deletion MAY wait for later phases. No file deletion or
archival MUST occur without a dedicated, approved task in `tasks.md`.

**Rationale**: The repository mixes v1/v2 paths, experiments, and placeholder UI.
Targeted cleanup in the first MVP reduces wrong-path risk without blocking
accuracy work behind a large refactor.

### X. Simple Logging

Logs MUST be **readable and purposeful**: what ran, whether calibration and
mapping passed or failed, and enough context to investigate a bad run.

Normal use MUST keep terminal output short — essential status only, not
frame-by-frame or per-sample spam. When deeper detail is needed, use a single
**verbose or debug option** rather than building a multi-mode logging framework.

Persist outcomes and key metrics in the run summary (Principle VII). Do not add
logging infrastructure, dashboards, or extra artifact types unless a spec proves
they are needed for the current MVP.

**Rationale**: Useful logs support iteration; complicated logging systems consume
time that should go to calibration and mapping accuracy.

### XI. Minimal Visual Distraction During Calibration (NON-NEGOTIABLE)

Calibration UI MUST keep the user focused on the target point. Long
explanations, detailed metrics, sample counts, debug text, and noisy on-screen
feedback MUST NOT appear on the calibration screen while the user is expected to
fixate on a target dot.

Permitted on-screen calibration feedback:

- target dot
- simple progress indicator (if needed)
- final pass/fail result only after calibration ends (if required)

Detailed status, quality metrics, sample counts, and failure reasons MUST go to
the run log or verbose output — not displayed as text during target fixation.

**Rationale**: Reading on-screen text during calibration shifts gaze away from
the target and corrupts collected samples.

## Development Workflow

All feature work follows the Spec Kit sequence:

1. **Constitution** — principles ratified (this document)
2. **Specify** — `spec.md` with prioritized user stories and measurable success criteria
3. **Clarify** — open questions resolved in spec
4. **Plan** — `plan.md` with constitution check and technical design
5. **Tasks** — `tasks.md` with dependency-ordered work
6. **Implement** — code changes only after approval of the above
7. **Analyze** — cross-artifact consistency before merge

Plans MUST include a **Constitution Check** gate and document any justified
violations in Complexity Tracking.

Benchmark and evaluation tasks MUST appear in `tasks.md` for any change touching
calibration or mapping. Each benchmark MUST record pass/fail and primary metrics
in a simple run summary.

First-MVP `tasks.md` SHOULD include targeted cleanup tasks where active,
legacy, experimental, or placeholder code would confuse the supported path.
Each deletion or archive operation MUST be its own approved task.

## Governance

- This constitution supersedes informal conventions, README summaries, and ad-hoc
  tuning practices for the Spec Kit redesign phase.
- Amendments require: updated `constitution.md`, version bump per semver,
  documented rationale in the Sync Impact Report comment, and review approval
  before dependent specs/plans are updated.
- **Version policy**: MAJOR = principle removal or redefinition; MINOR = new
  principle or material expansion; PATCH = clarifications only.
- **Compliance**: Every `plan.md` Constitution Check, every change touching
  calibration/mapping, and every `/speckit-analyze` run MUST verify adherence
  to principles I–XI.
- **Runtime guidance**: `docs/current-status.md` for repository evidence; active
  feature specs under `specs/` for scoped work.

**Version**: 1.2.0 | **Ratified**: 2026-06-09 | **Last Amended**: 2026-06-09
