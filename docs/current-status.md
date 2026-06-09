# GazeKey — Current Project Status

**Document purpose:** Evidence-based snapshot of the repository before a Spec Kit–driven redesign.  
**Date:** 2026-06-09  
**Scope:** Inspection only — no implementation changes implied.

---

## Executive summary

GazeKey is a **PySide6 desktop app** that runs a transparent virtual keyboard, captures webcam frames, extracts eye features with **MediaPipe Face Landmarker**, calibrates gaze-to-screen mapping, and attempts **dwell-based key selection** inside the app. The codebase has grown substantially beyond what `README.md` describes: calibration v2, ridge regression mappers, intent scoring, and extensive debug tooling are all present.

The **primary blocker** is reliability. Archived calibration sessions show **15-key benchmark accuracy between 20% and 60%** (best: 9/15 keys correct), with high session-to-session variance. Calibration quality gates and LOOCV metrics do not reliably predict real key-hit accuracy. The runtime path is powerful but **monolithic, layered, and difficult to reason about** — a clean spec-driven MVP focused on calibration and mapping is warranted.

---

## 1. Current implemented components

Evidence is drawn from `main.py`, `gazekey/`, `tests/`, `runs/`, `CURRENT_PIPELINE.md`, and `TYPING_CANDIDATE.md`.

### 1.1 Application shell and UI

| Component | Location | Status |
|-----------|----------|--------|
| Entry point | `main.py` | Launches `VirtualKeyboard` via PySide6 |
| Virtual keyboard | `gazekey/ui/virtual_keyboard.py` (~2,900 lines) | Frameless, draggable, always-on-top QWERTY + symbols layout; shift; minimize/restore; internal `QLineEdit` text buffer |
| Camera preview | `gazekey/ui/camera_preview_window.py` | Separate floating preview window |
| Calibration overlay | `gazekey/ui/calibration_overlay.py` | Fullscreen fixation dots during calibration |
| Geometry debug overlay | `gazekey/ui/calibration_geometry_overlay.py` | Optional train/LOOCV point visualization (`GAZEKEY_CALIB_GEOM_DEBUG`) |
| Suggestion bar | `virtual_keyboard.py` | **UI placeholder only** (`word1`, `word2`, `word3`; prints TODO on click) |
| Language toggle | `virtual_keyboard.py` | **Cosmetic only** — toggles EN/עב label; no layout or typing change |

Mouse click on keys works and updates the in-app text buffer via `TextBufferController`. Gaze dwell activation is wired separately through `_on_gaze_activate_key`.

### 1.2 Tracking pipeline

| Component | Location | Status |
|-----------|----------|--------|
| Webcam capture | `gazekey/tracking/video_capture.py` | OpenCV, 640×480 |
| Background tracking loop | `gazekey/tracking/tracking_manager.py` | ~30 FPS thread |
| Eye/iris detection | `gazekey/tracking/eye_detector.py` | MediaPipe Face Landmarker; blink flag; 16-point eye contours + iris centers per eye |
| Thread bridge | `gazekey/calibration/tracking_bridge.py` | Qt signal from worker → main thread |

### 1.3 Feature extraction

| Component | Location | Status |
|-----------|----------|--------|
| Frame features | `gazekey/features/extractor.py` | Eye-local `(u, v)` per eye, averaged ratios `avg_h`/`avg_v`, PCA eye-local `pca_uL/vL/uR/vR`, face center proxy, eye box size |
| Feature smoothing | `gazekey/features/feature_smoother.py` | `PcaFeatureSmoother` (EMA α = 0.28 at runtime) |
| Polynomial features | `gazekey/features/poly_features.py` | 12D poly features for alternate mappers |
| Vertical decoupling | `gazekey/features/vertical_decouple.py` | Residualize v on u at fit time (decoupled mapper path) |

### 1.4 Calibration (active path: v2)

| Component | Location | Status |
|-----------|----------|--------|
| **Active session** | `gazekey/calibration2/session.py` | 15-target `keyboard15` flow (default); fixation gate; per-target sample collection; CSV logging |
| Fixation gating | `gazekey/calibration2/fixation_gate.py` | Lock-on (~420 ms) before samples count; head-drift limits |
| Target geometry | `gazekey/calibration2/targets.py` | Key-aligned points on letter region; optional `fullscreen9`, `keyboard13`, legacy grids |
| Quality / outliers | `gazekey/calibration2/quality.py`, `outliers.py`, `region_quality.py` | LOOCV gates, monotonicity, region accuracy, head-drift checks |
| Persistence | `gazekey/calibration2/mapper_store.py` | Writes `calibration_v2.json` (version 7) — **not loaded on startup** |
| CSV artifacts | `gazekey/calibration2/calibration_csv.py` | `calibration_samples.csv`, `calibration_summary.csv` |

**Startup behavior** (`virtual_keyboard.py`): calibration is **required every launch**; saved JSON is inspection-only.

### 1.5 Calibration (legacy path: v1)

| Component | Location | Status |
|-----------|----------|--------|
| 5-point IDW calibration | `gazekey/calibration/` | Documented in `gazekey/calibration/README.md`; `calibration_v1.json` |
| Affine mapper | `gazekey/calibration/affine_mapper.py` | Legacy load path |

Per `CURRENT_PIPELINE.md`, v1 is a **fallback** when v2 mapper is absent. The active app path uses v2 exclusively after successful calibration.

### 1.6 Gaze mapping

| Component | Location | Status |
|-----------|----------|--------|
| **Frozen typing mapper** | `gazekey/mapping/typing_candidate.py` | `pca4_baseline_v1`: ridge on PCA u/v features |
| Mapper fit | `gazekey/mapping/ridge.py` | `fit_calibration_mapper()` — multi-candidate ranking **disabled**; only `pca4_baseline` fitted |
| Post-fit corrections | `row_bias.py`, `local_y_correction.py` | Per-row Y offset + X-interpolated local Y residual |
| Alternate mappers (inactive) | `poly12` variants, `pca4_decoupled_split`, `idw_ratio.py`, `idw_local.py`, `row_aware.py` | Present in code; not selected on default path |
| Layout geometry | `gazekey/layout/layout_inspector.py`, `layout_csv.py` | Key centers/rows for targets and scoring; exports `keyboard_layout.csv` |

### 1.7 Runtime gaze-to-key selection

| Component | Location | Status |
|-----------|----------|--------|
| Screen-coordinate smoothing | `gazekey/typing/gaze_smoother.py` | EMA α = 0.35 |
| Intent scoring | `gazekey/intent/scoring.py` | Anisotropic Gaussian; row stickiness; cross-row penalty |
| Selection policy | `gazekey/selection/policy.py` | Hysteresis + dwell (~1.25 s); stronger cross-row switch margins |
| Dwell / hit test | `dwell_selector.py`, `key_hit_tester.py`, `gaze_typing_controller.py` | Focus feedback and activation |
| Preview mode | `virtual_keyboard.py` | Gaze dot without key activation |
| Runtime logging | `gazekey/debug/runtime_key_confidence_logger.py` | `runtime_key_confidence.csv` |

### 1.8 Debug, analysis, and tests

| Asset | Location | Status |
|-------|----------|--------|
| Pipeline documentation | `CURRENT_PIPELINE.md` | Accurate runtime flow description |
| Frozen config rationale | `TYPING_CANDIDATE.md` | Session benchmarks and design decisions |
| Keyboard accuracy benchmark | `gazekey/debug/keyboard_accuracy.py` | 15-key post-calibration eval (opt-in via env) |
| Mapper diagnostics | `keyboard_accuracy_mapper_diag.py`, `keyboard_accuracy_compare.py` | Multi-mapper replay and layer ablation |
| Archived sessions | `runs/session_01` … `runs/‏‏session_06` | Logs + `key_accuracy_compare.csv` per session |
| Analysis scripts | `scripts/analyze_*.py`, `camera_*.py`, `eye_landmarker_demo.py` | Offline calibration analysis and camera demos |
| Unit tests | `tests/` | **61 tests** (calibration, mapping, quality gates, typing helpers) |
| Prior spec artifact | `docs/GazeKey_Project_Specification.pdf` | Pre–Spec Kit specification (not integrated with `.specify/`) |

### 1.9 Dependencies and infrastructure

- **Stack:** Python 3.8+, PySide6, OpenCV, MediaPipe, NumPy (`requirements.txt`).
- **`pynput`** is listed in `requirements.txt` and `README.md` but **no Python module imports or uses it** — OS-level typing injection is **not implemented**.
- **Spec Kit scaffolding** exists (`.specify/`, `.cursor/skills/speckit-*`) but `.specify/memory/constitution.md` is still a template placeholder.
- **`README.md` is outdated** — still describes Phase 1–3 roadmap items (5-point calibration, pynput injection) as future work despite substantial v2 implementation.

---

## 2. Current known problems

### 2.1 Mapping accuracy is insufficient for reliable typing

From `TYPING_CANDIDATE.md` and `runs/*/key_accuracy_compare.csv` (frozen `pca4_baseline`, 15 sample keys):

| Session | Quality gates | Key accuracy | Mean error |
|---------|---------------|--------------|------------|
| 01 | FAILED | 3/15 (20%) | 110.9 px |
| 02 | PASSED | 5/15 (33%) | 76.9 px |
| 03 | FAILED | 4/15 (27%) | 114.7 px |
| 04 | PASSED | **9/15 (60%)** | 46.9 px |
| 05 | PASSED | 5/15 (33%) | 79.6 px |
| 06 | PASSED | 4/15 (27%) | 112.1 px |

**Observations from data and code:**

- **LOOCV RMS does not predict key accuracy.** Session 05 had the best LOOCV (~45.7 px) but only 5/15 correct keys.
- **Systematic Y bias:** many failing keys show large negative `dy` (e.g. bottom row predicted ~100–170 px too high in session 06), indicating row-level mapping failure despite row-bias and local-Y correction layers.
- **Gates can pass with poor usability:** sessions 02, 05, 06 passed region/LOOCV gates but achieved ≤33% key accuracy.
- **u–v coupling** (`corr(v_mean, u_mean)` often 0.55–0.85 per `CURRENT_PIPELINE.md`) causes within-row tilt; multiple mitigation layers were added rather than resolving the root representation issue.

### 2.2 Instability and poor debuggability

- **`virtual_keyboard.py` is a ~2,900-line orchestrator** mixing UI, calibration lifecycle, mapper fit, runtime gaze loop, debug hooks, and env-var toggles. Hard to isolate whether errors come from features, fit, corrections, intent scoring, or selection.
- **Many overlapping code paths:** calibration v1 + v2; 6+ mapper types; frozen config atop disabled multi-candidate ranking; runtime intent/hysteresis stacked on top of mapper corrections.
- **Calibration not persisted for use:** user must recalibrate every launch, yet saved JSON is not loaded — slows iteration and obscures whether drift is session or model error.
- **Debug tooling is powerful but opt-in and scattered:** numerous `GAZEKEY_*` env vars; CSV artifacts at repo root (gitignored); no single “health dashboard” or pass/fail contract tied to user-visible key hits.
- **Documentation drift:** `README.md` contradicts `CURRENT_PIPELINE.md` and actual behavior, increasing onboarding and planning risk.

### 2.3 Calibration collection fragility

- Session logs (`runs/*/logs.txt`) show long `WAIT_LOCK` periods and large jumps in `avg_h`/`avg_v` between targets — head movement between dots affects feature means.
- Head-drift gates exist (`CALIB_HEAD_DRIFT_*`, `MAX_HEAD_DRIFT_EYE_H` in `typing_candidate.py`) but 2/6 archived sessions still failed gates; passed sessions remain inaccurate on key benchmark.
- Fixation collection uses time-based lock (~420 ms) rather than explicit quality feedback to the user during each target.

### 2.4 Scope creep in the runtime stack

Dwell typing, intent scoring, cross-row hysteresis, preview mode, and in-app text buffer are all implemented — but **mapping error dominates**, so tuning selection/dwell cannot deliver a reliable MVP. The stack optimizes for typing experiments before mapping is trustworthy.

---

## 3. What should be kept

These parts are proven, reusable, and aligned with the next-phase goal:

| Area | Rationale |
|------|-----------|
| **MediaPipe + OpenCV tracking pipeline** | Stable detection; background thread pattern works; `EyeData` contract is clear |
| **`TrackingBridge` thread boundary** | Correct Qt threading model |
| **Virtual keyboard UI shell** | Layout, transparency, drag, minimize, symbols toggle — good host for calibration targets and preview |
| **Keyboard layout inspection** | `inspect_keyboard_layout()` provides real key centers needed for keyboard-aligned calibration |
| **Calibration overlay concept** | Fullscreen dots + fixation workflow is the right UX pattern; implementation may be simplified |
| **Benchmark and logging infrastructure** | `keyboard_accuracy` eval, `runs/` session archives, CSV artifacts — essential for measuring redesign progress |
| **Unit test foundation** | 61 tests around calibration quality, mapping, geometry — extend with MVP acceptance tests |
| **`CURRENT_PIPELINE.md` / `TYPING_CANDIDATE.md`** | Honest internal record of what was tried; input for spec clarifications |
| **Analysis scripts** | Useful for offline diagnosis during redesign |
| **Spec Kit scaffolding** | `.specify/` templates and skills ready for structured replanning |

---

## 4. What should be redesigned

| Area | Why redesign |
|------|--------------|
| **Gaze feature representation** | u–v coupling and row tilt persist across mapper variants; PCA + correction layers are compensating rather than fixing |
| **Calibration → fit → validate pipeline** | Too many stages, gates, and wrappers; validation metrics misaligned with key-hit accuracy |
| **Mapper architecture** | Frozen `pca4_baseline` + row bias + local Y + region gates + intent scoring is hard to test in isolation; inactive alternatives add noise |
| **Application architecture** | Monolithic `VirtualKeyboard` should split into: tracking, calibration, mapping, evaluation, minimal typing feedback |
| **Success criteria and quality gates** | Replace LOOCV-primary gates with **key-hit accuracy** and repeatable benchmarks as the acceptance contract |
| **Persistence model** | Decide explicitly: load calibration on startup vs always recalibrate; current write-only JSON wastes user effort |
| **Calibration target strategy** | Evaluate whether `keyboard15` density helps or adds noise; consider simpler provable layouts for MVP |
| **Runtime selection stack** | Defer tuning intent/hysteresis/dwell until gaze point lands consistently on intended keys in preview |
| **Documentation** | Replace outdated `README.md` roadmap with Spec Kit–generated spec/plan as source of truth |

**Legacy v1 calibration** (`gazekey/calibration/`) should be treated as **deprecated reference**, not extended — the redesign should not fork another parallel path.

---

## 5. What should be postponed

Explicitly out of scope for the calibration/mapping MVP (matches user direction; confirmed absent or stub-only in code):

| Feature | Evidence |
|---------|----------|
| **Predictive text / auto-complete** | Suggestion bar is placeholder; `on_suggestion_clicked` prints TODO |
| **Multi-language support** | Language button only swaps label text |
| **External OS typing injection** | `pynput` in requirements but unused; `TextBufferController` only writes to `QLineEdit` |
| **Advanced personalization** | No settings panel; thresholds live in code/env vars |
| **Full accessibility polish** | No screen reader, high-contrast themes, or configurable motor accommodations |
| **Word prediction engine** | Listed in README future work only |
| **Multi-monitor support** | Not implemented; single-screen geometry assumed |
| **Blink-to-select / scanning keyboards** | Explicitly excluded in v1 calibration README |

**Dwell-based activation** may remain as a **minimal in-app feedback mechanism** for MVP validation, but should not be optimized until mapping accuracy meets a defined threshold.

---

## 6. Proposed clean MVP scope

**Mission:** A user can calibrate once (or per session, by explicit policy), see a gaze preview dot land on the intended key, and hit ≥N of 15 benchmark keys correctly in a repeatable test — **without** OS injection or advanced typing features.

### 6.1 In scope

1. **Webcam eye tracking** — reuse existing MediaPipe pipeline.
2. **Virtual keyboard UI** — reuse shell; show calibration targets on real key positions.
3. **Calibration flow** — collect gaze features at known screen points with clear user feedback; spec should define target count, fixation rules, and failure UX.
4. **Gaze-to-screen mapping** — one well-specified model (not a stack of frozen mapper + N correction layers); measurable train and hold-out error.
5. **Preview mode** — show mapped gaze position over keyboard (already exists; make it the primary validation UI).
6. **Objective acceptance test** — automated 15-key (or spec-defined) benchmark with **minimum accuracy target** (to be set in spec; current best is 60%).
7. **Debug artifacts** — structured logs/CSV for every calibration and benchmark run.

### 6.2 Out of scope (MVP)

- Dwell typing polish, intent scoring tuning, cross-row hysteresis optimization
- In-app sentence typing UX beyond minimal “did we hit the right key?”
- OS-level key injection
- Language switching, suggestions, personalization

### 6.3 Proposed MVP success metrics (for spec to finalize)

| Metric | Current baseline | MVP target (draft — set in spec) |
|--------|------------------|----------------------------------|
| 15-key benchmark accuracy | 20–60% | TBD (e.g. ≥80% same session, ≥70% across 3 sessions) |
| Median key error (px) | 47–112 px on passing sessions | TBD (e.g. < half key height ≈ 34 px) |
| Calibration pass rate | 4/6 sessions passed gates | TBD |
| Session-to-session variance | High | Low — spec should define max spread |

### 6.4 Suggested MVP user flow

```
Launch → Start camera → Calibrate (N points) → Quality result shown
  → Preview gaze dot on keyboard → Run benchmark (optional/auto)
  → Pass: enable minimal key-hit test | Fail: clear reason + recalibrate
```

---

## 7. Risks and open questions

### 7.1 Technical risks

| Risk | Detail |
|------|--------|
| **Webcam gaze ceiling** | Consumer webcam + head-fixed assumption may not reach desired accuracy without head-pose normalization or hardware guidance |
| **Feature space limits** | Eye-local ratios may be insufficient for fine key discrimination on a full QWERTY row |
| **Overfitting to one user/setup** | Six archived sessions may reflect one environment; spec should require multi-session validation |
| **Regression during rewrite** | Replacing layered stack risks losing best-case session 04 (60%) unless benchmarks guard regressions |

### 7.2 Open questions (for `speckit-clarify`)

1. **What key-hit accuracy is “reliable enough” for MVP?** (Per-key? Per-row? Worst-case key?)
2. **Should calibration persist across launches** once quality passes, or always recalibrate?
3. **Is the MVP keyboard the full QWERTY letter region** or a reduced layout (e.g. 3×3 grid) for initial proof?
4. **Single user / fixed setup** or must it generalize across distance, lighting, and glasses?
5. **Head movement policy:** strict head-fixed vs allow small head correction?
6. **Acceptable calibration duration** (15 points × ~3 s ≈ 45+ s today)?
7. **Primary platform** — Windows only (current dev environment) or cross-platform from day one?
8. **Relationship to `docs/GazeKey_Project_Specification.pdf`** — supersede entirely or mine requirements?

---

## 8. Recommended next Spec Kit steps

Spec Kit is initialized (`.specify/`, skills under `.cursor/skills/speckit-*`) but the constitution is still a template. Recommended order:

| Step | Skill / command | Purpose |
|------|-----------------|---------|
| 1 | **`speckit-constitution`** | Define non-negotiables: accuracy-first, measurable gates, simplicity, test-backed changes, deprecate layered compensations without evidence |
| 2 | **`speckit-specify`** | Write the MVP feature spec: calibration + mapping + preview + benchmark only; reference this status doc and `TYPING_CANDIDATE.md` evidence |
| 3 | **`speckit-clarify`** | Resolve open questions in §7.2; encode answers into the spec |
| 4 | **`speckit-checklist`** | Generate acceptance checklist (calibration UX, benchmark procedure, artifact outputs) |
| 5 | **`speckit-plan`** | Technical plan: module boundaries, feature model choice, gate redesign, what to retire from v1/v2 |
| 6 | **`speckit-tasks`** | Dependency-ordered `tasks.md` for implementation |
| 7 | **`speckit-analyze`** | Cross-check spec ↔ plan ↔ tasks for gaps before coding |
| 8 | **`speckit-implement`** | Execute tasks (only after user approves plan) |

### Suggested feature branch naming

Use `speckit-git-feature` when starting spec work (e.g. `001-calibration-mapping-mvp`).

### Artifacts to produce in `specs/` (or project convention)

- `spec.md` — MVP requirements and acceptance criteria
- `plan.md` — architecture and migration from current stack
- `tasks.md` — implementation checklist
- Updated `constitution.md` — project principles

### Evidence to attach during specify/plan

- This document (`docs/current-status.md`)
- `TYPING_CANDIDATE.md` session table
- `runs/‏‏session_04/key_accuracy_compare.csv` (best case) and `runs/‏‏session_06/key_accuracy_compare.csv` (passing gate, poor accuracy)
- `CURRENT_PIPELINE.md` (as-built reference to retire or simplify)

---

## Appendix A — Repository map (high level)

```
main.py
gazekey/
  ui/           Virtual keyboard, overlays, camera preview
  tracking/     OpenCV + MediaPipe
  features/     Eye feature extraction and smoothing
  calibration/  Legacy v1 (5-point IDW)
  calibration2/ Active v2 session, gates, CSV, quality
  mapping/      Ridge mappers, corrections, frozen typing candidate
  intent/       Key intent scoring
  selection/    Hysteresis + dwell policy
  typing/       Dwell, hit test, in-app text buffer
  layout/       Key geometry
  debug/        Accuracy benchmarks and runtime logging
tests/          61 unit tests
scripts/        Analysis and camera demos
runs/           6 archived calibration sessions
docs/           Prior PDF spec, MediaPipe diagram, this status doc
.specify/       Spec Kit templates (constitution not yet ratified)
```

## Appendix B — Documentation accuracy note

| Document | Trust level |
|----------|-------------|
| `CURRENT_PIPELINE.md` | High — matches code |
| `TYPING_CANDIDATE.md` | High — matches `runs/` data |
| `gazekey/calibration/README.md` | Medium — accurate for **v1 only** |
| `README.md` | **Low** — predates v2; do not use for planning |

---

*Generated from repository inspection. No code was modified.*
