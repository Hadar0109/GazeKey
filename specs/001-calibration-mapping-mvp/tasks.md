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
- [x] T004 [P] Add unit test that calibration targets from `gazekey/calibration/targets.py` use same layout snapshot as `inspect_keyboard_layout()` in `tests/unit/test_layout_geometry.py`
- [x] T005 [P] Implement `gazekey/evaluation/run_summary.py` — console + one lightweight file record per run (contracts/run-summary.md)
- [x] T006 [P] Implement `gazekey/evaluation/failure_analysis.py` — format per-key miss list, dx/dy, row errors into summary text (FR-023)
- [x] T007 Extract benchmark scoring into `gazekey/evaluation/benchmark_runner.py` using `gazekey/typing/key_hit_tester.py` (15 keys: `DEFAULT_SAMPLE_KEYS`)
- [x] T008 Wire `fit_calibration_mapper()` in `gazekey/mapping/ridge.py` to **PCA4 only** — disable multi-candidate ranking in active path; config in `gazekey/mapping/config.py` (FR-007)
- [x] T009 Disconnect v1 calibration fallback from `gazekey/ui/virtual_keyboard.py` normal flow (cleanup Phase A, FR-001)
- [x] T010 [P] Add `tests/unit/test_evaluation_summary.py` for pass/fail formatting and SC-001–004 threshold checks

**Checkpoint**: Geometry verified; evaluation module minimal (no mapper-compare tooling); PCA4-only fit path reachable.

---

## Phase 3: User Story 1 — Distraction-Free Calibration (P1)

**Goal**: Minimal fixation UI; per-session calibration; camera preview off during fixation (CQ-4).

**Independent test**: Complete calibration; dot + progress only on overlay; pass/fail after session; no camera window on fixation overlay.

- [x] T011 [US1] Strip debug/metrics text from `gazekey/ui/calibration_overlay.py` during fixation (FR-003, FR-004, SC-006)
- [x] T012 [US1] Ensure `gazekey/calibration/session.py` reports pass/fail only after session ends; LOOCV supplementary in summary only (FR-005, FR-009)
- [x] T013 [US1] Hide floating camera preview in `gazekey/ui/camera_preview_window.py` during calibration; default off; never z-order above fixation overlay (FR-006a, CQ-4)
- [x] T014 [US1] Require calibration at app start before preview/benchmark in `gazekey/ui/virtual_keyboard.py` (FR-006, CQ-2)
- [x] T015 [US1] Write calibration run summary via `gazekey/evaluation/run_summary.py` from calibration finish path (FR-014)
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

## Phase 7: Pre-Cleanup Baseline (historical)

**Purpose**: Pre-Phase-10 flow proof. **Not** the active Phase 8 tuning baseline.

- [x] T029 Run end-to-end baseline (pre-cleanup): calibrate → preview → dev-flag benchmark; saved to `runs/baseline_pca4_summary.txt` (FR-022, historical)
- [x] T030 Document pre-cleanup baseline metrics in `runs/baseline_pca4_summary.txt` (FR-023, historical)
- [x] T031 Flow completed end-to-end (not required for Phase 8 restart)

**Checkpoint**: Historical only. Active tuning baseline = **T061 two-run set** (Phase 11).

---

## Phase 8: Iteration — Result-Driven Accuracy (repeat as needed)

**Purpose**: Improve accuracy within PCA4 pipeline. **No mapper variant hunts.**

> **CLEAN RESTART (2026-06-10)**: `runs/` reset for fresh evidence. T029, old
> `iteration_*` files, and pre-restart tuning experiments (row-Y, alpha, layout, local-Y)
> are **historical only** — do not use as comparison evidence. **No T032–T035 before
> T061A–T061D complete.**

**Prerequisite**: T061D complete; first lever chosen. Compare every iteration vs
**T061 two-run baseline** (`runs/t061_baseline_comparison.md`).

**Iteration rule**: T062 implements **exactly one** of T032–T035 per cycle; T036 documents vs T061.

| Area | Task | Modules |
|------|------|---------|
| Layout | T032 | `gazekey/calibration/targets.py` |
| Fixation / collection | T033 | `gazekey/calibration/fixation_gate.py`, `session.py` |
| Geometry / hitboxes | T034 | `gazekey/layout/layout_inspector.py`, `key_hit_tester.py` |
| PCA4 fit / smoothing / row bias | T035 | `gazekey/mapping/ridge.py`, `config.py`, `row_bias.py` |

- [ ] T032 [P] **Layout** — one layout change; re-benchmark vs T061 baseline set
- [ ] T033 [P] **Collection** — fixation/collection change; re-benchmark vs T061
- [ ] T034 [P] **Geometry** — hitbox/center alignment; re-benchmark vs T061
- [ ] T035 [P] **PCA4 fit** — ridge/config/row_bias only; re-benchmark vs T061
- [ ] T036 Per iteration: document in `runs/iteration_NN_<change>.txt` vs T061; one change cited (FR-022, FR-023)

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

- [x] T040 Run 3 stable end-to-end flows (calibrate → preview → dev-flag benchmark); record per-run metrics and pass/fail in `runs/active_path_proven.txt`
- [x] T041 Verify **active PCA4 path proven** checklist in `plan.md`; confirm `runs/active_path_proven.txt` from T040 is complete
- [x] T042 Scan repository; produce `specs/001-calibration-mapping-mvp/cleanup-inventory.md` — classify every major path per plan (active MVP / future interaction / debug-offline / legacy / unknown); document path, purpose, MVP-imported, tests, recommendation, removal risk (FR-019)
- [x] T043 Resolve all `unknown` items from T042 — update inventory with findings; add `investigate` follow-up tasks to cleanup plan if any remain unresolved

### Phase 10B — Cleanup plan + approval (no deletions)

- [x] T044 From approved inventory, produce `specs/001-calibration-mapping-mvp/cleanup-plan.md` — exact keep / archive / delete / move-aside / refactor / disconnect decisions per item; one task stub per planned deletion or archive (FR-019)
- [x] T045 **User approval gate** — review [cleanup-plan.md](./cleanup-plan.md); do not start T046+ until plan is explicitly approved (approved 2026-06-10)

### Phase 10C — `virtual_keyboard.py` refactor (behavior-preserving)

Extract responsibilities incrementally; `VirtualKeyboard` becomes thin orchestrator.
Already extracted: `CalibrationController`, `GazePreviewController`.

- [x] T046 Extract keyboard UI layout/widgets from `gazekey/ui/virtual_keyboard.py` into `gazekey/ui/keyboard_layout.py` (control bar, rows, text display, placeholders, minimized view)
- [x] T047 Extract MVP + dev benchmark flow into `gazekey/ui/benchmark_controller.py` (banner, highlight, `evaluation/` integration, diagnostics hooks)
- [x] T048 Extract post-calibration mapper runtime into `gazekey/ui/mapper_runtime.py` (fit finish, predict/clamp, mapper store — no mapping parameter changes)
- [x] T049 Extract gaze loop dispatch into `gazekey/ui/gaze_loop.py` (`_on_eye_data_main_thread` → preview; dormant typing path isolated)
- [x] T050 Extract env flag reads into `gazekey/ui/env_flags.py` (`GAZEKEY_VERBOSE`, `GAZEKEY_DEV_BENCHMARK`, `GAZEKEY_CALIB_MODE`, etc.)
- [x] T051 Rewire `VirtualKeyboard` as thin orchestrator — delegate to extracted modules; remove duplicated logic; T028 integration test must still pass

### Phase 10D — Execute approved cleanup (one task per removal)

Only items approved in [cleanup-plan.md](./cleanup-plan.md) (T045). **Do not delete dwell/intent/selection.**

- [x] T052 Isolate future interaction code — `gazekey/future/` facade; preserve intent, selection, gaze_typing_controller, dwell_selector (FR-019)
- [x] T053 Disconnect v1 from `gazekey/ui/calibration_overlay.py` — v2-only overlay API (FR-019)
- [x] T054 Refactor `gazekey/mapping/__init__.py` to PCA4-only exports; update test imports (FR-019)
- [x] T055 Archive `gazekey/mapping/idw_local.py`, `idw_ratio.py`, `row_aware.py` → `archive/mapping_variants/` (FR-019)
- [x] T056 Move `tracking_bridge.py` → `gazekey/tracking/`; archive remaining `gazekey/calibration/` v1 → `archive/calibration_v1/` (FR-019)
- [x] T057 Archive `tests/test_calibration.py` → `archive/tests/test_calibration_v1.py` (FR-019)
- [x] T058 Delete root stale `key_accuracy_debug.csv` and `key_accuracy_compare.csv` (FR-019)
- [x] T060 **Behavior preservation gate** — re-run T029 baseline flow; confirm metrics vs pre-Phase-10; document in `runs/phase10_behavior_gate.txt`

**Checkpoint**: Inventory complete, plan approved, VK refactored, approved cleanups done,
behavior gate (T060) passed. **Then** resume Phase 8.

---

## Phase 11: T061 Baseline Set + First Tuning (blocks Phase 8)

**Purpose**: Two-run evidence baseline, AR triage, lever selection, then first one-change iteration.

**Frozen during T061**: no changes to α, row bias, smoothing, layout, fixation gate, hitboxes, or features.

- [ ] T061A **Baseline run 1** — calibrate → read-only preview → benchmark (`GAZEKEY_DEV_BENCHMARK=1`); artifacts in `runs/<session_id_A>/`. No tuning. (FR-022)
- [ ] T061B **Baseline run 2** — same setup, new app session, **no code/config changes**; `runs/<session_id_B>/`
- [ ] T061C **Baseline comparison + AR triage** — write `runs/t061_baseline_comparison.md`: key-hit, row, median_err, failed keys, per-key dx/dy, both `coverage.json` files, live geometry sanity (AR-5, AR-6), session variance (AR-7), regional bias (AR-2), AR-8 recommendation; trigger AR-3/AR-4 notes if baselines noisy; defer AR-1 unless unexplained mapping bias on both runs (FR-023)
- [ ] T061D **Choose first lever** — from T061C, confirm testing order and select **exactly one** of T032–T035 for T062; record rationale in `t061_baseline_comparison.md`
- [ ] T062 **First tuning iteration** — implement **only** T061D choice; re-benchmark; complete T036 (`runs/iteration_01_<lever>.txt`) vs T061 baseline set

---

## Phase 12: Acceptance

- [ ] T063 Run 3-session repeatability test per `quickstart.md` §8–9; record in `runs/acceptance_3session.md` (SC-004, CQ-1)
- [ ] T064 Verify constitution alignment checklist in `plan.md` — all gates still pass

---

## Dependencies & Execution Order

```text
Phase 1 → … → Phase 10 (T060) ✅
  → Phase 11: T061A → T061B → T061C → T061D → T062 (first iteration)
  → Phase 8 cycles: further T032–T035 + T036 (one change each, vs T061)
  → Phase 12: T063–T064 acceptance
```

- **T061A–T061D** MUST complete before **T062** or any code tuning
- **T061** two-run set = **only** active comparison baseline for Phase 8
- **T029**, deleted `iteration_*`, pre-restart tuning = historical only
- **US2** depends on **US1**; **US3** depends on **US2** (CQ-3 dev benchmark)

## Parallel Opportunities

- T004, T005, T006, T010 after T003
- T017, T020 after T018 starts
- T028 after Phases 3–6 complete, before T029 baseline (integration test needs full flow wired)
- **Phase 8**: T032–T035 are **mutually exclusive per iteration** — not parallel

## Implementation Strategy

1. Phases 1–10 complete ✅; `runs/` cleaned for fresh Phase 8 evidence
2. **T061A–T061D** — two baselines, comparison doc, lever pick; no tuning during T061
3. **T062** — first one-change iteration vs T061; then Phase 8 cycles + T036
4. AR checks: analysis in T061C only; no tooling until approved
5. Acceptance last (Phase 12, T063–T064)

**MVP demo**: US1 + US2 + US3 + baseline summary — minimum validation loop.
