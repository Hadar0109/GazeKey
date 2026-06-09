# Implementation Plan: Calibration & Gaze Mapping MVP

**Branch**: `001-calibration-mapping-mvp` | **Date**: 2026-06-09 (revised 2) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-calibration-mapping-mvp/spec.md`

## Summary

Deliver a **simple, testable pipeline** that answers one question: after calibration,
does mapped gaze land on the correct virtual-keyboard key? The redesign reuses the
existing MediaPipe/OpenCV tracking stack and PySide6 keyboard shell, but **simplifies**
the active path: one calibration flow (v2), **one PCA4-based mapper** at runtime,
read-only preview, a **separate** benchmark validation set, and lightweight run summaries.

**Technical approach**:

1. **Separate calibration targets from benchmark keys** — calibration learns mapping;
   benchmark validates it using the existing 15-key sample set (`DEFAULT_SAMPLE_KEYS`
   in `gazekey/debug/keyboard_accuracy.py`), independent of calibration layout.
2. **PCA4 as the chosen mapping direction** — active MVP uses `pca4_baseline` ridge
   on PCA u/v features (`gazekey/mapping/ridge.py`, `typing_candidate.py`). No
   mapper variant hunt: poly12, decoupled, IDW, and multi-candidate ranking stay
   out of the active path.
3. **Result-driven improvement** — use benchmark per-key results (which keys/rows fail,
   pixel error patterns) to guide targeted fixes to **calibration collection, target
   layout, and the single PCA4 fit path**. Add a correction layer only when a benchmark
   proves it helps — not by re-comparing all historical mapper variants.
4. **Calibration layout** — may adjust target count/placement (9 / 13 / 15) based on
   benchmark evidence; dense `keyboard15` is a suspect, not a locked default.
5. **MVP user flow** — launch → calibrate → **preview-only** → **manual** benchmark →
   pass/fail summary. Dwell/intent/typing disabled in the normal flow.
6. **Targeted cleanup** — one reachable calibration/mapping path first; **delete or
   archive** unused code once the active path is proven (dedicated tasks per removal).
7. **Minimal evaluation module** — thin benchmark + run summary + failure analysis only;
   not a diagnostics framework.

## Technical Context

**Language/Version**: Python 3.8+ (project baseline per `requirements.txt` and tests)

**Primary Dependencies**: PySide6 ≥6.6, OpenCV ≥4.8, MediaPipe ≥0.10, NumPy ≥1.24

**Storage**: Lightweight files only — reuse/extend `calibration_summary.csv` pattern
and optional per-session folder under `runs/`; no database

**Testing**: pytest (`tests/`, 61 existing tests); add MVP acceptance tests for
benchmark scoring, calibration pass/fail, and preview read-only behavior

**Target Platform**: Windows desktop (primary dev environment)

**Project Type**: Desktop application (single-process PySide6 + background tracking thread)

**Performance Goals**: ~30 FPS tracking; calibration completes in under 2 minutes;
benchmark 15 keys in under 3 minutes

**Constraints**:

- Constitution v1.2.0: no diagnostics platform, no multi-mode logging framework
- Fixation UI: dot + progress only during calibration
- Preview read-only: no key activation or text buffer updates
- Internal LOOCV/region gates must not be sole acceptance criteria

**Scale/Scope**: Single user, single monitor, in-app virtual keyboard letter region;
not multi-user or OS injection

## Resolved Decisions (formerly CQ-1–CQ-4)

| ID | Decision | Implementation impact |
|----|----------|----------------------|
| **CQ-1** | Use spec **initial success thresholds** as binding for this MVP; do not tighten yet | Benchmark pass/fail: ≥67% key-hit (10/15), ≤55 px median error, ≥80% row accuracy, ≥53% floor / ≤20 pt spread across 3 sessions |
| **CQ-2** | **Per-session calibration only** | Calibrate every launch; do not load `calibration_v2.json` on startup |
| **CQ-3** | **Preview-first**; benchmark started **manually** | After calibration pass → read-only preview; user triggers benchmark via button/menu |
| **CQ-4** | Camera preview **optional, hidden by default** | Floating preview window off unless user enables; **must not appear on calibration fixation overlay** |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (GazeKey v1.2.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| Accuracy First | Scope limited to calibration/mapping; dwell/typing not optimized | ✅ |
| Measurable Progress | Benchmark key-hit, pixel error, row accuracy, repeatability in SC + plan | ✅ |
| Simple Pipeline | `tracking → features → calibration → mapping → preview → benchmark` | ✅ |
| Spec Before Code | spec.md approved; plan.md (this); tasks.md pending | ✅ |
| MVP Scope Control | No prediction, language, OS injection, personalization, multi-monitor | ✅ |
| Testable Architecture | Module boundaries defined below; orchestrator split planned | ✅ |
| Run Clarity | Reuse summary CSV + console; no artifact sprawl | ✅ |
| Documentation Hierarchy | Spec Kit docs are source of truth | ✅ |
| Targeted Cleanup | Scoped to calibration/mapping path only | ✅ |
| Simple Logging | Quiet default + single verbose flag; no logging framework | ✅ |
| Minimal Calibration UI | Strip overlay debug text during fixation | ✅ |

## Project Structure

### Documentation (this feature)

```text
specs/001-calibration-mapping-mvp/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Entities and state
├── quickstart.md        # Manual validation procedure
├── contracts/           # Internal module contracts
│   ├── pipeline.md
│   ├── calibration-session.md
│   ├── gaze-mapper.md
│   ├── benchmark.md
│   ├── evaluation.md
│   └── run-summary.md
├── spec.md
└── tasks.md             # Phase 2 (/speckit-tasks — not yet created)
```

### Source Code (repository root — MVP target layout)

```text
main.py                          # Entry unchanged
gazekey/
  tracking/                      # KEEP — MediaPipe pipeline (reuse)
  features/                      # KEEP — FrameFeatures, smoother (reuse)
  layout/                        # KEEP — key geometry (reuse)
  calibration2/                  # EVOLVE — sole active calibration path
  mapping/                       # SIMPLIFY — one active mapper + fit path
  evaluation/                    # NEW — minimal: benchmark, summary, failure analysis only
  ui/
    virtual_keyboard.py          # SHRINK — orchestration only; delegate to controllers
    calibration_overlay.py       # EVOLVE — minimal fixation UI
    gaze_preview.py              # NEW (or extract) — read-only preview dot
  calibration/                   # DEPRECATE from active flow (v1 — keep code, unreachable)
  intent/                        # OUT OF MVP flow (keep code, not wired)
  selection/                     # OUT OF MVP flow (keep code, not wired)
  typing/                        # OUT OF MVP flow except TextBuffer for mouse clicks
  debug/                         # KEEP — keyboard_accuracy reused by evaluation/
tests/
  unit/                          # Extend for MVP contracts
  integration/                   # NEW — calibration → preview → benchmark flow
runs/                            # Per-session summaries (optional subfolders)
```

**Structure Decision**: Evolve in place under `gazekey/` rather than a parallel
package. New `gazekey/evaluation/` is a **thin layer** — extract only benchmark
execution, pass/fail scoring, per-key failure summary, and run-summary writing from
`gazekey/debug/keyboard_accuracy.py` and `virtual_keyboard.py`. It MUST NOT grow
into a diagnostics platform (no dashboards, replay engines, multi-mapper compare
tools, or layered analysis frameworks). Deeper offline analysis stays in `scripts/`
and existing `debug/` — out of the MVP user path.

**Keyboard geometry** (verify before trusting benchmark scores):

- `gazekey/layout/layout_inspector.py` — key centers, rows, hitboxes (`KeyGeometryRow`)
- `gazekey/typing/key_hit_tester.py` — gaze point vs key hitbox
- Calibration targets (`calibration2/targets.py`) and benchmark keys must align
  with the same layout snapshot used for hit testing

## Pipeline Design

### Active MVP runtime flow

```text
main.py
  └─ VirtualKeyboard (thin orchestrator)
       ├─ TrackingManager + TrackingBridge  → EyeData
       ├─ FeatureExtractor                  → FrameFeatures
       ├─ CalibrationController           → CalibrationSession (calibration2)
       │     └─ CalibrationOverlay        → dot + progress only
       ├─ MapperFit (pca4_baseline)      → GazeMapper (PCA4 ridge only in active path)
       ├─ GazePreviewController           → read-only dot on keyboard
       ├─ BenchmarkRunner (evaluation/)  → KeyAccuracyResult + pass/fail
       └─ RunSummaryWriter (evaluation/)  → console + lightweight file
```

### Calibration vs benchmark (separate concerns)

| Aspect | Calibration | Benchmark |
|--------|-------------|-----------|
| Purpose | Learn feature → screen mapping | Validate mapping on held-out keys |
| Target set | Planning evaluation: 9 / 13 / 15 layouts (`targets.py`) | Fixed 15 keys: `DEFAULT_SAMPLE_KEYS` |
| Overlap | May share some keys; not required | Independent validation set by design |
| UI | Fixation dots on keyboard | Highlight/prompt each test key in sequence |
| Pass/fail | Collection + sanity checks; not LOOCV-only | Key-hit accuracy vs SC-001–004 |

### Active mapping (PCA4 — fixed direction)

| Aspect | MVP choice |
|--------|------------|
| Core mapper | `pca4_baseline` — ridge on PCA u/v (`pca_uL`, `pca_uR`, `pca_vL`, `pca_vR`) |
| Fit entry point | `fit_calibration_mapper()` wired to PCA4 only; no multi-candidate ranking |
| Post-fit layers | Start with **PCA4 only**. Existing row bias / local Y in repo are **not** in the active path unless a benchmark-driven change proves they fix a measured failure mode |
| Out of active path | `poly12`, `decoupled_split`, `idw_*`, `row_aware`, v1 affine/IDW, LOOCV-based mapper switching |

**Improvement loop** (result-driven, not variant-hunting):

```text
calibrate → preview → benchmark → read per-key failures (row, dx/dy patterns)
  → hypothesize fix (calibration targets, collection, fit params, one justified layer)
  → re-benchmark → compare to prior run summary
```

Do **not** reopen a broad mapper comparison matrix. Benchmark answers *what* fails;
implementation changes target *that* failure within the PCA4 pipeline.

### Result-driven work discipline (required in `tasks.md`)

Every accuracy improvement cycle in `tasks.md` MUST follow this pattern:

```text
1. Baseline PCA4 run   — calibrate → preview → benchmark → save run summary
2. Failure analysis    — read per-key misses, row errors, dx/dy from summary
3. One focused change  — calibration, geometry, collection, or PCA4 fit only
4. Re-benchmark        — compare to baseline summary (improved / unchanged / worse)
```

**Mandatory task categories** (for `/speckit-tasks`):

| Category | Required content |
|----------|------------------|
| **Baseline PCA4 run** | Before any major pipeline change, task to run end-to-end PCA4 path and record baseline summary in `runs/` for comparison |
| **Failure analysis** | After every benchmark task, task to document which keys/rows failed and likely cause (mapping vs geometry vs collection) — output is a short written conclusion, not a new tool |
| **Keyboard geometry / hitboxes** | Task(s) to verify `inspect_keyboard_layout()` centers and hitboxes match on-screen keys; calibration targets and benchmark hit tests use the same geometry; fix mismatches before interpreting accuracy |
| **Cleanup** | Early tasks may *disconnect* legacy paths; **after** active PCA4 path is chosen and baseline exists, include dedicated delete/archive tasks for unused calibration/mapping code (one approved task per removal) |
| **Evaluation module** | Tasks scoped to benchmark runner + summary writer + failure fields only; explicitly exclude diagnostics framework work |

**Major change** means: calibration layout switch, fit/predict wiring change, overlay
UX change, hitbox/geometry fix, or adding a post-fit layer. It does **not** mean
every small bugfix — but any change expected to move benchmark metrics requires a
baseline run first.

### Calibration layout (may adjust based on benchmark evidence)

| Layout | Targets | Source | Notes |
|--------|---------|--------|-------|
| **C1** | 9 | 3×3 key-aligned (`default9` / row×col keys) | Fewer fixations; less head travel |
| **C2** | 13 | `keyboard13` | Drops 2 interior anchors vs keyboard15 |
| **C3** | 15 | `keyboard15` (current default) | Dense; reference baseline |

**Adjustment rule**: Change layout only when benchmark shows a clear pattern
(e.g., row-level failure, excessive head travel between dense targets) — not
by LOOCV alone. Ship one layout in the active path at a time.

### Quality gates redesign

| Current (problem) | MVP (planned) |
|-------------------|---------------|
| LOOCV/region gates as primary pass/fail | **Benchmark** is primary acceptance |
| Gates can pass at 27% key accuracy | Calibration pass = completed collection + basic sanity (face detected, min samples per target) |
| LOOCV RMS reported | LOOCV **supplementary** in run summary only |

### Run summary (lightweight)

- **Console**: One block per run — `[calibration] PASS/FAIL …` / `[benchmark] PASS/FAIL X/N keys …`
- **File**: Append row to existing `calibration_summary.csv` for calibration; add
  `benchmark_summary.csv` (same schema style) OR single `runs/<session_id>/summary.txt`
  with both outcomes — **one readable record per run**, not multiple parallel dumps
- **Verbose**: `GAZEKEY_VERBOSE=1` (consolidate existing env vars gradually) exposes
  per-target detail; default off

### Targeted cleanup (in scope — two phases)

**Phase A — disconnect** (before or during active-path wiring):

| Item | Action |
|------|--------|
| v1 calibration fallback | Unreachable from normal user flow |
| Dwell typing / intent / selection | Not invoked in MVP gaze loop |
| Placeholder suggestion bar, language toggle | Hidden from active flow |
| Experimental mappers | Not selectable at runtime |
| Multi-mode env toggles | Debug-only; not in user flow |

**Phase B — delete or archive** (after baseline PCA4 run + active path proven):

| Item | Action | Prerequisite |
|------|--------|--------------|
| Unused v1 calibration entry points | Delete or move to `archive/` | v2-only path verified |
| Unused mapper wiring (poly12 ranking, etc.) | Delete or archive dead code paths | PCA4-only fit confirmed in tasks |
| Disconnected dwell/intent hooks in orchestrator | Remove dead branches | Preview+benchmark flow stable |
| Row bias + local Y | Delete/archive **or** keep dormant | Only if benchmark never adopts them |

Each Phase B item = **one dedicated approved task** (constitution IX). Disconnect
alone is insufficient for final MVP cleanup — the goal is an unambiguous codebase,
not a cemetery of `if False` branches.

**Out of cleanup scope**: `scripts/`, full `debug/` tree purge, `pynput`, entire
`virtual_keyboard.py` rewrite in one step.

### Evaluation module scope (minimal)

`gazekey/evaluation/` contains **only**:

| In scope | Out of scope |
|----------|--------------|
| `BenchmarkRunner` — run 15-key test, score hits | Multi-mapper comparison runners |
| `RunSummaryWriter` — console + one file record | Dashboards, HTML reports |
| `FailureAnalysis` — per-key dx/dy, row, miss list in summary | Replay engines, session diff UI |
| Pass/fail vs SC-001–004 | LOOCV-primary gating, geom debug overlays |

Reuse logic from `keyboard_accuracy.py`; do not duplicate `keyboard_accuracy_mapper_diag.py`
or compare tooling in the MVP module.

## Phase 0 & Phase 1 Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Research decisions | [research.md](./research.md) | Complete |
| Data model | [data-model.md](./data-model.md) | Complete |
| Contracts | [contracts/](./contracts/) | Complete |
| Quickstart | [quickstart.md](./quickstart.md) | Complete |

## Complexity Tracking

> No constitution violations requiring justification. One PCA4 mapper and one
> calibration layout in the active path at a time. Any post-fit layer requires
> benchmark evidence before inclusion (document in tasks if added).

## Implementation Phases (for `/speckit-tasks`)

1. **Geometry verification** — confirm layout inspector centers/hitboxes vs on-screen keys; align calibration targets and benchmark hit tests
2. **Foundation** — minimal `evaluation/` (benchmark + summary + failure fields); contract tests
3. **Baseline PCA4 run** — wire PCA4-only path end-to-end; run benchmark; **save baseline summary** before further changes
4. **Calibration UX** — minimal overlay (no camera preview on fixation); sanity-only pass/fail
5. **Preview** — read-only default post-calibration; camera preview hidden by default (CQ-4)
6. **Benchmark + failure analysis** — manual-start benchmark; per-key failure in summary; **analysis task** after each run
7. **Iterate** — one change per cycle (layout, collection, PCA4 fit); re-benchmark vs baseline; no mapper variant hunts
8. **Cleanup phase A** — disconnect legacy paths from user flow
9. **Cleanup phase B** — delete/archive unused code (dedicated tasks per removal) after active path proven
10. **Acceptance** — 3-session repeatability vs SC-001–SC-004 (CQ-1 thresholds)

Each iteration phase (7) MUST include: baseline comparison → failure analysis →
single change → re-benchmark → recorded outcome.

## Post-Design Constitution Re-check

All gates remain **pass**. PCA4 direction aligns with Principle III (simple pipeline
first). Result-driven iteration uses benchmark as the gate (Principle II).
