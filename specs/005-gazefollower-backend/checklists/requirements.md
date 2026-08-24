# Specification Quality Checklist: GazeFollower Production Integration

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-20
**Updated**: 2026-08-24
**Feature**: [spec.md](../spec.md)

## Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for the GazeKey developer-operator audience used by Features 001–004
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [ ] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Planning obligations still required

These are specified as `/speckit.plan` work, not missing product-scope
decisions. They keep this checklist from being marked fully complete.

- [ ] Exact official GazeFollower commit/version, model/checkpoint
      identification, dependency/version approach, and license/attribution
      are recorded `[Spec §Planning Obligations 1, FR-022]`
- [ ] Official GazeInfo/output API has been inspected and the GazeSample
      contract is defined without invented fields `[Spec §Planning Obligations 2, FR-016, SC-020]`
- [ ] Official filtering versus GazeKey smoothing has been audited and one
      pointing-signal policy recorded `[Spec §Planning Obligations 3, FR-013, FR-014, SC-016]`
- [ ] Tested native calibration protocol (including 5 / 9 / 13 and
      result/accept/recalibrate behavior) is inspected and pinned
      `[Spec §Planning Obligations 4, FR-024, FR-025]`
- [ ] pygame versus PySide6 lifecycle, camera ownership, and event-loop
      boundary is designed for startup, abort/reject, recalibration, and
      shutdown `[Spec §Planning Obligations 5, FR-018, FR-019, SC-018]`
- [ ] Screen-geometry / DPI / window / QRect compatibility audit lists only
      legitimate transforms `[Spec §Planning Obligations 6, FR-020, FR-021, SC-017]`
- [ ] Dependency-isolation audit and exact GazeFollower → GazeKey handoff
      exist `[Spec §Planning Obligations 7, FR-011, SC-015]`
- [ ] Constitution check is recorded: independently measured screen mapping
      remains the sealed measurement upstream; production gaze/calibration
      implementation becomes GazeFollower rather than PCA4/Ridge
      `[Spec §Planning Obligations 8, Guidance]`
- [ ] Stage G inventory of obsolete legacy gaze runtime is listed, to be
      deleted only after Stage F `[Spec §Planning Obligations 9, FR-033]`

## Notes

- **Ready for**: `/speckit.plan`. **Not ready for**: `/speckit.implement`.
- **Estimator naming**: GazeFollower is named because it is the *specified
  production gaze/calibration subsystem*, not because the spec chooses a
  language, package layout, or wrapper module. Languages, APIs, weights,
  and package layout remain planning work except where the user required
  an architecture boundary.
- **Intentional architecture names**: pygame Preview/Calibration, PySide6
  keyboard, QRect hitboxes, GazeInfo/GazeSample, and sequential UI
  ownership are required product constraints from the 2026-08-24 rewrite.
  They fail the generic “no implementation details” checklist items on
  purpose. Remaining HOW (exact lifecycle mechanism, exact GazeSample
  fields, exact pinned commit, exact 5/9/13 choice) belongs in
  `/speckit.plan`.
- **Audience**: Same as Features 001–004 — the developer-operator who
  calibrates and evaluates GazeKey. User stories are written as product
  outcomes (official calibration, live keyboard handoff, preserved
  typing, safe recalibration/shutdown, integrated acceptance then
  cleanup).
- **Removed Stage 1 assumptions**: Normal Feature 005 application no
  longer continues on PCA4 throughout a long research trial;
  GazeFollower is no longer required to exist only as a separate
  evaluation backend; migration/integration is no longer blocked until
  T060 percentage/noise formulas are beaten; GazeKey no longer hosts
  candidate calibration fixation UI; production architecture is no
  longer forced to preserve the old estimator comparison contract.
- **Numeric gates**: Feature 004 T060 session noise (6 pp / 2.8 px /
  4 pp), Y-slope −0.80, and historical 67% / 55 px / 80% remain
  **reference evidence only**. They do not gate whether integration may
  begin and are not an automatic cleanup trigger. Decisive acceptance is
  integrated product usability across at least three product-condition
  sessions (SC-001–SC-012), with independent mapping metrics still
  recorded as evidence (SC-013).
- **Clarify session 2026-08-24**: Encoded the production-integration
  rewrite: GazeFollower owns camera-to-filtered screen gaze and official
  UIs; GazeKey begins at the handoff; sequential pygame then Qt;
  no post-GazeFollower mapper; prefer official filtered gaze; Git
  rollback rather than a dual-pipeline cascade; cleanup only after
  integrated acceptance.
- **Preserved 2026-08-20 safety**: chin/head-support product condition;
  live-layout coverage and full interactive-control sweep; official
  native calibration not `keyboard15`; shared screen/DPI geometry
  contract; no PCA4/`pca_vL` 0.15 candidate gates; filter/timestamp
  audit; per-run provenance + gitignored replay; user-independent
  architecture + optional second-user smoke; Feature 004 read-only;
  no third estimator/ensemble/fallback; Principle XI applies to any
  GazeKey-hosted calibration surface (official GazeFollower UI is used
  as-is, with conflicts recorded rather than restyled).
- **Constitution**: Project Context currently names the existing PCA4
  mapping stack as the foundation. This spec treats independently
  measured screen mapping as the sealed *measurement* upstream and
  selects GazeFollower as the production implementation.
  `/speckit.plan` MUST record that constitution check, the dependency
  audit, GazeSample contract, filter policy, native protocol, geometry
  audit, and pygame/Qt lifecycle design.
- **No product-scope clarifications pending** from this rewrite. Do not
  start implementation while planning has not completed the Planning
  Obligations list.
- Validation iteration 1 (2026-08-24 rewrite): replaced Stage 1 research-
  trial spec with production-integration spec; left implementation-detail
  and technology-agnostic checklist items unchecked because required
  architecture names and remaining upstream inspections belong in
  `/speckit.plan`.
