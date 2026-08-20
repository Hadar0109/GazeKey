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

**Product condition (decided 2026-08-20):** The target system is used **with
the chin/head support**, because the product goal is a stable head and the
highest achievable gaze-mapping accuracy under that condition. All accuracy
evaluation, `hadar` gates, and repeatability runs are captured **with** the
support. Free-head runs are diagnostic context only and MUST NOT be the
optimization target, even when they currently pass more easily. Baseline A
and B (free-head) remain the mandatory `eval_before` reference; T060 adds a
product-condition reference pair. See Phase 3.

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

**Product condition (decided 2026-08-20)**: The shipped system is used **with
the chin/head support**. Every mapping evaluation, `hadar` gate, and
repeatability run from here on is captured **with** the support. Baseline A
(`14938da0bdf0`) and B (`34fb259ccdfd`) were captured free-head; they remain
the required `eval_before` reference, and T060 adds a product-condition
("rest-condition") reference pair. Do not optimize against free-head runs.

**Order within Phase 3 (revised 2026-08-20)** — measurement capability first:

```text
T059 → T026 → T027 → T060 → T020 → T019 → T021 → T022 → T024 → T025
```

Reason: **with** the support, 0 of 5 sessions reached mapping evaluation
(`2879900a17e0`, `bfb745b0b87e` confirmed; `0694c1663623`, `42662808ac84`,
`cfdd5f1ea546` likely). All were blocked by the `avg_v` vs screen-Y
catastrophic check, which scores a **clamped 2-D proxy** rather than the
mapper's Y representation `(pca_vL, pca_vR)`. Both confirmed support sessions
beat accepted baselines A and B on `r(Y, pca_vL)` (+0.459 / +0.625 vs +0.357
/ +0.344), model-Y fidelity, training Y error, LOOCV (86.6 / 81.5 vs 89.4 /
95.2) and warning count — and were rejected. No collection experiment can be
measured under the product condition until that is resolved. This reorders
tasks **inside** Phase 3; plan phases A–F are unchanged.
Evidence: `runs/_feature004/T017_controlled_rest_vs_free.md`.

### Isolation of the unproven T017 change (do this first)

- [x] T059 [US2] **Isolate T017** (decision `inconclusive`, see `runs/_feature004/T017_4d_fixation_gate.md`): revert the 4-D fixation-gate product change, restoring the as-built 2-D behavior in `gazekey/calibration/fixation_gate.py`. The change is isolated in commit **`bedfb86`** ("fix(calibration): use per-eye 4D PCA for fixation stability checks"), which touches that file **only** — so this is a clean single-commit revert. In the **same** commit, revert or mark-as-desired the still-uncommitted T016 assertions in `tests/test_fixation_head_gate.py` so the suite matches the restored behavior. Leave the T018 and T023 pin tests untouched. Finish with `pytest -q` green. This is **isolation, not an accuracy experiment**: no eval vs A/B, no `keep_git_sha`, no accuracy claim, and T017's verdict stays `inconclusive` (recorded as `disposition`, not rewritten to `revert`). Rationale — T017 cannot be decided under the product condition until T027 unblocks measurement, and the experiment contract forbids starting a new experiment on top of an unproven change. T017 becomes re-testable as its own experiment after T060
  - **Done 2026-08-20.** `gazekey/calibration/fixation_gate.py` restored via `git checkout bedfb86^ --`, verified byte-identical to `bedfb86^` (`git diff bedfb86^` empty); it is the only product file touched. Confirmed first that no other module consumes the reverted symbols (`_pca4`, `_pca4_channel_stds`, `std_pca_uL/vL/uR/vR`) — `session.py` reads only `elapsed_collect_ms` and `calibration_overlay.py` only `state`, so the `debug_metrics` key change was unobserved. T016's gate assertions rewritten as **as-built pins** (the T018/T023 convention) with the desired 4-D behavior named in each docstring; the mapper-side 4-channel test was already true of the reverted tree and stands unchanged. `pytest -q`: **211 passed**

### Quality / pass-fail gates (research R10) — now the measurement blocker

- [x] T026 [US2] Write the gate finding (**evidence only, no policy change**): correlate `quality_gate_kind` with held-out inside-key and `hadar` focus using T010 summaries; inspect `_keyboard_blocking_reason` vs warning reasons in `gazekey/calibration/quality.py`. Record that the catastrophic check scores clamped binocular `avg_v` while the mapper fits Y from `(pca_vL, pca_vR)`, and that `pca_vR` tracks screen **X** on disk. Inputs: `runs/_feature004/T017_y_correlation_investigation.md`, `runs/_feature004/T017_controlled_rest_vs_free.md`. Also note that A/B passed this gate and were still untypeable — passing it guarantees nothing
  - **Done 2026-08-20** → `runs/_feature004/T026_quality_gate_findings.md`, computed over all **16** sessions with a `calibration_debug.csv`. Findings: (a) the **only** vertical check that can block a keyboard session reads `avg_v`, while every check reading `pca_vL`/`pca_vR` — including `require_any_vertical_monotonic` — is demoted to a warning because `_keyboard_blocking_reason` matches the substring `"catastrophic"`; (b) `avg_v = mean(clamp(0.5+pca_vL), clamp(0.5+pca_vR))` confirmed numerically (residual ≤ 0.0003), and the right-eye term **saturates at the clamp floor on 0–14 of 15 targets** depending on session, so the effective formula changes between targets within one session; (c) `r(X, pca_vR)` is −0.78…−0.97 in **16/16** sessions; (d) `r(Y, avg_v) < r(Y, pca_vL)` in **16/16** sessions; (e) 4 blocked-vs-accepted pairs invert the mapper's own Y signal, all rejecting a product-condition session for a weaker free-head baseline, with the boundary case turning on 0.034 (`bfb745b0b87e` +0.142 blocked vs baseline A +0.176 accepted, while their `r(Y,vL)` is +0.625 vs +0.357); (f) same 0.15 threshold on `r(Y, pca_vL)` would unblock 4 sessions and newly fail **none**. **Correction to this task's earlier wording**: Spearman rank agreement between `avg_v` and `r(Y, pca_vL)` is **+0.924**, so `avg_v` is broadly informative — the claim that it "does not rank-order sessions" was too strong. The real defect is that its errors are concentrated at the decision boundary and are one-sided against the product condition. Also: the requested `quality_gate_kind` ↔ outcome correlation **cannot be computed** (only 3 evaluated sessions, all `warning_only`), because the gate has never let a `blocking` session reach evaluation
- [x] T027 [US2] **One** product change in `gazekey/calibration/quality.py`, scoped to **what the vertical check measures**: score the catastrophic Y check on `r(screen_y, pca_vL)` — the mapper's own vertical channel — instead of clamped binocular `avg_v`. Keep the **0.15** threshold, keep blocking behavior, keep the `avg_v` value reported as a diagnostic. Do **not** loosen pass/fail into a warning, do **not** use fitted model-Y (T026 §3.6: circular, blocks 0/16 including an inverted session), do **not** make LOOCV the sole product accept/reject, do **not** add on-screen metrics during fixation (FR-004); pass/fail stays **after** the session (FR-005, SC-009). Add/adjust unit coverage in `tests/test_calibration2_quality.py`. Expected effect on the 16 sessions on disk: blocks 3 instead of 7 — still rejects `0694c1663623` (+0.012), `3d4be8b6eef7` (+0.075), `cfdd5f1ea546` (−0.054), and stops rejecting both product-condition sessions. Then recalibrate **with the chin/head support**, run the developer evaluation, and run the `hadar` gate; compare to baseline A and B; keep/revert/inconclusive; Git commit if keep. Requires T059 (done). Do **not** combine with T025 or T020. Record the caveat that a binocular check becomes preferable again if T020 repairs `pca_vR` — as a later separate task
  - **Code change landed 2026-08-20; live USER GATE pending.** Record: `runs/_feature004/T027_vertical_gate_representation.md`. Added `_paired_corr_with_screen_y` (pairs by index) and moved both the catastrophic 0.15 and preferred 0.55 vertical checks onto `pca_vL`; thresholds, blocking semantics and the 0.15–0.55 warning band unchanged; `avg_v` still computed and reported, and `screen_y_pca_vL_corr` added alongside it; `calibration_finish.py` prints the gated correlation first. Pre-flight replay of all 16 recorded sessions through the **shipped** function: blocked-on-Y goes **7 → 3**, newly passing `bfb745b0b87e`/`2879900a17e0`/`42662808ac84`/`05e40e22688f`, still blocking `0694c1663623`/`3d4be8b6eef7`/`cfdd5f1ea546`, and no previously passing session newly blocked — matching the T026 §3.6 prediction. `pytest -q`: **215 passed** (4 new tests, incl. good-`pca_vL`-with-catastrophic-`avg_v` accepted, inverted-`pca_vL`-with-good-`avg_v` still blocked, and a missing-sample test pinning that one dropped value no longer silently skips the whole blocking check). **Live gate done 2026-08-20 → decision KEEP.** Session `689c8a8ce90c`, with the chin/head support. The change was genuinely exercised: `r(Y, avg_v) = −0.152` (old gate would have **blocked**), `r(Y, pca_vL) = +0.222` (new gate passed). It is the **6th** support session and the **first** to reach mapping evaluation. Calibration PASSED `warning_only`, 19 warnings, LOOCV 104.3 px. Eval vs A/B: mapped-key 23% (vs 0% / 10%), median 81 px (vs 130 / 107), held-out 25% (vs 0% / 8%), editing 0% (tie), row 35% (ties B, below A 45%), `hadar` **3/5** wrong focus (vs 5/5 / 4/5) typing `uaraf`. Meets the pre-committed rule. **Attribution limit: T027 touches only the gate, so these gains are session variability, not an effect of the change** — the keep is earned by making the product condition measurable with no regression, and the row dip vs A is noise from the same distribution. `keep_git_sha`: **`b07e768`** (parent `6156659` = T059 revert, so reverting T027 alone restores the A/B tree). Records: `runs/_feature004/T027_vertical_gate_representation.md`, `runs/689c8a8ce90c/`
- [x] T060 [US2] **Product-condition ("rest-condition") reference pair**: once sessions pass under the product condition, capture **two** calib+eval sessions **with the chin/head support** on the kept stack and label them the product-condition reference (`runs/<session_id>/experiment_record.md`, plus `hadar_wrong_focus.md` on both). These **add to**, and do not replace, baseline A and B — the contract still requires citing A+B as `eval_before` (FR-026, SC-011). Record the condition difference explicitly
  - **CLOSED 2026-08-20** → `runs/_feature004/T060_product_condition_reference.md`. Ref 1 `689c8a8ce90c` (tree `b07e768`), ref 2 `4f665467b260` (tree `861a89c`, product code identical). Ref 2: calibration PASSED `warning_only`, 13 warnings, LOOCV 82.3 px; mapped-key 29%, median 78.2 px, row 39%, held-out 33%, editing 20%, repeatability 26.7%; `hadar` `ywdar` = **2/5** wrong focus
  - **Variability envelope on an unchanged tree, same condition** (the operative output): mapped-key **6 pp**, held-out **8.3 pp**, row 4 pp, median error **2.8 px** (most stable headline metric), LOOCV 22 px, `hadar` 1 letter, editing 20 pp (= 1 of only 5 keys, unusable at n=1), repeatability 0 pp. **A single post-change session cannot resolve a small effect**; results inside these bands are `inconclusive` until a second session confirms
  - **Localisation**: horizontal is stable *and* good — `r(X, avg_h)` −0.988/−0.994, X compression 0.94x/0.96x. Vertical is weak *and* unstable — `r(Y, pca_vL)` **+0.222 → +0.591** (2.7x apart) and Y compression **4.22x → 1.47x** (2.9x apart) between two sessions minutes apart, on a `pca_vL` range of only ~0.08 across 234 px of taught Y. `face_y`/`eye_box_h` drift small and comparable in both, so **head motion is not the explanation**. The one quantity that does not move is `r(X, pca_vR)` = −0.901/−0.899 → T020
  - **T027 in hindsight**: ref 2's `r(Y, avg_v) = +0.179` would have passed the *old* gate, so only ref 1 (−0.152) needed T027. This sharpens T026 rather than weakening it — two same-condition sessions straddle the old threshold by 0.029 while both `r(Y, pca_vL)` values are solidly positive, i.e. the old verdict turned on noise in a quantity the mapper never reads. T027 stays KEEP
  - Observational only, **not** a controlled result: both support sessions beat both free-head baselines on mapped-key, median error, held-out and `hadar`, with no overlap — but condition, date and gate version all differ, n=2 per group, and the T017 controlled runs found the opposite pass-rate direction. Recorded, not claimed

### Collection representation

- [x] T016 [P] [US2] Add failing-then-passing tests that the fixation gate evaluates the same 4-D representation the mapper consumes in `tests/test_fixation_head_gate.py` against `gazekey/calibration/fixation_gate.py` (not only averaged 2-D `u,v`) — landed, then converted by **T059** into **as-built pins**: the gate collapses PCA4 to a binocular mean, so opposing-eye jitter locks and a 0.15 one-eye jump is halved to 0.075 and escapes `jump_pca`. Each pin names the desired 4-D behavior in its docstring. The mapper-side test (fit consumes 4 independent channels) needed no change
- [ ] T017 [US2] Investigate 4-D vs 2-D lock in `gazekey/calibration/fixation_gate.py` vs `gazekey/mapping/` predict — **decision: inconclusive**; product change reverted by **T059**. Controlled diagnostic (2 WITH support, 2 WITHOUT): 0/2 usable with support, 1/2 without. T017 is **not** the Y-gate cause (the same block predates it), and its one supporting eval (`e3488095862f`) was free-head, i.e. not the product condition. Re-test as its own experiment after T060, under the product condition
- [x] T018 [P] [US2] Add tests for coherent per-frame aggregation (no independent per-channel means inventing a vector) in `tests/unit/test_calibration_session_collection.py` against `gazekey/calibration/session.py` — pins as-built Frankenstein means; aggregation itself is not changed until T019
- [ ] T020 [US2] **Run this first among T019–T022.** Investigate left/right eye-local **basis semantics** in `gazekey/features/extractor.py` (`_eye_uv_one_eye`) vs `gazekey/tracking/` eye-corner order — **`v` as well as `u`**. Evidence: `pca_vR` tracks screen **X** in all 11 sessions (`r(X, vR)` −0.78…−0.97) and `corr(uR, vR)` is +0.78…+0.94, i.e. the right eye's vertical axis is mixed with its horizontal one. That is the highest-value accuracy candidate under a stabilized head, and it also corrupts `avg_v`. If implicated, **one** semantics fix; recalibrate with the support; eval vs A/B (and the T060 reference); keep/revert/inconclusive. Requires T027 (done — evaluation under the product condition is now reachable). Do **not** combine with T027 or T019
  - **INVESTIGATION DONE 2026-08-20 → implicated, decisively. Product change NOT made; awaiting review of which single change to run.** Record: `runs/_feature004/T020_eye_local_basis_investigation.md`. Three independent lines of evidence: (i) ran the project's own `face_landmarker.task` on a probe face to *measure* the contour ring order instead of assuming it; (ii) applied an identical synthetic iris-displacement grid to both real contours through the real `_eye_uv_one_eye`, isolating code asymmetry from physiology; (iii) correlated all four stored channels against target X/Y across all **18** sessions (`calibration_v2.json` keeps `train_u_l/u_r/v_l/v_r`)
    - **Defect 1 — the aperture normalizer reads the wrong lid.** Measured ring order is: position 0 = corner, **1–7 = lower lid**, 8 = corner, **9–15 = upper lid**, for both eyes. The code's `upper = proj_y[1:5]` is therefore *entirely lower lid*, and `lower = proj_y[5:8] ∪ proj_y[9:13]` is a lid *mixture* — 4 lower + 3 upper on the left (median lands low) but 3 lower + 4 upper on the right (median lands high). So the same physical opening (true aperture 0.0203 left / 0.0205 right) is read as **0.824x** on the left and **0.525x** on the right
    - **Defect 2 — the vertical axis inherits the eye's canthal tilt with opposite sign per eye.** `y_hat = perp(x_hat)` has only its *sign* forced down, not its tilt removed; measured slant is +4.7° left / −5.1° right, giving `y_hat_x` = **−0.0817** / **+0.0888**. Horizontal iris motion therefore leaks into `v` oppositely per eye, then gets divided by the halved right-eye aperture: leak coefficient **0.441 left vs 0.745 right (1.69x)**. Synthetic sweep confirms `dv/d(dx)` = **−4.875 / +8.250** while `du/d(dx)` = +11.01/+11.03 (identical, exactly `1/eye_w`, only ~8% cross-talk) — so `u` is clean and `v` is not
    - **Both sign predictions confirmed 18/18 on real data**: `r(X, v_right)` mean **−0.900**, sign-consistent **18/18**; `r(X, v_left)` mean +0.087, sign-consistent only 10/18 (a coin flip, because there the leak fights a genuine Y signal of similar size). `r(u_right, v_right)` = **+0.896, 18/18** — the right eye's "vertical" channel is essentially a copy of its own horizontal one — against `r(u_left, v_left)` mean −0.097 (9/18). Spans: `u_left` 0.169 ≈ `u_right` 0.171 (match to 1%), but `v_left` **0.087** vs `v_right` **0.274** (3.1x). Predicted leak accounts for a **median 89%** of the left eye's observed vertical range (51–135%, several sessions >100%) and **47%** of the right's
    - **Defect 3, the deeper one — `v` is normalized by a gaze-*dependent* scale.** `u` is divided by eye width, which does not change as the eye rotates. `v` is divided by eyelid aperture, which *does*, because the lid follows the eye down — numerator and denominator move together and partially cancel, so the normalizer removes part of the signal it is scaling. Lid aperture is a vertical-gaze *cue* being divided out. Consequence: implied iris travel across the whole keyboard is **16.9% of eye width horizontally vs 1.6% vertically (10.5x)**, and the 1.6% still contains the leak
    - **Product-level symptom**: slope `d(dy)/d(target_y)` = **−0.961** (`689c8a8ce90c`) and **−0.878** (`4f665467b260`) — a slope of −1 means predicted Y is constant, so **88–96% of the vertical range is ignored** on eval locations, against 1.5–14% horizontally. Note `r(target_x, dy)` is only ≈ −0.09: the leak does *not* surface as X-dependent Y error, because ridge shrinks the near-useless Y weights toward zero, so neither signal nor leak reaches the output. **A fix must be judged on `d(dy)/d(target_y)` moving off −0.9, not on correlations tidying up.** Consistent with this, fitted `w_y` already leans on the left eye in 15/18 sessions (51–100% of `|w_y|`, median ~65%)
    - **Explains the T060 instability**: a channel that is mostly a stable geometric artifact plus a small genuine signal will reproduce the artifact to two decimals (`r(X, pca_vR)` −0.901/−0.899) while the surviving true fraction swings with incidental session geometry (`r(Y, pca_vL)` 0.222→0.591)
    - **Coupling a fix must handle**: `FixationGate` applies one threshold to both channels (`max_std_pca = 0.035`, `jump_threshold_pca = 0.10`, via `max(std_u, std_v)`). Because `v` is divided by aperture (~5.4x smaller than `eye_w`), the collection gate is currently **~5x stricter vertically than horizontally by accident**. A scale-changing fix must rescale those thresholds *in the same commit* to hold collection constant, or the result confounds better features with a looser gate — the T017 trap
    - **Benign findings**: corner polarity is anatomically mirrored (left position 0 = lm33 OUTER→INNER; right position 0 = lm362 **INNER**→OUTER) so the docstring is wrong for one eye, but both `x_hat` point image-right, which is what the mapper needs — fix the comment, not the code. Iris/contour pairing verified correct (lm468 inside the left contour, lm473 inside the right). `_eye_uv_one_eye` is the single path for calibration *and* live typing, so a fix adds no train/serve skew (FR-029)
    - **Candidate single changes:** **(A) TRIED and REVERTED 2026-08-20** — normalize `v` by eye width; two product-condition sessions `5e9c11d2c802` (slope −0.887) and `9ca533f8c0f0` (slope −0.943) both failed the −0.80 keep threshold and stayed inside the T060 range; session 2 row 29% also beyond the 4 pp envelope. Product restored to `861a89c`. Record: `runs/_feature004/T020_vertical_scale_change.md`. **(B) TRIED and REVERTED 2026-08-20** — image-vertical `y_hat`; both live sessions BLOCKED on `r(Y,pca_vL)` 0.116 (`89b4349e848b`) and 0.006 (`5e91836cbca2`). B did not remove X→v leak (`r(X,vL)` −0.385 / **−0.697**). Do not lower 0.15. Investigation: `runs/_feature004/T020_B_blocked_gate_investigation.md`. Product restored to `861a89c`. **(C) TRIED; live verdict REVERT 2026-08-20** — correct aperture lid indices; keep `perp(x_hat)` and the 0.15 gate. Sessions `72c67227e52d` (slope **−1.137**, mapped-key 6%, held-out 0%, median 117 px, `hadar` `uerer`) and `29c07b6b989f` (slope **−0.940**, median 98 px, `hadar` `udfdt`). Neither slope beat −0.80; listed T060 slices missed. Product code still C pending review. Record: `runs/_feature004/T020_lid_index_proposal.md`.
    - **Honest risk**: even a perfect fix leaves true vertical iris travel at ~1% of eye width. If landmark noise is comparable, the vertical axis may be under-resolved by this feature set regardless, and the next lever would be Phase 5 geometry / Phase 6 coverage or reducing the layout's vertical demand — not another feature tweak
  - **CHANGE A REVERTED 2026-08-20.** Product restored to `861a89c`. Sessions retained: `5e9c11d2c802` and `9ca533f8c0f0`. Record: `runs/_feature004/T020_vertical_scale_change.md`. **CHANGE B REVERTED 2026-08-20.** Both live sessions blocked (`89b4349e848b` r=0.116, `5e91836cbca2` r=0.006). Did not remove X→v leak. Do not lower 0.15. Product restored to `861a89c`. Investigation: `runs/_feature004/T020_B_blocked_gate_investigation.md`. **CHANGE C LIVE VERDICT REVERT 2026-08-20.** Sessions `72c67227e52d` and `29c07b6b989f`. Neither slope beat −0.80; session 1 missed mapped-key / held-out / median; session 2 missed median. Product code still C pending review — do not stack further accuracy or gate changes. Record: `runs/_feature004/T020_lid_index_proposal.md`.
  - **Separate defect found, out of T020 scope → new task T061**: `_EAR_CONTOUR_OFFSETS = (0, 4, 3, 8, 5, 11)` picks `p3` and `p5` as **both lower-lid** points, so EAR's second "vertical" term is a near-horizontal lower-lid chord. On an open eye it reads 0.0332 vs the genuine 0.0344 so EAR looks plausible (0.373/0.382), but that term cannot collapse during a blink, so `_EAR_BLINK_THRESHOLD = 0.20` does not mean what it appears to and blinks are under-detected, admitting partially-occluded frames into calibration
  - **Confirmed independently by `689c8a8ce90c`** (2026-08-20, first measured product-condition session): `r(X, pca_vR) = −0.901`, and the vertical axis is quantifiably the blocker — taught Y spans 234 px while predicted Y spans only 55 px (**~4.3x compression**), `pca_vL` spans just 0.072 across all 15 targets, `median_|dy|/h = 0.862` vs `median_|dx|/w = 0.176`, and all three live `hadar` errors were **row** errors with the correct column neighbourhood (H→U, D→R, R→F). Horizontal mapping is roughly usable; vertical is not. This is now the highest-value remaining lever, ahead of aggregation, layout, and ridge alpha
- [ ] T019 [US2] Investigate `_finalize_target_training_feature` (or equivalent) in `gazekey/calibration/session.py`; if implicated, one aggregation change, then eval vs baseline. **Not implicated by any of the 11 sessions on disk** — do not start it before T059/T026/T027/T060/T020
- [ ] T021 [US2] Investigate missing-eye policy in `gazekey/calibration/fixation_gate.py`, `gazekey/calibration/session.py`, and `gazekey/runtime/mapper_runtime.py`; align only if they silently diverge; one change; eval vs baseline
- [ ] T022 [US2] Investigate label-based `_row_column_peers` in `gazekey/calibration/outliers.py` (substring `"top"`/`"left"` vs `key_*` labels); if dead or misleading, one grouping change **or** documented keep — do not combine with T024/T026
- [ ] T061 [US2] **Blink EAR uses two lower-lid points as a "vertical" term** (found during T020, out of its scope). `_EAR_CONTOUR_OFFSETS = (0, 4, 3, 8, 5, 11)` in `gazekey/tracking/eye_detector.py` picks `p3` = ring position 3 and `p5` = position 5, both on the **lower lid** (measured, see `runs/_feature004/T020_eye_local_basis_investigation.md` §1), so `d(p3, p5)` measures a near-horizontal lower-lid chord rather than lid separation. On an open eye it reads 0.0332 against the genuine 0.0344 — close enough that EAR looks plausible (0.373 left / 0.382 right) — but it cannot collapse during a blink, so computed EAR cannot fall as far as a correct one and `_EAR_BLINK_THRESHOLD = 0.20` does not mean what it appears to. Effect: **under-detected blinks**, admitting partially-occluded frames into calibration and typing. One change (correct offsets to a genuine upper/lower pair), with a test pinning that a synthetic closed lid drives EAR below threshold and an open lid does not. Do **not** combine with T020 — it changes which frames are collected, which would confound any feature-semantics result

### Spatial row/column metadata (research R5) — investigate, do not assume retag

- [x] T023 [P] [US2] Add tests that document **as-built** `grid_row`/`grid_col` for Space vs Z/C/B/M and column coarsening in `parse_target_region` (`gazekey/calibration/region_quality.py`, `gazekey/calibration/targets.py`) in `tests/test_region_quality.py` / `tests/test_keyboard_geometry_targets.py` — these tests pin current behavior first
- [ ] T024 [US2] Investigate whether those tags mix distinct `screen_x/y` clusters for Space and other non-letter controls (Shift/Calibrate/Enter if used as targets) via `calibration_row_groups` in `gazekey/calibration/targets.py`, `evaluate_calibration_quality` in `gazekey/calibration/quality.py`, and region gates in `gazekey/calibration/region_quality.py`. Compare quality conclusions to actual coordinates. **No retag unless this evidence says the checks lie**
- [ ] T025 [US2] If T024 implicates metadata: one focused retag or grouping-rule change in `gazekey/calibration/targets.py` (and callers); recalibrate; eval vs baseline; keep/revert/inconclusive. Do **not** change pass/fail policy in the same iteration

**Checkpoint**: T017 is isolated, not carried; a session can pass under the product condition; a rest-condition reference pair exists; each remaining collection hypothesis has evidence; unproven changes are not stacked; gates and metadata were investigated separately

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
- [ ] T058 Run the **3-session final repeatability** protocol (SC-004) on the kept stack, **all three with the chin/head support** (product condition): three fresh calib+eval sessions; record mapped-key rates and best–worst spread vs the 53% / 20 pp reference floors in `runs/<session_id>/` via `tools/evaluation/run_summary.py`. Do not substitute baseline A/B or the T060 reference pair for these three sessions
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
- **US2 collection (Phase 3)**: After baseline T014–T015. Internal order
  revised 2026-08-20 to `T059 → T026 → T027 → T060 → T020 → T019 → T021 →
  T022 → T024 → T025`. **T059 (T017 isolation) blocks every later Phase 3
  experiment** — no new experiment starts on top of an unproven change.
  **T027 blocks T060 and T020–T025** under the product condition, because
  the vertical gate currently rejects rest sessions before evaluation runs
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
- Gate change (T027) **and** feature semantics (T020)
- T017 isolation (T059) **and** any accuracy change — T059 is isolation only
- Clamp/clip change (T034) **and** ridge alpha (T041)
- Aggregation **and** auto-alpha
- Layout change (T037 or T057) **and** mapper lever (T041)

### Parallel opportunities

- T002 / T003 after T001
- T004 / T005 before or beside T006–T011 (tests may fail until scoring lands)
- T012 / T013 / T055 after T007 / T009 (different test files)
- T016 / T018 / T023 as tests (done) while T027/T020/T019 are sequential
  experiments; T026 write-up may be drafted beside T059
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

Then run T027, T020, T019, T024 **one at a time** (after T059 isolation and
the T026 write-up).

---

## Implementation Strategy

### MVP First (measurement)

1. Phase 1 Setup
2. Phase 2 eval fidelity + **two** CurrentStateBaseline sessions + `hadar`
   wrong-focus on unchanged product
3. **STOP**: no mapping/collection “fixes” until A and B exist

### Incremental delivery (one investigation at a time)

1. US2 isolation: revert the unproven T017 gate change (T059)
2. US2 measurement capability: gate evidence (T026), then **one** change to
   what the vertical gate measures (T027), then the product-condition
   reference pair (T060)
3. US2 collection: eye-local `u`/`v` basis semantics (T020) first, then
   aggregation, missing-eye, peers
4. US2 metadata (Space / non-letter tags)
5. US3 sync
6. US4 geometry then, separately, clip/clamp if implicated
7. US1 coverage candidates (one per experiment; continue via T057 if needed)
8. Plan E auto-alpha diagnosis, then at most one mapper lever
9. Plan F: vs A/B + 3-session SC-004 + `hadar` vs A/B + hold-out words +
   `pytest -q` — all under the product condition (chin/head support)

### Suggested MVP scope

Phase 1 + Phase 2 (trustworthy eval + baseline). That is the Feature 004
measurement MVP. Product accuracy work starts only after T015.

---

## Notes

- [P] = different files, no incomplete dependencies
- Investigation ≠ patch: T024, T026, T033, T040 are evidence tasks
- Isolation ≠ experiment: T059 reverts an unproven change and makes no
  accuracy claim; it needs no eval and no `keep_git_sha`
- Follow-up change tasks exist only if evidence implicates that area
- All accuracy runs use the **chin/head support** (product condition);
  free-head runs are diagnostic context only
- Passing the calibration quality gates is **necessary, not sufficient**:
  baseline A and B both passed and were still not practically typeable
- USER GATE `hadar` always suggestions-off; compare wrong-focus to A and B
- Final hold-out words must not be used as development practice words
- Each **keep** requires a Git checkpoint (FR-026)
- Do not implement mapper complexity before collection/geometry/coverage
