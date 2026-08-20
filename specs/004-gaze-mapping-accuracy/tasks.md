# Tasks: Gaze Mapping Accuracy

**Input**: Design documents from `/specs/004-gaze-mapping-accuracy/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included where plan.md / contracts require pytest for scoring,
isolation, collection dimensionality, aggregation coherence, spatial fit,
and geometry/hit-test. Live webcam / `hadar` (vs baseline wrong-focus) and
final hold-out words = USER GATE (not fully automatable).

**Execution constraint (overrides parallel story starts):** Product/mapping
code changes follow plan phases **A → B → C → D → E → F**. Evaluation-tool
fidelity may land before the baseline. After the baseline, **one** logical
area per iteration; keep / revert / inconclusive. Audit items are
**investigations**, not a patch list.

**Path conventions**: Repository root (`gazekey/`, `tools/evaluation/`,
`tests/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 mapped-key typing, US2 collection, US3 train/live sync,
  US4 geometry, US5 independent measurement + one-change discipline

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pin Feature 004 artifacts and the as-built hypothesis inventory
so later experiments stay attributable.

- [x] T001 Confirm Feature 004 pointers and plan phases A–F in `.specify/feature.json`, `.cursor/rules/specify-rules.mdc`, and `specs/004-gaze-mapping-accuracy/plan.md` (no mapping code)
- [x] T002 [P] Add an experiment-record template (hypothesis, logical_area, eval_before A+B or last keep, eval_after, keep|revert|inconclusive, **keep_git_sha**) under `specs/004-gaze-mapping-accuracy/contracts/experiment-discipline.md` usage notes; persist records in `runs/<session_id>/` (no extra diagnostics platform)
- [x] T003 [P] Inventory the active mapping path only (no deletions): `gazekey/calibration/`, `gazekey/mapping/`, `gazekey/runtime/mapper_runtime.py`, `gazekey/typing/key_hit_tester.py`, `tools/evaluation/` — label active vs unused (e.g. `GazeSmoother` not on typing) in the experiment notes

**Checkpoint**: Feature 004 docs are the source of truth; audit items are listed as hypotheses

---

## Phase 2: Foundational — Evaluation fidelity + baseline (Plan A) 🎯 MVP measurement

**Purpose**: Trustworthy developer measurement of the **runtime** mapper /
geometry / key-hit path, then a **fresh current-state baseline**. No
collection, mapper, smoother, layout, or clip **product** change until
T015. Evaluation-tool and summary-field work in this phase is allowed
(research R2, FR-028/FR-029).

**⚠️ CRITICAL**: No User Story 1–4 **accuracy code** until this phase is
complete (**two** baseline sessions + USER GATE `hadar` wrong-focus on the
unchanged product).

**Maps to**: US5 (independent measurement), US1 (mapped-key scoring definition)

- [x] T004 [P] [US5] Add unit tests for inside-tight-rect + focus-stability scoring (snap ≠ success) in `tests/unit/test_benchmark_mvp.py` and/or `tests/unit/test_evaluation_summary.py`
- [x] T005 [P] [US5] Add a contract test that `gazekey.ui` / typing enablement does not import `tools.evaluation` in `tests/contract/test_evaluation_isolation.py` (new)
- [x] T006 [US5] Align `tools/evaluation/benchmark_runner.py` (and `tools/evaluation/benchmark_session.py` / `benchmark_controller.py` as needed) so each collect frame uses the same predict helper as product typing (`MapperRuntime.key_accuracy_predict_screen_xy` via `gazekey/runtime/mapper_runtime.py`) and `hit_test_layout_keys` in `gazekey/typing/key_hit_tester.py`
- [x] T007 [US5] Stop treating `DEFAULT_SAMPLE_KEYS` in `tools/evaluation/benchmark_runner.py` as the only slice: add **held-out letters** (research R3 default `W,R,Y,I,O,S,F,H,K,X,V,N` while current 15-anchor `keyboard15` is active) **and** an **editing/control** slice (Shift, Backspace, Space, Enter, Calibrate; do not double-count a calib-target key in the primary rate). Recompute slices if layout later changes. Do **not** score Feature 003 suggestion / prediction-bar keys as 004 mapped-key accept
- [x] T008 [US5] Record per-location `inside_tight`, `focus_stability`, `dx`/`dy`/`error_px`, `dx_over_width`/`dy_over_height`, `row_correct` in `tools/evaluation/run_summary.py` / `tools/evaluation/session.py` per `specs/004-gaze-mapping-accuracy/contracts/mapping-evaluation.md`. Held-out inside-key + focus stability are the FR-007 operational measures — do not add a separate feature-space metrics framework
- [x] T009 [US5] Add an evaluation **clip/clamp diagnostic** (research R7): for the same frames, record unclamped vs clamped `(x,y)` hit-test and `clamp_hit_rate` in `tools/evaluation/benchmark_runner.py` and `tools/evaluation/run_summary.py` — diagnostic only; do **not** change `Pca4BaselineMapper._clip_xy` in `gazekey/mapping/ridge.py` or `MapperRuntime.clamp_xy` in `gazekey/runtime/mapper_runtime.py`
- [x] T010 [US5] Record calibration `quality_gate_kind` (`blocking` | `warning_only` | `clean`) from `evaluate_calibration_quality` / `_keyboard_blocking_reason` in `gazekey/calibration/quality.py` onto the run summary in `tools/evaluation/run_summary.py` / `tools/evaluation/calib_finish_artifacts.py` — **do not** change which reasons block product typing
- [x] T011 [US5] Write remaining live-vs-eval diffs into `fidelity_notes` on the summary (`tools/evaluation/run_summary.py`) including EMA reset-per-key vs continuous typing
- [x] T012 [P] [US5] Add tests that held-out letter membership is not identical to `keyboard15` anchors and that the editing/control slice is present (Shift/Backspace/Space/Enter/Calibrate) in `tests/unit/test_benchmark_mvp.py`
- [x] T013 [P] [US5] Add tests that unclamped/clamped diagnostic fields exist and do not alter product clamp in `tests/unit/test_benchmark_diagnostics.py`
- [x] T055 [P] [US5] Add a unit/contract test that mapper `fit` is spatial only (`features → x,y`) and does not accept `key_id`, label, or row semantics as regression inputs in `tests/unit/test_spatial_fit_no_key_id.py` (new) against `gazekey/mapping/ridge.py` / `gazekey/mapping/base.py` (FR-030)
- [x] T014 [US5] Capture **CurrentStateBaseline A and B** (two sessions, mandatory) on unchanged mapping/collection: for each, calibrate via `python main.py`, run developer evaluation (all slices), save `runs/<session_id>/`. No mapping code change between A and B — **A = `runs/14938da0bdf0/`, B = `runs/34fb259ccdfd/`**, captured ~5 min apart on one code state; comparison in `runs/_feature004/baseline_A_B_comparison.md`
- [x] T015 [US5] USER GATE per `specs/004-gaze-mapping-accuracy/quickstart.md`: type `hadar` with suggestions unused on **both** baseline sessions; record wrong-focus letters (H/A/D/R) vs dwell under `runs/<session_id>/` for later comparison (SC-006) — **A 5/5 wrong focus** (H→J, A→D, D→F, A→D, R→G), **B 4/5 wrong focus** (H ok, A→S, D→F, A→S, R→F); records in `runs/<session_id>/hadar_wrong_focus.md`

**Checkpoint**: Both baseline artifacts exist; eval includes held-out letters **and** editing/control; clamp and quality-gate fields are diagnostics; spatial-fit test exists

---

## Phase 3: User Story 2 — Calibration Captures the Gaze Mapping Will Use (Priority: P1)

**Goal**: Confirm or reject collection-quality hypotheses, including
**warning-only pass/fail gates** and **spatial row/column metadata**
(especially Space / non-letter controls). Each item is measure → optional
one change → keep/revert/inconclusive.

**Independent Test**: After a session, developer records show accepted
samples are stable in the mapper’s representation, coherent, and that
quality conclusions match spatial clusters — or a written keep of the
current behavior.

**Depends on**: Phase 2 baseline (T014–T015)

### Collection representation

- [ ] T016 [P] [US2] Add failing-then-passing tests that the fixation gate evaluates the same 4-D representation the mapper consumes in `tests/test_fixation_head_gate.py` against `gazekey/calibration/fixation_gate.py` (not only averaged 2-D `u,v`)
- [ ] T017 [US2] Investigate 4-D vs 2-D lock in `gazekey/calibration/fixation_gate.py` vs `gazekey/mapping/` predict; if evidence implicates it, make **one** gate change, recalibrate, compare held-out to baseline, record keep/revert/inconclusive
- [ ] T018 [P] [US2] Add tests for coherent per-frame aggregation (no independent per-channel means inventing a vector) in `tests/unit/test_calibration_session_collection.py` against `gazekey/calibration/session.py`
- [ ] T019 [US2] Investigate `_finalize_target_training_feature` (or equivalent) in `gazekey/calibration/session.py`; if implicated, one aggregation change, then eval vs baseline
- [ ] T020 [US2] Investigate left/right `u` semantics in `gazekey/features/extractor.py` vs `gazekey/tracking/` eye-corner order; if implicated, one semantics fix, then eval vs baseline
- [ ] T021 [US2] Investigate missing-eye policy in `gazekey/calibration/fixation_gate.py`, `gazekey/calibration/session.py`, and `gazekey/runtime/mapper_runtime.py`; align only if they silently diverge; one change; eval vs baseline
- [ ] T022 [US2] Investigate label-based `_row_column_peers` in `gazekey/calibration/outliers.py` (substring `"top"`/`"left"` vs `key_*` labels); if dead or misleading, one grouping change **or** documented keep — do not combine with T024/T026

### Spatial row/column metadata (research R5) — investigate, do not assume retag

- [ ] T023 [P] [US2] Add tests that document **as-built** `grid_row`/`grid_col` for Space vs Z/C/B/M and column coarsening in `parse_target_region` (`gazekey/calibration/region_quality.py`, `gazekey/calibration/targets.py`) in `tests/test_region_quality.py` / `tests/test_keyboard_geometry_targets.py` — these tests pin current behavior first
- [ ] T024 [US2] Investigate whether those tags mix distinct `screen_x/y` clusters for Space and other non-letter controls (Shift/Calibrate/Enter if used as targets) via `calibration_row_groups` in `gazekey/calibration/targets.py`, `evaluate_calibration_quality` in `gazekey/calibration/quality.py`, and region gates in `gazekey/calibration/region_quality.py`. Compare quality conclusions to actual coordinates. **No retag unless this evidence says the checks lie**
- [ ] T025 [US2] If T024 implicates metadata: one focused retag or grouping-rule change in `gazekey/calibration/targets.py` (and callers); recalibrate; eval vs baseline; keep/revert/inconclusive. Do **not** change pass/fail policy in the same iteration

### Warning-only quality / pass-fail gates (research R10) — investigate, do not assume harden

- [ ] T026 [US2] Using baseline (and later) summaries from T010, correlate `quality_gate_kind` with held-out inside-key and `hadar` focus. Inspect `_keyboard_blocking_reason` vs warning reasons in `gazekey/calibration/quality.py`. Ask whether warning-only sessions are unusable, and whether clean/pass sessions still fail practical typing because gates measure the wrong thing (including T024 metadata). Write the finding in experiment notes — **no policy change in this task**
- [ ] T027 [US2] If T026 implicates the policy: one justified change (keep warnings, harden a **subset**, or change what is measured) in `gazekey/calibration/quality.py`. Do **not** make LOOCV the sole product accept/reject. Do **not** combine with T025. Do **not** add on-screen metrics during fixation (FR-004); pass/fail remains **after** the session (FR-005, SC-009). Recalibrate; eval vs baseline A and B; keep/revert/inconclusive; Git commit if keep

**Checkpoint**: Each collection hypothesis has evidence; unproven changes are not stacked; gates and metadata were investigated separately

---

## Phase 4: User Story 3 — Training and Live Prediction Speak the Same Language (Priority: P1)

**Goal**: Measure train vs live preparation (smoothing, averaging, missing
eye); one justified sync change or a documented keep.

**Independent Test**: Same look at a key produces compatible representations
at fit and at `key_accuracy_predict_screen_xy`, or the difference is
written and tied to measured accuracy.

**Depends on**: Phase 2; preferably after US2 keep/revert so collection noise
does not masquerade as a smoother bug

- [ ] T028 [US3] Measure runtime feature EMA (`FEATURE_SMOOTHER_ALPHA` / `gazekey/features/feature_smoother.py`) vs calibration unsmoothed target means in `gazekey/calibration/session.py` and `gazekey/runtime/mapper_runtime.py`; record the mismatch vs baseline failure pattern
- [ ] T029 [US3] If T028 implicates sync: **one** change (apply the same smoother to collected frames, stop smoothing at predict, or keep with written justification in experiment notes). Recalibrate; eval vs baseline; keep/revert/inconclusive
- [ ] T030 [US3] Confirm missing-eye / incomplete-vector policy is the same in gate, aggregation, and predict (`gazekey/calibration/fixation_gate.py`, `gazekey/calibration/session.py`, `gazekey/runtime/mapper_runtime.py`); if already covered by T021, record “not implicated / already decided” rather than a second change

**Checkpoint**: Any remaining train/live difference is intentional and evidence-backed

---

## Phase 5: User Story 4 — Keyboard Geometry Matches What Mapping Was Taught (Priority: P2)

**Goal**: One coordinate system from overlay dots through hit-test, including
Feature 003 layout. **Clip/clamp** when predictions leave the prediction
domain is an investigation (research R7), not a predetermined remove/expand.

**Independent Test**: Taught `screen_x/y`, visible key rects, mapped gaze,
and `hit_test_layout_keys` agree; unclamped vs clamped diagnostic from T009
is interpreted against edge-key errors.

**Depends on**: Phase 2 (T009 diagnostic data); do not retune ridge for
geometry bugs

- [ ] T031 [P] [US4] Add automated geometry tests: overlay/global target coords vs restored keyboard `inspect_keyboard_layout` / tight `rect` used by `hit_test_layout_keys` in `tests/unit/test_layout_geometry.py` and `tests/test_keyboard_geometry_targets.py` (`gazekey/ui/calibration_overlay.py`, `gazekey/ui/calibration_controller.py`, `gazekey/layout/`). **Close FR-013/014 resize:** if no supported user-facing resize/reposition/scaling path exists in `gazekey/ui/keyboard_layout.py` / `gazekey/ui/virtual_keyboard.py`, record **unsupported** in experiment notes and do not treat it as an open mapping defect; still test overlay close → restored keyboard. If a supported path exists, assert geometry refresh or that typing is not left on stale coords
- [ ] T032 [US4] Investigate Feature 003 bottom-row Calibrate vs Space vs suggestion-bar snapshot: clip rect from `letter_keys_region_rect` at calib start in `gazekey/ui/calibration_controller.py` vs typing layout in `gazekey/ui/virtual_keyboard.py` / `gazekey/ui/keyboard_layout.py`. Geometry mismatch ⇒ sync bug, not alpha
- [ ] T033 [US4] Analyze T009 unclamped vs clamped mapped-key on baseline (and later) runs: does clamp pin edge keys (outer letters, Space, Calibrate)? Are clip bounds wrong? Would unclamped points still miss? Write the finding — **do not change clamp in this task**
- [ ] T034 [US4] If T033 implicates clamp or clip bounds: **one** change to clip AABB and/or clamp behavior in `gazekey/mapping/ridge.py` `_clip_xy` and/or `gazekey/runtime/mapper_runtime.py` `clamp_xy` (and the calib-start rect in `gazekey/ui/calibration_controller.py` if that is the bound). Do not expand to fullscreen overlay unless evidence says the prediction domain is fullscreen. Recalibrate; eval vs baseline; keep/revert/inconclusive
- [ ] T035 [US4] USER GATE: after any layout/clip keep, confirm overlay dots vs restored hitboxes per `specs/004-gaze-mapping-accuracy/quickstart.md` section 6; record under `runs/<session_id>/`

**Checkpoint**: Geometry/clip hypotheses have evidence; clamp was not removed “because the audit said so”

---

## Phase 6: User Story 1 — Look at a Key and Hit That Key (Priority: P1) — coverage then product check

**Goal**: Required prediction domain is Feature 003 letter/editing keys.
Investigate calibration-domain candidates vs current key-centered 15
(research R4) — **one candidate per experiment**. A failed first candidate
does not prove `keyboard15` is optimal. Practical `hadar` is compared to
baseline wrong-focus (suggestions off).

**Independent Test**: Held-out inside-key + focus stability + editing/control
slice vs baseline A and B; USER GATE `hadar` wrong-focus vs those sessions.

**Depends on**: Plan B–C investigations complete or explicitly not implicated.
Do not start coverage while an unproven collection/geometry change is stacked.

- [ ] T036 [US1] Design **one** coverage candidate (spatial grid inside keyboard AABB, slightly expanded, or keep current 15) in `gazekey/calibration/targets.py` / `gazekey/mapping/config.py` without putting key ids into the fit
- [ ] T037 [US1] Run that **one** layout experiment vs current `keyboard15` control; recalibrate; same evaluation as baseline A/B; keep/revert/inconclusive; Git commit if keep
- [ ] T057 [US1] If T037 is revert or inconclusive, run **another** distinct layout candidate as a **new** experiment (still one change; same eval). Do **not** conclude `keyboard15` is optimal from the first failure. Repeat T057 only while coverage remains implicated and unproven changes are not stacked
- [ ] T038 [US1] If a layout is kept, recompute held-out letter and editing/control slices in `tools/evaluation/benchmark_runner.py` (research R3) and re-check spatial row/col metadata (T024) as a **separate** follow-up if tags changed — do not bundle with T037/T057
- [ ] T039 [US1] USER GATE `hadar` suggestions-off after a coverage keep (or after ruling coverage out) per `specs/004-gaze-mapping-accuracy/quickstart.md`; compare wrong-focus letters to baseline A and B (SC-006)

**Checkpoint**: Coverage is a kept layout, a documented further-candidate plan, or a written “current 15 still stands **without** treating first-failure as proof of optimality”

---

## Phase 7: User Story 1 continued — Mapper lever (Plan E, only if needed)

**Goal**: Touch mapper parameters **only if** held-out inside-key,
editing/control slice, and `hadar` wrong-focus vs A/B still fail after
collection, sync, geometry, and coverage investigation (FR-017, research R11).

**Independent Test**: Same eval as baseline; one mapper lever; keep/revert.

- [ ] T040 [US1] **Diagnose** as-built auto-alpha in `gazekey/mapping/ridge.py` `_auto_alpha` (largest alpha among scores within `ALPHA_SELECT_LOOCV_TOL_PX` of best LOOCV; grid in `gazekey/mapping/config.py`). Record selected alpha vs the full grid on kept sessions. **Do not change the rule in this task**
- [ ] T041 [US1] If T040 implicates underfit (or another single mapper hypothesis): **one** lever only — auto-alpha selection **or** X↔Y coupling **or** one justified extra layer — in `gazekey/mapping/ridge.py` / `gazekey/mapping/config.py` / `gazekey/mapping/row_bias.py`. Recalibrate; eval vs baseline A and B; keep/revert/inconclusive; Git commit if keep
- [ ] T042 [P] [US1] If an alpha-selection experiment is run, extend `tests/test_ridge_mapper_selection.py` to pin the **chosen** rule (as-built or kept alternative), not a predetermined min-alpha patch
- [ ] T043 [US1] If the first hypothesis list is exhausted and accuracy is still insufficient, continue diagnosis (further coverage candidates, mapping assumptions, feature sufficiency, mapper family) in experiment notes under `runs/<session_id>/` and the next one-change in `gazekey/mapping/` or `gazekey/features/` per FR-035 — do not stop while `hadar` wrong-focus is worse than both baselines and held-out has not improved

**Checkpoint**: Alpha was diagnosed at Phase E, not retuned during A–D; no stacked mapper levers

---

## Phase 8: User Story 5 wrap — Experiment discipline across stories (Priority: P2)

**Goal**: Every accuracy change has a recorded keep/revert/inconclusive;
evaluation never enters the product path.

- [ ] T044 [US5] Verify each kept experiment has an `ExperimentRecord` citing baseline A+B or last keep **and** a `keep_git_sha` (`specs/004-gaze-mapping-accuracy/data-model.md`, notes under `runs/<session_id>/`). Create the Git commit of that proven state if missing
- [ ] T045 [US5] Confirm product typing (`python main.py`, `gazekey/ui/virtual_keyboard.py`, `gazekey/runtime/gaze_loop.py`) still does not consult evaluation results for fit, clamp, hit-test, dwell, or enablement (`tests/contract/test_evaluation_isolation.py`)

**Checkpoint**: Unproven changes are not in the tree; product path remains evaluation-free

---

## Phase 9: Benchmark & Evaluation (Plan F)

**Purpose**: Acceptance vs baseline with simple run summary (Principles II & VII).
Historical 67% / 55 px / 80% row are **reference floors**, not automatic
Feature 004 pass.

- [ ] T046 Compare the kept stack to **baseline A and B**: held-out letters, editing/control inside-key, focus stability, key-relative error, clamp diagnostic, quality_gate_kind — write pass/fail + primary metrics in `runs/<session_id>/` via `tools/evaluation/run_summary.py`
- [ ] T058 Run the **3-session final repeatability** protocol (SC-004) on the kept stack: three fresh calib+eval sessions; record mapped-key rates and best–worst spread vs the 53% / 20 pp reference floors in `runs/<session_id>/` via `tools/evaluation/run_summary.py`. Do not substitute baseline A/B for these three sessions
- [ ] T047 USER GATE on the kept product (`specs/004-gaze-mapping-accuracy/quickstart.md`): `hadar` wrong-focus vs baseline A and B; then **2–3 additional short words not used during development**, covering different rows/keyboard regions, suggestions unused. Record focus errors under `runs/<session_id>/`
- [ ] T048 Confirm Feature 003 suggestions still work when used (preservation, not mapping accept) via `tests/contract/test_suggestion_typing_path.py` and a short manual check
- [ ] T049 Run full-project `pytest -q` from repo root; fix regressions caused by 004 changes only

**Checkpoint**: Two-session baseline comparison + 3-session SC-004 + `hadar` vs A/B + hold-out words + pytest; do not declare success from repeatability of the 15 anchors alone

---

## Phase 10: Targeted Cleanup (only where the active path is confusing)

**Purpose**: Principle IX — clean only what causes calibration/mapping/eval
confusion. Each deletion is its own approved task.

- [ ] T050 Label leftover unused mapping/eval helpers (debug `map_gaze_screen_xy` vs typing predict in `gazekey/typing/gaze_ui_mapper.py` / `gazekey/runtime/mapper_runtime.py`) in comments — no broad archival
- [ ] T051 [P] If a dead outlier-peer path remains after T022 keep/revert, either remove or clearly mark it in `gazekey/calibration/outliers.py` as a **separate** task from any gate/metadata change

**Checkpoint**: Active calib → PCA4 → hit-test path is obvious

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Docs and validation after the accuracy stack is decided.

- [ ] T052 [P] Update `specs/004-gaze-mapping-accuracy/quickstart.md` with the actual evaluation command, held-out set in use, and any kept clip/gate/alpha outcomes
- [ ] T053 [P] Sync `docs/CURRENT_PIPELINE.md` only if the **kept** mapping path diverges from Feature 003 as-built (do not rewrite for reverted experiments)
- [ ] T054 Run `specs/004-gaze-mapping-accuracy/quickstart.md` end-to-end on the kept stack (eval slices + `hadar` vs A/B + hold-out words + 3-session notes)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: Immediate
- **Foundational / Plan A (Phase 2)**: Depends on Setup — **BLOCKS** all
  product/mapping accuracy changes until T014–T015 (two sessions) and T055
  complete
- **US1 coverage (Phase 6)**: After collection/sync/geometry; T057 only after
  T037 revert/inconclusive
- **Mapper Plan E (Phase 7)**: Only if Phase 6 still fails vs baseline A and B
- **Benchmark (Phase 9)**: After the kept stack is stable; T058 is the
  3-session final protocol, not a substitute for T014
- **US2 collection (Phase 3)**: After baseline T014–T015
- **US3 sync (Phase 4)**: After baseline; prefer after US2 so data quality
  is not confounded with smoother mismatch
- **US4 geometry (Phase 5)**: After baseline; T009 diagnostic may be
  analyzed in parallel with US2 **measurement** tasks, but clip/clamp
  **code** waits for T033 evidence
- **US1 coverage (Phase 6)**: After collection/sync/geometry investigated
  or explicitly not implicated
- **Mapper Plan E (Phase 7)**: Only if Phase 6 still fails vs baseline
- **US5 wrap (Phase 8)**: Ongoing records; isolation re-check before accept
- **Benchmark (Phase 9)**: After the kept stack is stable
- **Cleanup / Polish**: After accept or when a specific confusion blocks MVP

### User story mapping

| Story | Plan | Notes |
|-------|------|--------|
| US5 | A (+ wrap) | Eval fidelity + baseline is the gate |
| US2 | B | Includes R10 warning-only gates and R5 spatial metadata |
| US3 | C (sync) | Smoother / missing-eye |
| US4 | C (geometry) | Includes R7 clip/clamp investigation |
| US1 | D + E + `hadar` | Coverage then mapper; auto-alpha only in E |

### Within each investigation

1. Measure / pin as-built with tests or eval columns
2. If implicated, **one** focused change
3. Same evaluation as baseline A and B
4. keep / revert / inconclusive
5. On keep: Git checkpoint (`keep_git_sha`)
6. Do not stack unproven work

### Forbidden pairings (same iteration)

- Metadata retag (T025) **and** gate-policy change (T027)
- Clamp/clip change (T034) **and** ridge alpha (T041)
- Aggregation **and** auto-alpha
- Layout change (T037 or T057) **and** mapper lever (T041)

### Parallel opportunities

- T002 / T003 after T001
- T004 / T005 before or beside T006–T011 (tests may fail until scoring lands)
- T012 / T013 / T055 after T007 / T009 (different test files)
- T016 / T018 / T023 as tests while T017/T019 are sequential experiments
- T031 tests vs T032 investigation (different files)
- T042 tests only if T041 chooses an alpha-rule experiment
- T052 / T053 after the kept stack is known

Do **not** parallelize sequential mapping experiments on the same tree.

---

## Parallel Example: Phase 2 scoring tests

```text
Task: "Add unit tests for inside-tight-rect + focus-stability scoring in tests/unit/test_benchmark_mvp.py"
Task: "Add contract test that product typing does not import tools.evaluation in tests/contract/test_evaluation_isolation.py"
```

## Parallel Example: US2 measurement (not product changes)

```text
Task: "Pin as-built Space grid_row vs letter row in tests/test_region_quality.py"
Task: "Pin 4-D vs 2-D gate behavior in tests/test_fixation_head_gate.py"
```

Then run T017, T019, T024, T026 **one at a time**.

---

## Implementation Strategy

### MVP First (measurement)

1. Phase 1 Setup
2. Phase 2 eval fidelity + **two** CurrentStateBaseline sessions + `hadar`
   wrong-focus on unchanged product
3. **STOP**: no mapping/collection “fixes” until A and B exist

### Incremental delivery (one investigation at a time)

1. US2 collection (gate, aggregation, u-axis, missing-eye, peers)
2. US2 metadata (Space / non-letter tags) then, separately, warning-only gates
3. US3 sync
4. US4 geometry then, separately, clip/clamp if implicated
5. US1 coverage candidates (one per experiment; continue via T057 if needed)
6. Plan E auto-alpha diagnosis, then at most one mapper lever
7. Plan F: vs A/B + 3-session SC-004 + `hadar` vs A/B + hold-out words +
   `pytest -q`

### Suggested MVP scope

Phase 1 + Phase 2 (trustworthy eval + baseline). That is the Feature 004
measurement MVP. Product accuracy work starts only after T015.

---

## Notes

- [P] = different files, no incomplete dependencies
- Investigation ≠ patch: T024, T026, T033, T040 are evidence tasks
- Follow-up change tasks exist only if evidence implicates that area
- USER GATE `hadar` always suggestions-off; compare wrong-focus to A and B
- Final hold-out words must not be used as development practice words
- Each **keep** requires a Git checkpoint (FR-026)
- Do not implement mapper complexity before collection/geometry/coverage
