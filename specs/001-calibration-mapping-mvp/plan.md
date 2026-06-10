# Implementation Plan: Calibration & Gaze Mapping MVP

**Branch**: `001-calibration-mapping-mvp` | **Date**: 2026-06-10 (revised 4) | **Spec**: [spec.md](./spec.md)

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
5. **MVP user flow** — launch → calibrate → **preview-only** → optional **dev-flag** benchmark →
   pass/fail summary. Dwell/intent/typing disabled in the normal flow.
6. **Active-code cleanup & refactor (Phase 10)** — inventory every major module first;
   then isolate future interaction code, thin `virtual_keyboard.py`, and execute
   **approved** delete/archive tasks only (one task per removal; no blind deletion).
7. **Mapping experiments deferred** — Phase 8 accuracy/layout work stays **paused**
   until Phase 10 completes; resume with a cleaner active path.
8. **Minimal evaluation module** — thin benchmark + run summary + failure analysis only;
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
| **CQ-3** | **Preview-first**; benchmark **dev-flag only** (`GAZEKEY_DEV_BENCHMARK=1`) | After calibration pass → read-only preview; benchmark auto-starts only when dev flag set — no UI button |
| **CQ-4** | Camera preview behavior differs by mode | **Calibration/fixation**: optional, **hidden/off by default**; must not appear on top of or interfere with fixation overlay. **Post-calibration preview / normal UI**: preview window **available/open** as part of active system UI (user may close it) |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (GazeKey v1.2.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| Accuracy First | Scope limited to calibration/mapping; dwell/typing not optimized | ✅ |
| Measurable Progress | Benchmark key-hit, pixel error, row accuracy, repeatability in SC + plan | ✅ |
| Simple Pipeline | `tracking → features → calibration → mapping → preview → benchmark` | ✅ |
| Spec Before Code | spec.md approved; plan.md (this); tasks.md complete | ✅ |
| MVP Scope Control | No prediction, language, OS injection, personalization, multi-monitor | ✅ |
| Testable Architecture | Module boundaries defined below; orchestrator split planned | ✅ |
| Run Clarity | Reuse summary CSV + console; no artifact sprawl | ✅ |
| Documentation Hierarchy | Spec Kit docs are source of truth | ✅ |
| Targeted Cleanup | Phase 10: inventory-first cleanup + VK refactor; approved removals only | ✅ |
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

### Benchmark failure pattern → allowed fix (decision guide)

Use failure analysis (per-key `dx`/`dy`, row accuracy, miss clusters) to pick the
most likely fix area. Per-iteration sequencing (at most one change per cycle) is
enforced in `tasks.md` Phase 8 only.

| Failure pattern | Likely cause | Allowed fix area | Not allowed |
|-----------------|--------------|----------------------------------------|-------------|
| Wrong row on many keys; large consistent `dy` | Mapping Y scale/bias or calibration row coverage | PCA4 fit path (`ridge.py`, ridge α, feature smoothing) **or** calibration layout | Mapper variant swap; row_bias/local_y without analysis note |
| Keys correct row but wrong column; `dx` dominant | Horizontal mapping or geometry | Geometry/hitboxes **or** PCA4 fit (u features) **or** calibration layout | Multiple areas at once |
| Erratic per-key misses; preview also poor | Collection noise, head drift, fixation | Fixation/collection (`fixation_gate.py`, sample gates) | Layout change before collection stable |
| Preview OK but benchmark misses only | Hitbox/key center mismatch | Geometry/hitboxes (`layout_inspector.py`, `key_hit_tester.py`) | PCA4 refit before geometry verified |
| Accuracy varies wildly between targets | Dense calibration / head travel | Calibration layout (reduce to 9/13) | Adding post-fit layers |
| End-to-end flow cannot complete | Blocking bug, not mapping | **Flow fix only** (UI, crash, benchmark won't start) | Accuracy iteration (Phase 8) |

### Result-driven work discipline (required in `tasks.md`)

Every accuracy improvement cycle in `tasks.md` MUST follow this pattern:

```text
1. Baseline PCA4 run   — calibrate → preview → benchmark → save run summary
2. Failure analysis    — read per-key misses, row errors, dx/dy from summary
3. One focused change  — calibration, geometry, collection, or PCA4 fit only (see `tasks.md` Phase 8 for iteration sequencing)
4. Re-benchmark        — compare to baseline summary (improved / unchanged / worse)
```

**Baseline gate**: Phase 7 MUST complete end-to-end (calibrate → preview → manual
benchmark → saved summary). If the baseline run **cannot** finish, fix blocking
flow issues first (Phases 3–6, geometry, crashes, benchmark UI). **Do not** start
Phase 8 accuracy iterations until an end-to-end baseline exists.

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

### Targeted cleanup (three phases)

**Phase 9 — disconnect** (complete):

| Item | Action |
|------|--------|
| v1 calibration fallback | Unreachable from normal user flow |
| Dwell typing / intent / selection | Not invoked in MVP gaze loop |
| Placeholder suggestion bar, language toggle, symbols switch | Behavior disabled in MVP; regions stay visible/layout-reserved (no geometry shrink) |
| Experimental mappers | Not selectable at runtime |
| Multi-mode env toggles | Debug-only; not in user flow |
| Camera preview during calibration | Hidden/off by default; never on fixation overlay (CQ-4) |

**Phase 10 — active-code cleanup & architecture refactor** (see dedicated section below):

Inventory first; plan second; implement only after user approves the cleanup plan.
Goals: clear active MVP path, isolate future interaction code, thin orchestrator —
**not** a broad redesign or mass deletion.

**Phase 10+ — approved removals** (after inventory + plan + approval):

Each delete/archive/move = **one dedicated approved task** (constitution IX).
Uncertain items stay `investigate` until resolved — never blind deletion.

#### Definition: “active PCA4 path proven”

All of the following MUST be true before Phase 10 execution (delete/archive/refactor):

1. **End-to-end baseline completed** — Phase 7 saved summary in `runs/`
2. **Single reachable user flow** — calibrate (v2) → preview (read-only) → dev-flag benchmark (`GAZEKEY_DEV_BENCHMARK=1`); PCA4 only; no v1/experimental mapper in path
3. **Flow stability** — three consecutive manual runs complete without crash or blocked step (calibration pass → preview → benchmark finish)
4. **Documented failure analysis** — at least one benchmark produced per-key failure detail in run summary

Accuracy targets (SC-001–SC-004) do **not** need to be met for Phase 10 —
proven *flow* and *path*, not final accuracy, unlock cleanup/refactor work.

**Explicitly out of Phase 10 delete scope**:

- `scripts/` — offline dev tooling; keep
- Full `gazekey/debug/` purge — keep; disconnect from active import chain only if plan approves
- Dwell / intent / selection — **preserve**; isolate from active path, do not delete
- `keyboard_full9` / `keyboard_wide9` — keep behind `GAZEKEY_CALIB_MODE` for deferred layout experiments
- Mapping accuracy parameters — no α, row-Y, local-Y, X correction, or smoothing changes during cleanup/refactor

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

## Phase 10: Active-Code Cleanup & Architecture Refactor

**Purpose**: Before resuming Phase 8 mapping experiments, make the active MVP path
obvious, maintainable, and free of mixed legacy/experimental/future code in the
orchestrator. **Inventory and plan first; implement only after user approval.**

**Not in scope**: Accuracy tuning, layout A/B runs, mapper variant changes, or a
larger architectural redesign. Simplify the **existing** structure only.

### Step 1 — Full cleanup inventory (mandatory before any deletion)

Scan the repository and classify every major folder/file. Output:
`specs/001-calibration-mapping-mvp/cleanup-inventory.md`.

| Classification | Meaning |
|----------------|---------|
| **Active MVP path** | Required for calibrate → PCA4 mapping → read-only preview → dev benchmark |
| **Future interaction** | Not active now; preserve for later (dwell, intent, selection, gaze typing) |
| **Debug/offline tooling** | Developer-only; not reachable from normal user flow |
| **Legacy/replaced** | Superseded by calibration2 / PCA4 / evaluation; archive/delete candidate |
| **Unknown** | Needs investigation — **no delete/move until resolved** |

Each inventory row MUST document:

| Field | Content |
|-------|---------|
| `path` | File or directory |
| `purpose` | Apparent role from code + imports |
| `mvp_imported` | Yes/No — imported (directly or transitively) by active MVP path from `main.py` |
| `tests_depend` | Test files that import or exercise this path |
| `recommendation` | `keep` / `disconnect` / `archive` / `delete` / `investigate` |
| `removal_risk` | What breaks or is lost if removed without further work |

**Seed inventory** (to be verified and extended during T042 — not pre-judged):

| Path | Likely class | Notes |
|------|--------------|-------|
| `main.py` | Active MVP | Entry point |
| `gazekey/tracking/` | Active MVP | MediaPipe pipeline |
| `gazekey/features/` | Active MVP | FrameFeatures, smoother |
| `gazekey/layout/` | Active MVP | Key geometry |
| `gazekey/calibration2/` | Active MVP | Sole active calibration path |
| `gazekey/mapping/ridge.py`, `typing_candidate.py`, `base.py` | Active MVP | PCA4 fit/predict |
| `gazekey/mapping/row_bias.py`, `local_y_correction.py`, `idw_*.py`, `row_aware.py` | Legacy/dormant or investigate | Not in active MVP path unless benchmark adopts |
| `gazekey/evaluation/` (benchmark, summary, failure) | Active MVP | Thin evaluation layer |
| `gazekey/evaluation/benchmark_diagnostics.py`, `coverage_diagnostics.py` | Debug/offline | Dev diagnostics; verify import chain |
| `gazekey/ui/virtual_keyboard.py` | Active MVP (refactor target) | Mixed orchestrator — split in Step 3 |
| `gazekey/ui/calibration_controller.py`, `gaze_preview.py`, `calibration_overlay.py`, `camera_preview_window.py` | Active MVP | Already extracted boundaries |
| `gazekey/calibration/` (v1) | Legacy/replaced | Superseded by calibration2 |
| `gazekey/intent/`, `gazekey/selection/` | Future interaction | Preserve; isolate |
| `gazekey/typing/` (gaze path: dwell, gaze_typing_controller, gaze_ui_mapper) | Future interaction + partial MVP | `TextBuffer` / `key_hit_tester` active; gaze typing dormant |
| `gazekey/debug/` | Debug/offline | Benchmark source, mapper compare, runtime logs |
| `gazekey/mvp_log.py` | Active MVP | Quiet logging |
| `scripts/` | Debug/offline | Offline analysis; not in user flow |
| `tests/` | Active MVP support | Must map test → module dependencies in inventory |

### Step 2 — Cleanup plan + approval gate

From the inventory, produce `specs/001-calibration-mapping-mvp/cleanup-plan.md` listing
**exactly** what will be kept, archived, deleted, moved aside as future code, or
refactored. Rules:

- **No blind deletion** — anything uncertain stays `investigate` with a follow-up task
- **One approved task per deletion or archive** — add task IDs to `tasks.md` when plan is approved
- **Future interaction preserved** — dwell/intent/selection/gaze-typing move to an isolated
  package or facade (e.g. `gazekey/future/` or explicit `gazekey/interaction/`) so
  `VirtualKeyboard` does not import scoring/dwell in the active MVP path
- **Layout experiments preserved** — `keyboard_full9`, `keyboard_wide9` remain in
  `targets.py` behind `GAZEKEY_CALIB_MODE`; no deletion

**User approval required** (T045) before T046+ execution.

### Step 3 — `virtual_keyboard.py` refactor (incremental, same behavior)

`gazekey/ui/virtual_keyboard.py` (~2900 lines) currently mixes UI layout, calibration
finish/mapper fit, preview, benchmark, env flags, debug keyboard-accuracy paths, and
dormant gaze-typing/intent wiring. Goal: **thin orchestrator** that wires controllers.

Already extracted: `CalibrationController`, `GazePreviewController`.

Planned extractions (one task each; preserve behavior):

| New module | Responsibility moved from `VirtualKeyboard` |
|------------|---------------------------------------------|
| `gazekey/ui/keyboard_layout.py` | Widget creation: control bar, letter/symbol rows, text display, suggestion bar placeholders, minimized view, key styles |
| `gazekey/ui/benchmark_controller.py` | MVP dev benchmark + optional debug keyboard-accuracy session; banner/highlight; diagnostics writes |
| `gazekey/ui/mapper_runtime.py` | Post-calibration mapper fit orchestration, predict/clamp helpers, mapper store access |
| `gazekey/ui/gaze_loop.py` | `_on_eye_data_main_thread` dispatch: preview vs dormant typing; tracking bridge callbacks |
| `gazekey/ui/env_flags.py` | `GAZEKEY_VERBOSE`, `GAZEKEY_DEV_BENCHMARK`, `GAZEKEY_CALIB_MODE`, and related reads |

After extraction, `VirtualKeyboard` retains: window lifecycle, wiring controllers,
mouse-click typing (`TextBuffer`), and high-level mode state — not mapping math or
benchmark scoring.

Refactor constraints (behavior preservation gate — T056):

- No alpha, row-Y bias, local-Y, X correction, or feature-smoothing changes
- No calibration layout default change (`keyboard15` stays default)
- No benchmark pass/fail threshold changes
- T028 integration test and T029 baseline metrics must match pre-refactor (within normal run variance)

### Step 4 — Execute approved cleanup items

Only items marked `archive`, `delete`, `disconnect`, or `move` in the **approved**
cleanup plan. Representative expected actions (final list comes from inventory):

| Action | Example | Rule |
|--------|---------|------|
| Archive | `gazekey/calibration/` v1 package | Move to `archive/calibration_v1/` if tests allow |
| Disconnect | Debug imports in active path | `keyboard_accuracy_compare`, `mapper_diag` via dev-only entry |
| Move aside | Dwell/intent/selection gaze wiring | Isolated module; not imported in MVP gaze loop |
| Keep | `scripts/`, `gazekey/debug/`, layout candidates | Reachable only via env flags or CLI |
| Investigate | Any module with unclear MVP test linkage | Resolve before delete |

### Phase 8 resume (after Phase 10)

Phase 8 accuracy/layout experiments remain **paused** until Phase 10 completes
(inventory → plan approval → refactor → approved cleanup → behavior gate T056).
Then resume T032–T035 per failure-pattern guide. Layout comparison (`keyboard_full9`
vs `keyboard_wide9` vs `keyboard15`) runs in Phase 8, not Phase 10.

## Implementation Phases (for `/speckit-tasks`)

1. **Geometry verification** — confirm layout inspector centers/hitboxes vs on-screen keys; align calibration targets and benchmark hit tests
2. **Foundation** — minimal `evaluation/` (benchmark + summary + failure fields); contract tests
3. **Baseline PCA4 run** — wire PCA4-only path end-to-end; run benchmark; **save baseline summary**; if blocked, fix flow before iteration
4. **Calibration UX** — minimal overlay (no camera preview on fixation); sanity-only pass/fail
5. **Preview** — read-only default post-calibration; camera preview **open/available** in normal UI (CQ-4); hidden during calibration only
6. **Benchmark + failure analysis** — dev-flag benchmark; per-key failure in summary; **analysis task** after each run
7. **Iterate (PAUSED)** — result-driven accuracy work; **resume after Phase 10**
8. **Disconnect (Phase 9)** — legacy paths unreachable from user flow ✅
9. **Active-code cleanup & refactor (Phase 10)** — inventory → plan → approval → refactor VK → approved removals → behavior gate
10. **Resume iteration (Phase 8)** — mapping/layout experiments with clean active path
11. **Acceptance** — 3-session repeatability vs SC-001–SC-004 (CQ-1 thresholds)

## Post-Design Constitution Re-check

All gates remain **pass**. PCA4 direction aligns with Principle III (simple pipeline
first). Result-driven iteration uses benchmark as the gate (Principle II).
