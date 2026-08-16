# Implementation Plan: Gaze Mapping Accuracy

**Branch**: `004-gaze-mapping-accuracy` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-gaze-mapping-accuracy/spec.md`

## Summary

Make **user gaze → intended virtual-keyboard key** accurate enough for
practical typing on the Feature 003 product, without putting the developer
benchmark into the product path and without compensating via dwell or
predictive text.

Sealed upstream remains:

`tracking → gaze features → calibration (spatial targets) → PCA4 mapping →
mapped gaze`

Product typing still **consumes** mapped gaze (`hit-test → dwell → KeyAction
→ OS → suggestions`). Feature 004 changes collection, geometry consistency,
evaluation fidelity, coverage investigation, and — only if still needed —
the existing simple mapper.

**Technical approach** (research R1):

1. Make developer evaluation a **trustworthy measurement** of the runtime
   mapper / geometry / key-hit path; score **mapped-key focus** (inside
   intended rect + focus stability), with **held-out** keys, key-relative
   error, and documented fidelity gaps.
2. Record a **fresh current-state baseline** (no mapping code change).
3. Investigate and, one area at a time, fix **collection quality**,
   **train/live sync**, and **003 geometry** — hypotheses, not a patch dump.
4. Investigate **calibration domain vs prediction domain** (spatial coverage);
   current key-centered 15 is a control, not assumed optimal.
5. Touch mapper parameters only if held-out mapped-key and `hadar` (suggestions
   off) are still insufficient.
6. Each experiment: **keep / revert / inconclusive**; do not stack unproven
   changes. Each **keep** is a Git checkpoint.

Exact point counts, smoother values, alpha, correction layers, and mapper
replacement are **experiment outcomes**, not this plan’s frozen solution.

## Technical Context

**Language/Version**: Python 3.8+ (project baseline)

**Primary Dependencies**: PySide6 ≥6.6, OpenCV ≥4.8, MediaPipe ≥0.10, NumPy
≥1.24, pynput ≥1.7.6 (OS adapter unchanged). No new pip deps planned.

**Storage**: Per-session files under `runs/<session_id>/` (calibration +
evaluation summaries). No database. Baseline run id recorded in experiment
notes.

**Testing**: pytest — evaluation scoring (inside-key, held-out letters,
editing/control slice, isolation from `gazekey.ui` product enablement),
collection gate dimensionality, aggregation coherence, **spatial fit (no
key-id / label / row as regression inputs)**, geometry/hit-test contracts,
resize unsupported-or-tested. Live webcam / `hadar` + hold-out words =
**USER GATE**.

**Target Platform**: Windows desktop (primary)

**Project Type**: Desktop application (PySide6 + tracking thread)

**Performance Goals**: Tracking ~30 FPS unchanged; evaluation must not run
on the product typing path

**Constraints**:

- Spec 004 clarifications (2026-08-16) + [research.md](./research.md)
- Constitution v1.3.0: mapping independently measured; no downstream
  compensation; simple pipeline before new layers; minimal calib UI
- Developer evaluation isolated (FR-020–022)
- 67% / 55 px / 80% row = **reference floors** vs baseline, not automatic
  final accept
- Feature 003 product behavior preserved
- One logical accuracy change per iteration

**Scale/Scope**: Single user, single monitor, Feature 003 QWERTY
letter/editing keyboard as required **prediction domain**; English
suggestions remain but stay unused during mapping word checks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (GazeKey **v1.3.0**)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| Accuracy First | Mapping independently validated; 003 stages consume mapped gaze; no dwell/prediction compensation | ✅ |
| Measurable Progress | Mapped-key / key-relative / row / two-session baseline + 3-session final; 67% is reference; held-out letters + editing keys + `hadar` vs baseline | ✅ |
| Simple Pipeline | Start from PCA4; new layers only after collection/geometry/coverage and a mapping eval win | ✅ |
| Spec Before Code | Spec + plan + `tasks.md` exist; implement after approval | ✅ |
| Feature Scope Control | Mapping foundation only; 003 product preserved; no language/personalization | ✅ |
| Testable Architecture | Eval in `tools/evaluation`; collection/mapping/UI remain separable | ✅ |
| Run Clarity | One evaluation summary + calib summary; no new diagnostics platform | ✅ |
| Documentation Hierarchy | Spec Kit SoT for 004; 001 docs historical | ✅ |
| Targeted Cleanup | Only active-path confusion on calib/mapping/eval fidelity; inventory in tasks | ✅ |
| Simple Logging | Existing verbose flag; no new logging framework | ✅ |
| Minimal Calibration UI | Unchanged: dot + optional progress; pass/fail after session | ✅ |

**Post-design re-check**: Same — evaluation fidelity and spatial-target
contracts do not add mapper complexity; layout candidates are experiments
after baseline.

## Project Structure

### Documentation (this feature)

```text
specs/004-gaze-mapping-accuracy/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── mapping-evaluation.md
│   ├── calibration-spatial-targets.md
│   ├── pipeline-sync.md
│   └── experiment-discipline.md
└── tasks.md             # generated; implement after Phase 2 two-session gate
```

### Source Code (repository root)

```text
gazekey/
├── tracking/            # UNCHANGED unless bottleneck proven
├── features/            # extractor, smoother — sync experiments
├── calibration/         # session, fixation_gate, outliers, targets
├── mapping/             # pca4 ridge + config — last lever
├── runtime/             # mapper_runtime predict/clamp
├── layout/              # inspect_keyboard_layout
├── typing/              # hit_test, dwell — consume mapped gaze only
├── ui/                  # overlay + keyboard geometry; no 003 UX redesign
└── prediction/          # UNCHANGED; unused during mapping word checks

tools/evaluation/        # developer measurement only (fidelity + slices)
tools/preview/           # preserved

tests/
├── unit/                # gate, aggregation, spatial fit, eval scoring
├── contract/            # eval isolation; hit-test agreement
└── integration/         # pipeline without requiring webcam
```

**Structure Decision**: Extend existing calibration/mapping/evaluation
modules. Do not add a new mapper package. Do not import `tools.evaluation`
from product typing/calibration fit.

## Implementation phases (for tasks.md)

### Phase A — Evaluation fidelity + baseline (gate)

- Align developer evaluation with runtime predict + `hit_test_layout_keys`
- Score inside-tight-rect + focus stability; key-relative error
- Repeatability vs held-out **letter** vs **editing/control** slices
  (research R3)
- Document `fidelity_notes`
- Capture **two** **current-state baseline** sessions (A and B; no
  mapping/collection edits)
- USER GATE: `hadar` suggestions-off on unchanged product; record
  wrong-focus letters for later comparison
- **Gate**: both baseline artifacts exist; eval no longer *only* mean-points
  the historical 15 anchors; editing/control slice present

### Phase B — Collection quality (one experiment at a time)

Hypotheses (confirm/reject with eval vs baseline). Each is an
**investigation**, not a predetermined patch:

- Fixation gate vs full mapper representation
- Coherent per-frame aggregation
- Left/right `u` semantics
- Missing-eye policy aligned with predict
- Label-based outlier peers vs spatial grid
- **Warning-only calibration quality / pass-fail gates** (research R10):
  correlate blocking vs warning-only vs clean with held-out mapped-key and
  `hadar`; do not harden or drop gates without that evidence
- **Spatial row/column metadata** used by quality checks (research R5):
  especially Space and other non-letter controls sharing a letter-row or
  coarsened column index; confirm tags vs `screen_x/y` clusters before
  retagging

Keep / revert / inconclusive after each. Do not stack. Do not combine
metadata retagging with a gate-policy change. Quality-gate experiments MUST
NOT add fixation-screen metrics (FR-004); pass/fail only after the session
(FR-005). Each `keep` is a Git checkpoint.

### Phase C — Train/live sync + Feature 003 geometry

- Smoothing/averaging differences: measure, then one justified change or
  documented keep
- Overlay vs restored keyboard vs clip vs hit-test coordinates
- Prediction-domain clip (keyboard letter/editing AABB)
- **Clip/clamp when predictions fall outside the prediction domain**
  (research R7): report unclamped vs clamped hit-test as an evaluation
  diagnostic; confirm whether clamp pins edge keys, whether clip bounds
  are wrong, or whether unclamped points still miss — do not remove or
  expand clamp without that evidence
- Automated geometry tests + USER GATE if layout/clip changes
- **Resize/reposition/scaling:** test refresh if a supported path exists;
  otherwise record **unsupported** and close FR-014 for user-driven resize
  (overlay vs restored keyboard still required)

### Phase D — Coverage / calibration domain

- One layout candidate vs current key-centered 15 per experiment
  (research R4 A/B/C)
- Further candidates allowed after revert/inconclusive; a failed first
  candidate does **not** prove `keyboard15` is optimal
- Targets remain spatial; fit still coordinate-only
- Recompute held-out / editing slices after any layout keep
- If a layout keep changes target positions, re-check spatial row/col
  metadata used by quality (Phase B item) — still a separate experiment

### Phase E — Mapper lever (only if needed)

- Only if held-out inside-key and `hadar` focus still fail vs baseline
- **Diagnose the existing auto-alpha selection rule** (research R11):
  among near-best LOOCV scores, as-built picks the **largest** alpha.
  Record selected alpha vs the grid; treat a selection-rule change as
  one mapper lever — not a predetermined retune
- Otherwise one lever (alpha **or** coupling **or** a single justified
  layer) — not combined with the auto-alpha diagnosis if both would
  change
- Same experiment contract

### Phase F — Acceptance addendum

- Compare the kept stack to **both** baseline sessions (held-out letters,
  editing/control, key-relative, stability)
- **3-session final repeatability** on the kept stack (SC-004)
- USER GATE: `hadar` wrong-focus vs baseline A/B; then 2–3 additional
  short words not used during development (suggestions unused)
- Confirm 003 product path (suggestions still work when used; prediction
  bar is not a mapping-accept slice)
- Historical 67% used as reference, not automatic pass
- Full-project `pytest -q`

## Complexity Tracking

No constitution violations requiring justification.

## Generated artifacts

| Artifact | Path |
|----------|------|
| Research | [research.md](./research.md) |
| Data model | [data-model.md](./data-model.md) |
| Quickstart | [quickstart.md](./quickstart.md) |
| Contracts | [contracts/](./contracts/) |
| Tasks | [tasks.md](./tasks.md) |

**Next command**: `/speckit-implement` after reviewing `tasks.md` (do not skip
the Phase 2 baseline gate). Optional: `/speckit.git.commit` to save plan +
tasks.
