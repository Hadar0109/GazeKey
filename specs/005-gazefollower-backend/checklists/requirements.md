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

## Planning obligations

Resolved by `/speckit.plan` plus the 2026-08-24 review session. Unchecked
Content Quality items remain because `spec.md` names required architecture
(pygame/Qt/GazeFollower), not because product questions are open.

- [x] Exact official GazeFollower commit/version, model/checkpoint
      identification, dependency/version approach, and license/attribution
      are recorded `[Spec §Planning Obligations 1, FR-022]`
- [x] Official GazeInfo/output API has been inspected and the GazeSample
      contract is defined without invented fields `[Spec §Planning Obligations 2, FR-016, SC-020]`
- [x] Official filtering versus GazeKey smoothing has been audited and one
      pointing-signal policy recorded `[Spec §Planning Obligations 3, FR-013, FR-014, SC-016]`
- [x] Tested native calibration protocol (including 5 / 9 / 13 and
      result/accept/recalibrate behavior) is inspected and pinned
      `[Spec §Planning Obligations 4, FR-024, FR-025]`
- [x] pygame versus PySide6 lifecycle, camera ownership, and event-loop
      boundary is designed for startup, abort/reject, recalibration, and
      shutdown `[Spec §Planning Obligations 5, FR-018, FR-019, SC-018]`
- [x] Screen-geometry / DPI / window / QRect compatibility audit lists only
      legitimate transforms `[Spec §Planning Obligations 6, FR-020, FR-021, SC-017]`
- [x] Dependency-isolation audit and exact GazeFollower → GazeKey handoff
      exist `[Spec §Planning Obligations 7, FR-011, SC-015]`
- [x] Constitution check is recorded: independently measured screen mapping
      remains the sealed measurement upstream; production gaze/calibration
      implementation becomes GazeFollower rather than PCA4/Ridge
      `[Spec §Planning Obligations 8, Guidance]`
- [x] Stage G inventory of obsolete legacy gaze runtime is listed, to be
      deleted only after Stage F `[Spec §Planning Obligations 9, FR-033]`

## Review decisions (2026-08-24) — closed

- [x] Python 3.11 product runtime; rebuild GazeKey env on 3.11; do not
      prove GazeFollower on the 3.14 venv
- [x] GazeSample validity: status, SUCCESS, finite filtered xy, both
      openness values > 10; no TrackingManager/EyeDetector; no hold-last
- [x] License of record CC BY-NC-SA 4.0; `version.py` CC BY 4.0 is
      upstream inconsistency; commercial use out of Feature 005
- [x] Official Preview/Calibration/result UI as-is (Principle XI;
      Constitution v1.4.0 exception, resolved 2026-08-24)
- [x] Geometry STOP policy is Stage A (T011 schema/helper, T012 policy);
      live keyboard values and proof are T028/T029/T030; identity/origin/DPR
      only; do not change `generate_points` preemptively
- [x] Invalid sample → `MappedGazePoint.valid=False`; Stage F natural
      blink coverage

## Notes

- **Ready for**: `/speckit.analyze` re-check, then `/speckit.implement`.
  `tasks.md` exists.
- **Estimator naming**: GazeFollower is named because it is the *specified
  production gaze/calibration subsystem*, not because the spec chooses a
  language, package layout, or wrapper module.
- **Intentional architecture names**: pygame Preview/Calibration, PySide6
  keyboard, QRect hitboxes, GazeInfo/GazeSample, and sequential UI
  ownership are required product constraints from the 2026-08-24 rewrite.
  They fail the generic “no implementation details” checklist items on
  purpose. HOW is now recorded in `plan.md` / `research.md`.
- **Audience**: Same as Features 001–004 — the developer-operator who
  calibrates and evaluates GazeKey.
- **Removed Stage 1 assumptions**: Normal Feature 005 application no
  longer continues on PCA4 throughout a long research trial;
  GazeFollower is no longer required to exist only as a separate
  evaluation backend; migration/integration is no longer blocked until
  Feature 004 T060 percentage/noise formulas are beaten; GazeKey no longer hosts
  candidate calibration fixation UI; production architecture is no
  longer forced to preserve the old estimator comparison contract.
- **Numeric gates**: Feature 004 T060 figures remain reference evidence
  only. Decisive acceptance is integrated product usability across at
  least three product-condition sessions (SC-001–SC-012), with
  independent mapping metrics as evidence (SC-013).
- **Clarify session 2026-08-24**: Production-integration rewrite, then
  plan, then review closure of Python 3.11, GazeSample validity,
  CC BY-NC-SA 4.0, official UI as-is, geometry STOP gate, and no
  hold-last.
- **Constitution**: Independently measured screen mapping remains the
  sealed *measurement* upstream; production implementation is
  GazeFollower. Former v1.3.0 C1/C2 letter-conflicts were **resolved by
  Constitution v1.4.0 on 2026-08-24** (historical notes in `plan.md`
  Complexity Tracking, not active exceptions).
- **No product-scope or planning-review items pending.** Spec status is
  Ready for implementation. Next command: `/speckit.analyze` (re-check)
  or `/speckit.implement` after that review.
- Validation iteration 1 (2026-08-24 rewrite): Stage 1 research-trial spec
  replaced.
- Validation iteration 2 (2026-08-24 plan + review): planning obligations
  and six review conflicts closed in plan/research/data-model/contracts.
- Validation iteration 3 (2026-08-24 constitution + analyze remediation):
  Constitution v1.4.0; Stage A naming; SC-012 Stage E cite + one Stage F
  recalibration reconfirm; spec Ready for implementation; T053/T064/T011/
  T024/T047 wording.
