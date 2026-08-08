<!--
Sync Impact Report
Version change: 1.2.0 → 1.3.0
Modified principles:
  - Project Context → post-mapping product stage (mapping remains foundation)
  - I Accuracy First → keep non-negotiable mapping reliability; allow later
    specified features to consume mapped gaze (dwell/typing/OS) without treating
    them as permanently out of scope; forbid downstream compensation of mapping
  - II Measurable Progress → mapping metrics remain independent; other features
    use their own acceptance criteria from their specs
  - III Simple Pipeline → sealed upstream through mapped gaze; optional
    specified downstream stages; no mapping compensations without benchmark proof
  - V MVP Scope Control → rename emphasis to Feature Scope Control: mapping
    foundation vs advanced/post-mapping features that require their own specs
  - VI Testable Architecture → include typing/OS boundaries when those features
    exist; keep calibration/mapping separable
  - VIII Documentation Hierarchy → post-mapping features reconcile via new specs
    (clarified)
Added sections: (none)
Removed sections: (none)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ updated
  - .specify/templates/spec-template.md ✅ updated
  - .specify/templates/tasks-template.md ✅ reviewed (no constitution-gate wording change required)
Follow-up TODOs: None
-->

# GazeKey Constitution

## Project Context

GazeKey is a webcam-based virtual keyboard controlled by eye gaze. The long-term
product vision includes webcam eye tracking, a virtual keyboard overlay,
calibration, gaze-to-key mapping, dwell-time selection, OS-level typing
integration, Hebrew/English support, and predictive text.

**Calibration and PCA4 gaze-to-key mapping** remain an **independently validated
foundation**. Mapped gaze is the sealed upstream product of that foundation.
Later Spec Kit features MAY consume mapped gaze to add dwell interaction,
typing, OS integration, and other product capabilities — each with its own
specification and acceptance criteria.

Downstream typing and interaction MUST NOT modify, retune, or compensate for
calibration/mapping behavior to “fix” typing. Mapping accuracy MUST continue
to be evaluated independently through its own key-hit (and related) benchmarks.
Instrumentation, logging, and cleanup MUST stay light and practical — enough to
judge progress, not a project of their own.

## Core Principles

### I. Accuracy First (NON-NEGOTIABLE)

Gaze-to-key mapping reliability remains the foundation of GazeKey. No change to
calibration or mapping is considered successful unless mapping quality is
measured with objective end-to-end metrics (Principle II).

Later-specified features (including dwell selection, typing, and OS integration)
MAY build on **mapped gaze** once specified. They MUST:

- **consume** mapped gaze as an input, and
- **NOT** alter calibration sample collection, mapper fitting, quality gates, or
  predict behavior to compensate for typing/interaction issues.

Improving typing UX MUST NOT become a reason to patch the mapper without a
mapping-focused benchmark justification (Principle III). Advanced capabilities
such as predictive text, language switching, personalization, multi-monitor
support, and accessibility polish still require their own specifications — they
are not implied by enabling dwell/OS typing.

**Rationale**: Prior work layered runtime compensations atop an unstable mapping
foundation. Downstream features must not recreate that failure mode.

### II. Measurable Progress Only (NON-NEGOTIABLE)

Every calibration or mapping change MUST be evaluated using objective metrics:

- **key-hit accuracy** (primary acceptance metric for mapping)
- **pixel error**
- **row accuracy**
- **repeatability across sessions**

Subjective feel, anecdotal demos, and internal-only model metrics (e.g., LOOCV,
RMS) MUST NOT be the sole acceptance criteria for mapping. They may supplement
but not replace end-to-end key-hit benchmarks.

Features that do not change calibration/mapping (for example dwell typing or OS
injection) MUST define measurable acceptance criteria in **their own** feature
spec. Those criteria MUST NOT replace or weaken independent mapping benchmarks.

**Rationale**: Quality gates that do not correlate with real key-hit accuracy
have masked regressions; mapping and typing progress must stay measurable and
separable.

### III. Simple Pipeline Before Layered Compensation

Prefer a clear, testable pipeline whose sealed upstream is:

`tracking → feature extraction → calibration → mapping → mapped gaze`

Specified downstream stages (for example dwell selection → key action → OS
input) MAY follow mapped gaze when an approved feature spec defines them.
Correction layers, fallback models, heuristic patches, and per-region
compensations on the **mapping** path MUST NOT be added unless a controlled
**mapping** benchmark demonstrates improved key-hit accuracy over the simpler
baseline.

**Rationale**: Additional mapping complexity must earn its place with evidence;
downstream stages must not smuggle mapping compensations.

### IV. Spec Before Code (NON-NEGOTIABLE)

No implementation work MUST begin before these artifacts exist and are approved
for the feature:

1. Feature specification (`spec.md`)
2. Clarification answers (resolved `NEEDS CLARIFICATION` items)
3. Technical plan (`plan.md`)
4. Task list (`tasks.md`)

**Rationale**: Restarts without gated design reproduce accidental scope creep
and untestable changes.

### V. Feature Scope Control

Each active feature spec defines what is in scope for that work.

The **mapping foundation** (calibration + PCA4 mapping + independent mapping
benchmark) remains mandatory infrastructure. It MUST stay isolated and
independently testable regardless of which post-mapping features are active.

Post-mapping product capabilities — including dwell interaction, typing, and OS
integration — are **not permanently forbidden**. They MAY be implemented when an
approved feature specification defines requirements, architecture boundaries,
and acceptance criteria. They MUST consume mapped gaze only and MUST NOT rewrite
the mapping foundation “for typing.”

Capabilities that remain advanced relative to core typing still require their
own specs when undertaken, including (non-exhaustively):

- predictive text
- Hebrew/English (or other) language switching
- personalization / profiles
- multi-monitor support
- advanced accessibility polish

**Rationale**: Scope discipline protects the mapping foundation while allowing
specified product stages beyond mapping-only MVP work.

### VI. Testable Architecture

Code MUST be organized so tracking, calibration, mapping, evaluation/benchmark
for mapping, UI feedback, and (when present) typing/OS boundaries can be tested
independently. Monolithic modules that mix UI, calibration, mapping, runtime
selection, and debug behavior MUST be split or bounded behind clear interfaces
as part of approved redesign tasks.

Downstream typing/interaction modules MUST NOT fold selection or OS injection
into mapper fit/predict.

**Rationale**: Tangled calibration/mapping/typing paths impede isolated
diagnosis and invite compensation layers.

### VII. Run Clarity (Debuggability Without Clutter)

Each calibration and **mapping** benchmark run MUST make it easy to answer:
**what happened, and did calibration/mapping pass or fail?**

Acceptance for mapping work requires a simple, readable run summary — for
example, concise terminal output plus one lightweight persisted record per run.
The summary MUST include pass/fail, primary accuracy metrics, and a brief
failure reason when applicable.

The project does NOT require a diagnostics platform, dashboards, or many
parallel artifact types. Add detail only when a benchmark or approved feature
spec shows it improves understanding — not preemptively.

**Rationale**: Progress depends on knowing whether a change helped without
building a heavy debug system.

### VIII. Documentation Hierarchy

The original project specification (PDF) remains the **long-term product
vision**. Spec Kit documents under `specs/` and `.specify/` are the **source of
truth** for scope, design, and acceptance for the active work.

When the PDF and Spec Kit conflict on active scope, Spec Kit and this
constitution prevail. Post-mapping features (dwell, typing, OS integration, and
later advanced capabilities) MUST be introduced through **new or updated feature
specs** that explicitly reconcile with this constitution and, where relevant,
the PDF vision.

### IX. Targeted Codebase Cleanup

Clarify the **active path** carefully — not as an unplanned full rewrite. Keep
one unambiguous calibration/mapping flow. When product packaging splits (for
example runtime product vs developer tooling), cleanup MUST be driven by an
approved feature `tasks.md` with inventory-first deletions.

Code MUST be distinguishable as:

- **active product / foundation code**
- **reusable infrastructure**
- **deprecated legacy code**
- **experimental code**
- **debug-only / developer tooling**
- **specified future product features** (implemented only under an approved spec)

Cleanup SHOULD address confusion such as multiple active calibration/mapping
paths, placeholder features in the product flow, and experimental or legacy code
that looks supported. No file deletion or archival MUST occur without a
dedicated, approved task in `tasks.md`.

**Rationale**: Targeted cleanup reduces wrong-path risk without blocking
progress behind an unbounded purge.

### X. Simple Logging

Logs MUST be **readable and purposeful**: what ran, whether calibration and
mapping passed or failed, and enough context to investigate a bad run. When
typing/OS features are active, logs MAY note essential typing/session status
without frame spam.

Normal use MUST keep terminal output short — essential status only. When deeper
detail is needed, use a single **verbose or debug option** rather than building
a multi-mode logging framework.

Persist mapping outcomes and key metrics in the mapping run summary (Principle
VII). Do not add logging infrastructure, dashboards, or extra artifact types
unless a spec proves they are needed.

**Rationale**: Useful logs support iteration; complicated logging systems consume
time that should go to product reliability.

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

Any change touching calibration or mapping MUST include mapping benchmark /
evaluation tasks in `tasks.md`, with pass/fail and primary metrics in a simple
run summary. Mapping accuracy remains evaluated **independently** of typing or
OS-integration acceptance criteria.

Post-mapping features MUST state how they consume mapped gaze and how they avoid
modifying the mapping foundation.

Each deletion or archive operation MUST be its own approved task.

## Governance

- This constitution supersedes informal conventions, README summaries, and ad-hoc
  tuning practices for Spec Kit–driven work.
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

**Version**: 1.3.0 | **Ratified**: 2026-06-09 | **Last Amended**: 2026-08-08
