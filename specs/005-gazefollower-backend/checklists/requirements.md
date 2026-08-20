# Specification Quality Checklist: GazeFollower Backend Migration

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-20
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Estimator naming**: GazeFollower is named because it is the *specified
  candidate*, not because the spec chooses a language, library, or module
  layout. Languages, APIs, weights, and package layout are deferred to
  `/speckit-plan`. The official repository URL is recorded under Assumptions
  as a source-of-truth constraint (user requirement).
- **Audience**: Same as Features 001–004 — the developer-operator who
  calibrates and evaluates GazeKey. User stories are written as product
  outcomes (isolated trial, Y-axis improvement, safe rollback).
- **Numeric gates**: Stage 1 SC-001–SC-004 use Feature 004 T060 session
  noise (6 pp / 2.8 px / 4 pp) and the last Feature 004 “Y is used” slope
  bar (−0.80). Historical 67% / 55 px / 80% remain reference floors, not an
  automatic migrate.
- **Clarify session 2026-08-20 (calibration, geometry, reachability)**:
  Encoded eight user-provided decisions: live-layout coverage + full
  interactive-control sweep; official native 5/9/13 calibration (not
  `keyboard15`) independent of the benchmark; shared screen/DPI geometry
  contract; no PCA4/`pca_vL` 0.15 candidate gates; filter/timestamp
  audit; per-run provenance + gitignored replay; user-independent
  architecture + optional second-user smoke; production-ready only after
  mapping metrics **and** the full keyboard path, before cleanup.
  Which of 5/9/13 is pinned remains a **planning** inspection of the
  official repo.
- **Clarify session 2026-08-20 (legacy isolation and production contract)**:
  GazeFollower is an independent official pipeline; PCA4 is historical
  baseline only. Stage 1 forbids reuse of estimator-specific GazeKey
  mapping components; allowlist is backend-agnostic only. Production
  contract is **not** locked to `(x, y)`-only; planning inspects
  official outputs. Downstream redesign only after gates, never to
  inflate Stage 1. Dependency audit + isolation test where practical.
- **Constitution**: Project Context currently names the existing mapping
  stack as the foundation. This spec treats independently measured
  screen mapping as the sealed *measurement* upstream and allows
  estimator replacement after the Stage 1 gate plus review. Production
  architecture is built around GazeFollower, not the historical stack.
  `/speckit-plan` MUST record that constitution check, the dependency
  audit, and any conflict with official GazeFollower calibration/geometry/outputs.
- **No clarifications pending** from this session. Do not start
  implementation while planning has not inspected upstream calibration,
  geometry, outputs, and the dependency audit.
- Validation iteration 1 (specify): replaced leftover `main.py` wording.
- Validation iteration 2 (clarify): live layout, native calib, geometry.
- Validation iteration 3 (clarify): strict legacy isolation; Stage 1 vs
  production contract.
