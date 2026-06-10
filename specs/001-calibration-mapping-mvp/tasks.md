# Tasks: Calibration & Gaze Mapping MVP

**Input**: `specs/001-calibration-mapping-mvp/` (spec.md, plan.md, research.md, contracts/)

**Prerequisites**: spec.md and plan.md approved; constitution v1.2.0

**Organization**: Phases follow plan implementation order. User-story labels map to spec.md US1–US4.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

**Purpose**: Confirm feature branch context and evaluation module scaffold.

- [x] T001 Confirm feature branch `001-calibration-mapping-mvp` and feature dir `specs/001-calibration-mapping-mvp/`
- [x] T002 [P] Create `gazekey/evaluation/` package with `__init__.py`

---

## Phase 2: Foundational (blocking)

**Purpose**: Geometry verification, minimal evaluation module, PCA4-only active path. **No user story work until this phase completes.**

- [x] T003 Verify key centers and hitboxes in `gazekey/layout/layout_inspector.py` match on-screen keys; document any offset in `runs/geometry_check.txt` (FR-024)
- [x] T004 [P] Add unit test that calibration targets from `gazekey/calibration2/targets.py` use same layout snapshot as `inspect_keyboard_layout()` in `tests/unit/test_layout_geometry.py`
- [x] T005 [P] Implement `gazekey/evaluation/run_summary.py` — console + one lightweight file record per run (contracts/run-summary.md)
- [x] T006 [P] Implement `gazekey/evaluation/failure_analysis.py` — format per-key miss list, dx/dy, row errors into summary text (FR-023)
- [x] T007 Extract benchmark scoring from `gazekey/debug/keyboard_accuracy.py` into `gazekey/evaluation/benchmark_runner.py` using `gazekey/typing/key_hit_tester.py` (15 keys: `DEFAULT_SAMPLE_KEYS`)
- [x] T008 Wire `fit_calibration_mapper()` in `gazekey/mapping/ridge.py` to **PCA4 only** — disable multi-candidate ranking in active path; config in `gazekey/mapping/typing_candidate.py` (FR-007)
- [x] T009 Disconnect v1 calibration fallback from `gazekey/ui/virtual_keyboard.py` normal flow (cleanup Phase A, FR-001)
- [x] T010 [P] Add `tests/unit/test_evaluation_summary.py` for pass/fail formatting and SC-001–004 threshold checks

**Checkpoint**: Geometry verified; evaluation module minimal (no mapper-compare tooling); PCA4-only fit path reachable.

---

## Phase 3: User Story 1 — Distraction-Free Calibration (P1)

**Goal**: Minimal fixation UI; per-session calibration; camera preview off during fixation (CQ-4).

**Independent test**: Complete calibration; dot + progress only on overlay; pass/fail after session; no camera window on fixation overlay.

- [x] T011 [US1] Strip debug/metrics text from `gazekey/ui/calibration_overlay.py` during fixation (FR-003, FR-004, SC-006)
- [x] T012 [US1] Ensure `gazekey/calibration2/session.py` reports pass/fail only after session ends; LOOCV supplementary in summary only (FR-005, FR-009)
- [x] T013 [US1] Hide floating camera preview in `gazekey/ui/camera_preview_window.py` during calibration; default off; never z-order above fixation overlay (FR-006a, CQ-4)
- [x] T014 [US1] Require calibration at app start before preview/benchmark in `gazekey/ui/virtual_keyboard.py` (FR-006, CQ-2)
- [x] T015 [US1] Write calibration run summary via `gazekey/evaluation/run_summary.py` from `gazekey/calibration2/calibration_csv.py` / session finish path (FR-014)
- [x] T016 [US1] Extract minimal `CalibrationController` boundary from `gazekey/ui/virtual_keyboard.py` — start/finish session, pass/fail callback, summary trigger; keep full app orchestration in `virtual_keyboard.py` (FR-017)

**Checkpoint**: US1 independently testable.

---

## Phase 4: User Story 2 — Read-Only Gaze Preview (P2)

**Goal**: Gaze dot on keyboard; no key activation; camera preview available post-calibration (CQ-4).

**Independent test**: After calibration, preview tracks gaze; text buffer unchanged; camera preview open in normal UI.

- [x] T017 [P] [US2] Extract read-only preview dot logic into `gazekey/ui/gaze_preview.py` from `gazekey/ui/virtual_keyboard.py`
- [x] T018 [US2] Default to preview mode after calibration pass; disable dwell typing / intent / selection in MVP gaze loop in `gazekey/ui/virtual_keyboard.py` (FR-008, FR-021, SC-007)
- [x] T019 [US2] Show camera preview window after calibration completes (user may close); not shown during fixation (FR-006a, CQ-4)
- [x] T020 [P] [US2] Add test in `tests/unit/test_preview_readonly.py` — gaze on key does not update text buffer (SC-007)

**Checkpoint**: US2 independently testable.

---

## Phase 5: User Story 3 — Manual Benchmark (P3)

**Goal**: User-initiated 15-key benchmark; pass/fail vs CQ-1 thresholds; failure analysis after each run.

**Independent test**: Dev-flag benchmark (`GAZEKEY_DEV_BENCHMARK=1`) auto-starts after preview; summary shows key-hit, row accuracy, median error, pass/fail.

- [x] T021 [US3] Dev-only benchmark trigger (`GAZEKEY_DEV_BENCHMARK=1`) in `gazekey/ui/virtual_keyboard.py` — auto-start after preview; no visible UI control (FR-010, CQ-3)
- [x] T022 [US3] Integrate `gazekey/evaluation/benchmark_runner.py` with UI flow; block if calibration not passed
- [x] T023 [US3] Record benchmark pass/fail vs SC-001–004 (≥10/15 keys, ≤55 px median, ≥80% row, CQ-1) in `gazekey/evaluation/run_summary.py` (FR-012, FR-013)
- [x] T024 [US3] After each benchmark, append failure analysis (keys/rows failed; mapping vs geometry vs collection) via `gazekey/evaluation/failure_analysis.py` (FR-023)

**Checkpoint**: US3 independently testable.

---

## Phase 6: User Story 4 — Run Clarity (P4)

**Goal**: Quiet normal runs; optional verbose; one summary per run.

**Independent test**: Normal runs stay quiet; `GAZEKEY_VERBOSE=1` exposes detail; calibration + dev benchmark each produce one summary line.

- [x] T025 [US4] Consolidate quiet default logging in `gazekey/ui/virtual_keyboard.py`; remove per-frame spam (FR-015)
- [x] T026 [US4] Add single `GAZEKEY_VERBOSE=1` flag handling for extra detail; default off (FR-015, FR-016)
- [x] T027 [US4] Ensure one summary record per calibration and per benchmark in `gazekey/evaluation/run_summary.py` (FR-014, SC-005)
- [x] T028 [P] Add integration test in `tests/integration/test_mvp_pipeline.py` — calibrate → read-only preview; dev-flag benchmark (`GAZEKEY_DEV_BENCHMARK=1`) auto-start + summary; include **on-screen geometry sanity check** (visible key centers vs layout snapshot) before T029 baseline

**Checkpoint**: US4 complete; full MVP flow covered by integration test.

---

## Phase 7: Baseline PCA4 Run (mandatory before Phase 8)

**Purpose**: Establish comparison baseline per FR-022. **Phase 8 is blocked** until this completes end-to-end.

- [x] T029 Run end-to-end baseline: calibrate → preview → dev-flag benchmark (`GAZEKEY_DEV_BENCHMARK=1`); save summary to `runs/baseline_pca4_summary.txt` (FR-022)
- [x] T030 Document baseline metrics (key-hit, row accuracy, median error) and failure analysis note in `runs/baseline_pca4_summary.txt` (FR-023)
- [ ] T031 If T029 **cannot** complete end-to-end, fix blocking flow issues in Phases 3–6 (crash, calibration won't pass, preview/benchmark won't start) — **do not** enter Phase 8 until T029 succeeds (not required; T029 completed end-to-end)

**Checkpoint**: Saved baseline summary exists. If not, fix flow only (no accuracy iterations).

---

## Phase 8: Iteration — Result-Driven Accuracy (repeat as needed)

**Purpose**: Improve accuracy within PCA4 pipeline. **No mapper variant hunts.**

> **PAUSED (decision 2026-06-10, revised)**: Mapping accuracy and layout experiments are
> paused until **Phase 10** (active-code cleanup & architecture refactor) completes. The
> Candidate A/B layouts `keyboard_full9` (Candidate A) and `keyboard_wide9` (Candidate B) in
> `gazekey/calibration2/targets.py` are **retained**, kept behind `GAZEKEY_CALIB_MODE`
> (default active layout stays `keyboard15`). **Do not delete** layout candidates during
> Phase 10. Resume T032–T035 after Phase 10 behavior gate (T056) passes.

**Iteration rule (tasks-only)**: Apply **at most one accuracy-related change** per
cycle, then re-benchmark. Tasks T032–T035 are marked `[P]` as **conditional
alternatives** — pick **one** per iteration using the failure-pattern guide in
`plan.md` §Benchmark failure pattern → allowed fix. **Do not run T032–T035 in
parallel.** If failure analysis later justifies a post-fit correction layer
(e.g. row bias), document it in the T036 iteration note only — no dedicated task
until benchmark evidence supports it.

- [ ] T032 [P] **Layout iteration** (if guide points to calibration density/placement): one layout change in `gazekey/calibration2/targets.py`; re-benchmark vs T029 baseline
- [ ] T033 [P] **Collection iteration** (if guide points to fixation/drift): adjust `gazekey/calibration2/fixation_gate.py` or `session.py`; re-benchmark vs baseline
- [ ] T034 [P] **Geometry iteration** (if guide points to hitbox/center mismatch): fix `gazekey/layout/layout_inspector.py` / hit test alignment; re-benchmark vs baseline
- [ ] T035 [P] **PCA4 fit iteration** (if failure analysis justifies mapping Y/X bias, ridge α, or feature smoothing — not a new mapper): adjust `gazekey/mapping/ridge.py` and/or `gazekey/mapping/typing_candidate.py` only; re-benchmark vs baseline
- [x] T036 Document iteration outcome (improved / unchanged / regressed) in `runs/` vs T029 baseline; cite which single change (T032–T035) was applied (FR-022, FR-023)

**Checkpoint**: Stop when SC-001–SC-004 met or no justified single-change lever remains.

---

## Phase 9: Cleanup Phase A — Disconnect

- [x] T037 Disconnect unimplemented future UI controls in `gazekey/ui/virtual_keyboard.py` (FR-018): disable MVP behavior for suggestion bar, language toggle, symbols switch, etc., but **keep regions visible/layout-reserved** on the interactive keyboard surface — do not hide or reclaim their space (calibration geometry must reflect the full future keyboard)
- [x] T038 Block experimental mapper selection paths in `gazekey/mapping/ridge.py` and `gazekey/ui/virtual_keyboard.py` (FR-007)
- [x] T039 Document debug-only env vars in `specs/001-calibration-mapping-mvp/quickstart.md` (not in user flow)

---

## Phase 10: Active-Code Cleanup & Architecture Refactor

**Purpose**: Inventory → cleanup plan → user approval → incremental `virtual_keyboard.py`
refactor → approved removals only. **Goal is clarity, not mass deletion.** See
`plan.md` §Phase 10.

**Gate**: Complete T040–T041 before inventory or refactor work. See `plan.md` §Definition:
active PCA4 path proven.

**Behavior preservation** (all Phase 10 execution tasks): no alpha, row-Y, local-Y, X
correction, feature-smoothing, calibration-layout default, or benchmark threshold changes.

### Phase 10A — Inventory (no deletions)

- [ ] T040 Run 3 stable end-to-end flows (calibrate → preview → dev-flag benchmark); record per-run metrics and pass/fail in `runs/active_path_proven.txt`
- [ ] T041 Verify **active PCA4 path proven** checklist in `plan.md`; confirm `runs/active_path_proven.txt` from T040 is complete
- [ ] T042 Scan repository; produce `specs/001-calibration-mapping-mvp/cleanup-inventory.md` — classify every major path per plan (active MVP / future interaction / debug-offline / legacy / unknown); document path, purpose, MVP-imported, tests, recommendation, removal risk (FR-019)
- [ ] T043 Resolve all `unknown` items from T042 — update inventory with findings; add `investigate` follow-up tasks to cleanup plan if any remain unresolved

### Phase 10B — Cleanup plan + approval (no deletions)

- [ ] T044 From approved inventory, produce `specs/001-calibration-mapping-mvp/cleanup-plan.md` — exact keep / archive / delete / move-aside / refactor / disconnect decisions per item; one task stub per planned deletion or archive (FR-019)
- [ ] T045 **User approval gate** — review cleanup-plan.md; do not start T046+ until plan is explicitly approved

### Phase 10C — `virtual_keyboard.py` refactor (behavior-preserving)

Extract responsibilities incrementally; `VirtualKeyboard` becomes thin orchestrator.
Already extracted: `CalibrationController`, `GazePreviewController`.

- [ ] T046 Extract keyboard UI layout/widgets from `gazekey/ui/virtual_keyboard.py` into `gazekey/ui/keyboard_layout.py` (control bar, rows, text display, placeholders, minimized view)
- [ ] T047 Extract MVP + dev benchmark flow into `gazekey/ui/benchmark_controller.py` (banner, highlight, `evaluation/` integration, diagnostics hooks)
- [ ] T048 Extract post-calibration mapper runtime into `gazekey/ui/mapper_runtime.py` (fit finish, predict/clamp, mapper store — no mapping parameter changes)
- [ ] T049 Extract gaze loop dispatch into `gazekey/ui/gaze_loop.py` (`_on_eye_data_main_thread` → preview; dormant typing path isolated)
- [ ] T050 Extract env flag reads into `gazekey/ui/env_flags.py` (`GAZEKEY_VERBOSE`, `GAZEKEY_DEV_BENCHMARK`, `GAZEKEY_CALIB_MODE`, etc.)
- [ ] T051 Rewire `VirtualKeyboard` as thin orchestrator — delegate to extracted modules; remove duplicated logic; T028 integration test must still pass

### Phase 10D — Execute approved cleanup (one task per removal)

Only items approved in cleanup-plan.md (T045). **Do not delete dwell/intent/selection.**

- [ ] T052 Isolate future interaction code (dwell, intent, selection, gaze typing) from active MVP import path — move to `gazekey/future/` or equivalent facade; preserve all modules for later use (FR-019)
- [ ] T053 [cleanup-plan] Execute first approved archive/delete/disconnect item — dedicated task per cleanup-plan row (e.g. v1 `gazekey/calibration/` if plan approves)
- [ ] T054 [cleanup-plan] Execute second approved archive/delete/disconnect item — dedicated task per cleanup-plan row (e.g. dormant mapper wiring in `gazekey/mapping/` if plan approves)
- [ ] T055 [cleanup-plan] Execute third approved archive/delete/disconnect item — dedicated task per cleanup-plan row (e.g. debug-only imports removed from active chain if plan approves)
- [ ] T056 **Behavior preservation gate** — re-run T029 baseline flow; confirm key-hit, row accuracy, median error, and pass/fail unchanged vs pre-Phase-10 (normal run variance); document in `runs/phase10_behavior_gate.txt`

> **Note**: T053–T055 are placeholders for the first three approved removals. When
> cleanup-plan.md is written (T044), add one dedicated task per additional approved
> deletion/archive **before T056** (insert/renumber as needed). Uncertain items stay
> `investigate` — never delete.

**Checkpoint**: Inventory complete, plan approved, VK refactored, approved cleanups done,
behavior gate passed. **Then** resume Phase 8.

---

## Phase 11: Resume Phase 8 — Mapping Experiments

**Purpose**: Return to result-driven accuracy work with a clean active path.

- [ ] T057 Resume Phase 8 — pick one of T032–T035 per failure-pattern guide; re-benchmark vs T029 baseline; document via T036

---

## Phase 12: Acceptance

- [ ] T058 Run 3-session repeatability test per `specs/001-calibration-mapping-mvp/quickstart.md` §8; record in `runs/acceptance_3session.md` (SC-004, CQ-1)
- [ ] T059 Verify constitution alignment checklist in `specs/001-calibration-mapping-mvp/plan.md` — all gates still pass

---

## Dependencies & Execution Order

```text
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 (incl. T028 integration)
  → Phase 7 (baseline; T031 loops to 3–6 if blocked)
  → Phase 9 (disconnect) ✅
  → Phase 10 (inventory → plan → approval → refactor → approved cleanup → T056 gate)
  → Phase 11 (resume Phase 8: T032–T035 / T036)
  → Phase 12 (acceptance)
```

- **Phase 8 (T032–T036) PAUSED** until Phase 10 completes (T056 behavior gate)
- **T028** after Phases 3–6 complete and **before T029** baseline (full flow wired)
- **T029–T030** MUST succeed before Phase 10 execution (T046+)
- **T040–T041** MUST pass before T042 (inventory)
- **T045** user approval MUST pass before T046+ (refactor + cleanup execution)
- **T056** MUST pass before **T057** (resume Phase 8)
- **US2** depends on **US1**; **US3** depends on **US2** (CQ-3)

## Parallel Opportunities

- T004, T005, T006, T010 after T003
- T017, T020 after T018 starts
- T028 after Phases 3–6 complete, before T029 baseline (integration test needs full flow wired)
- **Phase 8**: T032–T035 are **mutually exclusive per iteration** — not parallel

## Implementation Strategy

1. Complete Phases 1–2, then US1 → US4 (incl. T028 integration test)
2. **Baseline (T029)** must finish end-to-end; else T031 fix flow, retry T029
3. **Phase 10** before resuming accuracy work: inventory → plan → approval → VK refactor → approved cleanups → T056 gate
4. **Phase 11**: resume Phase 8 — one change from decision guide → re-benchmark → T036 document
5. Acceptance last (Phase 12)

**MVP demo**: US1 + US2 + US3 + baseline summary — minimum validation loop.
