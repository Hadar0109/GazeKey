<!--
Sync Impact Report
Version change: 1.3.0 → 1.4.0
Modified principles:
  - Project Context → mapping foundation is the sealed screen-space
    measurement boundary; production implementation may be replaced when
    specified and independently validated; Feature 005 GazeFollower is the
    approved production gaze-estimation/calibration implementation; PCA4 is
    historical evidence, not a permanent constitutional requirement
  - I Accuracy First → keep non-negotiable independently measured mapping
    reliability and no downstream compensation; do not permanently require
    PCA4; replacement backends must not be silently combined with the
    previous estimator
  - II Measurable Progress → keep independent mapping metrics; name
    intended-key/focus, row, pixel error, repeatability, reachability,
    latency, and practical interaction tests as applicable
  - III Simple Pipeline → sealed upstream is screen-space mapped gaze from
    the approved backend; no ad-hoc post-backend mapping corrections
  - V Feature Scope Control → mapping foundation = approved gaze backend +
    independent screen-space mapping benchmark (not PCA4-as-implementation)
  - XI Minimal Visual Distraction During Calibration → keep GazeKey-owned
    fixation UI minimal; add explicit exception for an approved upstream
    backend's official Preview/Calibration/result UI used unmodified
    (Feature 005 GazeFollower UI allowed as-is)
Added sections: (none)
Removed sections: (none)
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ updated
  - .specify/templates/spec-template.md ✅ updated
  - .specify/templates/tasks-template.md ✅ updated
Follow-up TODOs: None. Feature 004 specs/runs/tags are historical and MUST
NOT be rewritten to match this amendment. Feature 005 spec/plan/tasks keep
their planning-time constitution-check notes as historical record.
-->

# GazeKey Constitution

## Project Context

GazeKey is a webcam-based virtual keyboard controlled by eye gaze. The long-term
product vision includes webcam eye tracking, a virtual keyboard overlay,
calibration, gaze-to-key mapping, dwell-time selection, OS-level typing
integration, Hebrew/English support, and predictive text.

**Independently validated screen-space gaze mapping** remains the **sealed
measurement foundation**. Mapped gaze (screen-space point + validity) is the
sealed upstream product of that foundation. The production
gaze-estimation/calibration **implementation** MAY be replaced when a feature
specification names the backend, independently validates it, and preserves this
screen-space boundary.

For Feature 005, **official GazeFollower** is the approved production
gaze-estimation and calibration implementation. **PCA4** remains historical
implementation and evidence (including Feature 004). It is **not** a permanent
constitutional requirement that PCA4 stay the production mapping implementation.

Later Spec Kit features MAY consume mapped gaze to add dwell interaction,
typing, OS integration, and other product capabilities — each with its own
specification and acceptance criteria.

Downstream typing and interaction MUST NOT modify, retune, or compensate for
gaze estimation/mapping behavior to “fix” typing. Mapping accuracy MUST continue
to be evaluated independently through meaningful external metrics (Principle
II). Instrumentation, logging, and cleanup MUST stay light and practical —
enough to judge progress, not a project of their own.

## Core Principles

### I. Accuracy First (NON-NEGOTIABLE)

Gaze-to-key mapping reliability remains the foundation of GazeKey. No change to
calibration or mapping is considered successful unless mapping quality is
measured with objective end-to-end metrics (Principle II).

This principle protects the **measurement boundary**, not a permanently named
estimator. A different production gaze-estimation/mapping backend MAY replace
the previous one only when that replacement is specified, independently
validated, and still emits sealed screen-space mapped gaze.

Later-specified features (including dwell selection, typing, and OS integration)
MAY build on **mapped gaze** once specified. They MUST:

- **consume** mapped gaze as an input, and
- **NOT** alter the approved backend's calibration/estimation, quality gates, or
  predict behavior to compensate for typing/interaction issues, and
- **NOT** add ad-hoc mapping corrections, learned remaps, bias, affine fits, or
  extra smoothing after the approved backend in order to hide poor gaze
  estimation.

A replacement backend MUST NOT be silently combined, averaged, or used as a
fallback cascade with the previous estimator unless a future specification
explicitly approves that architecture.

Improving typing UX MUST NOT become a reason to patch mapping without a
mapping-focused benchmark justification (Principle III). Advanced capabilities
such as predictive text, language switching, personalization, multi-monitor
support, and accessibility polish still require their own specifications — they
are not implied by enabling dwell/OS typing.

**Rationale**: Prior work layered runtime compensations atop an unstable mapping
foundation. Downstream features must not recreate that failure mode. Naming one
historical implementation (PCA4) as permanently required would block a specified,
independently validated replacement.

### II. Measurable Progress Only (NON-NEGOTIABLE)

Every calibration or mapping change MUST be evaluated using objective external
metrics, as applicable to the feature:

- **intended-key / focus accuracy** (primary acceptance metric for mapping;
  historically recorded as key-hit accuracy)
- **pixel error**
- **row accuracy**
- **repeatability across sessions**
- **reachability** of required live controls when the product surface requires it
- **latency / update rate** when pointing must remain interactive
- **practical interaction tests** defined by the feature spec (for example dwell
  typing into an external application)

Subjective feel, anecdotal demos, vendor/demo scores, and internal-only model
metrics (e.g., LOOCV, RMS, training loss) MUST NOT be the sole acceptance
criteria for mapping. They may supplement but not replace independent
screen-space mapping evidence.

Features that do not change calibration/mapping (for example dwell typing or OS
injection) MUST define measurable acceptance criteria in **their own** feature
spec. Those criteria MUST NOT replace or weaken independent mapping benchmarks.

**Rationale**: Quality gates that do not correlate with real on-keyboard mapping
have masked regressions; mapping and typing progress must stay measurable and
separable.

### III. Simple Pipeline Before Layered Compensation

Prefer a clear, testable pipeline whose sealed upstream is:

`approved gaze backend → screen-space mapped gaze`

The historical PCA4 path was `tracking → feature extraction → calibration →
mapping → mapped gaze`. A specified replacement (including official
GazeFollower) MAY own tracking, calibration, inference, and filtering internally,
provided GazeKey still consumes only sealed screen-space mapped gaze.

Specified downstream stages (for example dwell selection → key action → OS
input) MAY follow mapped gaze when an approved feature spec defines them.
Correction layers, fallback models, heuristic patches, per-region compensations,
and silent ensembles with a previous estimator on the **mapping** path MUST NOT
be added unless a controlled **mapping** benchmark demonstrates improved
intended-key accuracy over the simpler baseline **and** a feature spec
explicitly approves that architecture.

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

The **mapping foundation** (approved gaze-estimation/calibration backend +
independent screen-space mapping benchmark) remains mandatory infrastructure.
It MUST stay isolated and independently testable regardless of which
post-mapping features are active. It MUST NOT be defined as “whatever PCA4
currently does.”

Post-mapping product capabilities — including dwell interaction, typing, and OS
integration — are **not permanently forbidden**. They MAY be implemented when an
approved feature specification defines requirements, architecture boundaries,
and acceptance criteria. They MUST consume mapped gaze only and MUST NOT rewrite
or compensate the mapping foundation “for typing.”

Capabilities that remain advanced relative to core typing still require their
own specs when undertaken, including (non-exhaustively):

- predictive text
- Hebrew/English (or other) language switching
- personalization / profiles
- multi-monitor support
- advanced accessibility polish

**Rationale**: Scope discipline protects the mapping measurement boundary while
allowing specified product stages and specified backend replacement.

### VI. Testable Architecture

Code MUST be organized so tracking, calibration, mapping, evaluation/benchmark
for mapping, UI feedback, and (when present) typing/OS boundaries can be tested
independently. When an upstream backend owns tracking/calibration/inference,
GazeKey MUST still keep a testable handoff (screen-space mapped gaze), live
geometry/hit-testing, and typing/OS boundaries. Monolithic modules that mix UI,
calibration, mapping, runtime selection, and debug behavior MUST be split or
bounded behind clear interfaces as part of approved redesign tasks.

Downstream typing/interaction modules MUST NOT fold selection or OS injection
into mapper fit/predict or into post-backend mapping corrections.

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

Historical feature records (including Feature 004 specs, runs, tags, and
commits) remain evidence of the implementation and investigations of that
time. They MUST NOT be rewritten to match a later constitution amendment.

### IX. Targeted Codebase Cleanup

Clarify the **active path** carefully — not as an unplanned full rewrite. Keep
one unambiguous production gaze/calibration flow. When product packaging splits
(for example runtime product vs developer tooling), cleanup MUST be driven by an
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

**GazeKey-owned** calibration UI MUST keep the user focused on the target point.
Long explanations, detailed metrics, sample counts, debug text, and noisy
on-screen feedback MUST NOT appear on a GazeKey-hosted calibration screen while
the user is expected to fixate on a target dot.

Permitted on-screen feedback for GazeKey-owned calibration:

- target dot
- simple progress indicator (if needed)
- final pass/fail result only after calibration ends (if required)

Detailed status, quality metrics, sample counts, and failure reasons MUST go to
the run log or verbose output — not displayed as text during target fixation.

**Upstream-owned calibration exception:** When an approved external/upstream
gaze backend owns calibration, GazeKey MAY use that backend's official Preview,
Calibration, progress, result, accept, and retry UI **unmodified**. GazeKey MUST
NOT recreate a metric-heavy equivalent in GazeKey UI merely to imitate the
upstream experience. This exception does NOT permit unrelated GazeKey debug
metrics or experimental overlays during calibration.

For Feature 005, the official GazeFollower Preview/Calibration/result UI is
therefore constitutionally allowed as-is.

**Rationale**: Reading GazeKey-hosted on-screen text during calibration shifts
gaze away from the target and corrupts collected samples. Stripping or restyling
an upstream backend's official calibration UI would change the specified
estimator rather than keep GazeKey's own fixation surface minimal.

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

**Version**: 1.4.0 | **Ratified**: 2026-06-09 | **Last Amended**: 2026-08-24
