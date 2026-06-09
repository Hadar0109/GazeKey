# Research: Calibration & Gaze Mapping MVP

**Date**: 2026-06-09 (revised)  
**Feature**: `001-calibration-mapping-mvp`

## R-1: Calibration target count and placement

**Decision**: Active MVP ships **one calibration layout at a time**. Initial
candidate: evaluate whether **keyboard13** or a **9-point key-aligned** layout
outperforms dense `keyboard15` — adjust based on **benchmark evidence**, not
LOOCV alone.

**Rationale**:

- Repository default `keyboard15` may add head-movement noise between fixations
  (`docs/current-status.md`).
- Layout is a calibration concern, separate from mapper choice.
- Changes are result-driven: benchmark row/key failure patterns inform whether
  to reduce density or reposition targets.

**Alternatives considered**:

| Alternative | Status |
|-------------|--------|
| Lock keyboard15 | Rejected as default — spec defers count; evidence questions density |
| Fullscreen 9-point grid | Not key-aligned; weaker keyboard tie-in |
| Change mapper instead of layout when keys fail | Wrong lever — mapping direction is PCA4 (R-3) |

---

## R-2: Benchmark test key set (separate from calibration)

**Decision**: Use the existing **15-key benchmark set** (`DEFAULT_SAMPLE_KEYS` in
`gazekey/debug/keyboard_accuracy.py`) as the **fixed validation set**.

**Rationale**: Archived `runs/` baseline; covers rows/columns; independent of
calibration targets (FR-010, FR-011).

---

## R-3: Active mapping approach — PCA4 baseline (chosen)

**Decision**: **PCA4 ridge (`pca4_baseline`)** is the chosen mapping direction
for this MVP. No broad mapper variant comparison or multi-candidate ranking in
the active path.

| Aspect | Choice |
|--------|--------|
| Features | PCA eye-local `pca_uL`, `pca_uR`, `pca_vL`, `pca_vR` |
| Model | Ridge regression — X from u features, Y from v features |
| Code | `gazekey/mapping/ridge.py`, config in `typing_candidate.py` |
| Runtime smoothing | `PcaFeatureSmoother` (existing alpha) before predict |

**Out of active MVP path** (remain in repo, not selectable):

- `poly12` / `poly12_ridge_split` / decoupled variants
- Multi-candidate LOOCV ranking in `fit_calibration_mapper`
- v1 IDW / affine mappers
- `row_aware`, `idw_ratio`, `idw_local`

**Post-fit corrections** (row bias, local Y): Present in repository from prior
work but **not** in the initial MVP active stack. Reintroduce a single layer only
when benchmark per-key results show a specific failure mode it fixes — documented
as a targeted task, not a variant hunt.

**Rationale**:

- Prior analysis (`TYPING_CANDIDATE.md`) already selected PCA4 direction; accuracy
  problem is reliability (20–60%), not lack of mapper options.
- Constitution Principle III: improve the simple pipeline before adding layers.
- Benchmark should diagnose *what* fails (rows, keys, drift), not trigger another
  mapper bake-off.

**Improvement process** (result-driven):

1. Run benchmark after calibration + preview check.
2. Read per-key `dx`/`dy`, row accuracy, failure clusters in run summary.
3. Apply **one** targeted change (calibration target, collection gate, ridge alpha,
   or one justified correction layer).
4. Re-benchmark; compare run summaries.
5. Repeat — do not compare poly12/decoupled/IDW alternatives.

---

## R-4: Calibration pass/fail criteria

**Decision**: Calibration **pass** = all targets completed with minimum samples
and basic sanity (face tracked, head drift within limits). **LOOCV/region gates
supplementary only** — logged, not sole gate.

**Rationale**: Gates passed at ≤33% key accuracy in archived sessions.

---

## R-5: Post-calibration user mode (CQ-3 resolved)

**Decision**: **Preview-first** after calibration pass. Benchmark **manual start**
(button/menu). Dwell typing disabled in MVP flow.

---

## R-6: Run summary format

**Decision**: Console summary + one lightweight file record per run. Reuse
`calibration_summary.csv` pattern; benchmark metrics in companion row or file.

---

## R-7: Architecture extraction strategy

**Decision**: Incremental extraction from `virtual_keyboard.py` into controllers
and `gazekey/evaluation/`.

---

## R-8: Tracking and features (reuse)

**Decision**: No change to MediaPipe tracking or `FrameFeatures` unless benchmark
proves extraction is the bottleneck.

---

## R-9: Task and evaluation discipline

**Decision**: `tasks.md` MUST enforce practical, result-driven work:

1. **Baseline PCA4 run** before Phase 8 (saved summary in `runs/`); if blocked, fix flow first
2. **One accuracy change per iteration** — T030–T033 are mutually exclusive picks from plan decision guide
3. **Failure analysis** after every benchmark (which keys/rows; mapping vs geometry vs collection)
4. **PCA4 fit iteration** (T033) allowed only when failure analysis justifies — not mapper variant hunts
5. **Keyboard geometry verification** before trusting scores
6. **Cleanup phase B** after **active PCA4 path proven** (plan definition) — delete/archive, not disconnect-only
7. **Minimal `evaluation/`** — benchmark + summary + failure fields only

**Rationale**: Prevents parallel accuracy changes, refactors without baselines, or
evaluation sprawl into a diagnostics platform.

---

## R-10: Resolved clarifications (CQ-1–CQ-4)

| ID | Resolution |
|----|------------|
| CQ-1 | Initial spec thresholds binding; no tightening yet |
| CQ-2 | Per-session calibration only |
| CQ-3 | Preview-first; manual benchmark |
| CQ-4 | Camera preview optional, hidden by default; never on fixation overlay |
