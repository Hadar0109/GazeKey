# Tasks: GazeFollower Production Integration

**Input**: Design documents from `/specs/005-gazefollower-backend/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included where plan.md / contracts require pytest isolation, GazeSample
validity, invalid-sample dwell cancel, and GazeSample → MappedGazePoint →
hit-test isolation. Stage C and Stage F live webcam sessions are **USER GATE**
(not fully automatable).

**Execution constraint (overrides parallel story starts):** Product work follows
plan stages **A → B → C → D → E → F → G**. Do **not** collapse this feature
into one large migration. Later stages MUST NOT start until the prior stage
checkpoint passes.

**Product condition:** Chin/head support for all accuracy evaluation, `hadar`
gates, and repeatability runs.

**Hard constraints (do not violate while implementing any task):**

- Do not introduce EyeTheia, another backend, an ensemble, or a fallback cascade.
- Do not recreate GazeFollower Preview/Calibration in Qt.
- Do not add learned mapping, bias, affine correction, PCA, Ridge, or extra
  smoothing after GazeFollower.
- Do not modify Feature 004 specs, runs, tags, or commits.
- Do not reconnect dwell before the Stage C USER GATE **T029** PASS **or
  USER-ACCEPTED CONTINUATION** (`runs/_feature005/T029_parity_audit.md`).
- This file's **T060** is the Feature 005 suggestion USER GATE. Always write
  **Feature 004 T060** when referring to the historical Feature 004 experiment.
- Stage G may begin at T064 only after T062 PASS **and** T063 cleanup-hold
  release. Destructive deletions T066–T078 MUST NOT start until T062 PASS,
  T063 hold released, T064 checkpoint exists, **and** T065 inventory freeze
  is complete. Entering Stage G does **not** already depend on T064.
- Rollback is Git, not a GazeFollower/PCA4 cascade.

**Path conventions**: Repository root (`gazekey/`, `main.py`, `tools/`, `tests/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 startup, US2 keyboard gaze handoff, US3 typing product,
  US4 recalibrate/shutdown, US5 integrated acceptance + cleanup
- Setup / Foundational (Stage A): no story label
- USER GATE and HARD STOP GATE are called out in the task description

---

## Phase 1: Implementation Stage A — Environment setup (Shared Infrastructure)

**Purpose**: First **implementation** increment after completed planning
Stage A (`plan.md` / `research.md` / `contracts/`). Rebuild GazeKey on
Python 3.11 and pin official GazeFollower v1.0.2 with verified model
provenance. No Qt keyboard integration yet. T001–T017 remain required
and stay in this order.

**Independent Test**: `python --version` is 3.11.x; retained GazeKey imports
succeed; `import gazefollower` reports 1.0.2; `base.mnn` SHA-256 matches
plan.md.

- [X] T001 Rebuild the GazeKey environment on Python 3.11 (discovery 3.11.9) as a new/replaced venv at `.venv`; do **not** prove GazeFollower on the existing Python 3.14 venv; record the interpreter path used by the product
- [X] T002 Verify all retained GazeKey dependencies on that 3.11 environment (`PySide6`, `pynput`, and current `requirements.txt` entries still needed for keyboard/dwell/OS/prediction) and update `requirements.txt` so the 3.11 product env is the source of truth
- [X] T003 Install and pin official `gazefollower==1.0.2` at commit `553920edcb7998c029828677f50f6d8eb4a16249` in `requirements.txt` (PyPI pin or pip-from-commit); adapter code must `import gazefollower` and MUST NOT vendor upstream into `gazekey/`
- [X] T004 Create package `gazekey/backend/` (`__init__.py`) as the only new production gaze adapter; do not copy GazeFollower internals into `gazekey/features/`, `gazekey/mapping/`, or `gazekey/calibration/`
- [X] T005 Verify packaged `gazefollower/res/model_weights/base.mnn` SHA-256 `2f96b95275fe6d7b79e98df3237ebb96e15ef5522c96968f08167da7e1954a96` and record provenance plus license-of-record **CC BY-NC-SA 4.0** (attribution + non-commercial/share-alike; `version.py` CC BY 4.0 is upstream inconsistency only) in `gazekey/backend/provenance.py`

**Checkpoint**: 3.11 env runs; `gazekey/backend/` exists; GazeFollower 1.0.2 and `base.mnn` hash are pinned

---

## Phase 2: Implementation Stage A — Thin backend, isolation, geometry STOP (Foundational)

**Purpose**: Blocking adapter, GazeSample contract, dependency isolation, and
the geometry HARD STOP **mechanism/policy**. No official Preview in `main.py`
yet. No dwell. No live Qt keyboard / QRect proof in this stage.

**⚠️ CRITICAL**: Stages B–G MUST NOT begin until this phase is complete,
including T012 **implemented and tested**. T012 does **not** claim that real
keyboard geometry has already passed: the Qt keyboard and live QRects do not
exist yet. Stage B depends on T012 being implemented/tested, not on a
live-coordinate PASS. The actual runtime geometry proof is Stage C
(T028 record, T029 USER GATE, T030 invoke STOP if needed). If only
identity/origin/DPR transforms are allowed and a later live audit cannot
align them, **stop and report** — do not add a mapper, bias, or affine
correction, and do not change upstream `generate_points`.

**Independent Test**: pytest isolation + GazeSample validity tests pass; geometry
helpers record the required fields and **refuse** transforms other than
identity/origin/DPR.

- [X] T006 [P] Implement `GazeSample` in `gazekey/backend/gaze_sample.py` per `specs/005-gazefollower-backend/data-model.md` and `contracts/gaze-sample.md` (`timestamp_ns`, `valid`, `x`, `y`, diagnostic `calibrated_x/y`, `tracking_state`, `left_openness`, `right_openness`); omit `features`, `raw_gaze_coordinates`, `event`, and invented confidence
- [X] T007 [P] Implement identity/origin/DPR-only geometry in `gazekey/backend/geometry.py` per `contracts/screen-geometry.md` (`qt_global = origin_offset + gf_filtered_px / dpr_or_1`, or identity); forbid learned affine, Ridge remap, `_gaze_bias_*`, mapper `clip_bounds`, copied `camera_position`, and hard-coded key tables
- [X] T008 Implement official `GazeInfo` → `GazeSample` mapping in `gazekey/backend/adapter.py`: pointing `x,y` from `filtered_gaze_coordinates` after T007; `valid` iff `status==True`, `tracking_state==SUCCESS`, finite length-2 filtered xy, and both openness values `> 10`; invalid MUST NOT hold-last
- [X] T009 Implement the thin lifecycle wrapper in `gazekey/backend/lifecycle.py` around official `GazeFollower` + `DefaultConfig` (`cali_mode=13`, `screen_physical_size=None`; do not copy `camera_position`) exposing `preview()`, `calibrate()`, `start_sampling()`, `stop_sampling()`, `release()`, and `get_gaze_info()`; never start a new Preview/Calibration mode unless camera state is `CLOSING`
- [X] T010 Add a Qt-thread-safe sample callback in `gazekey/backend/lifecycle.py` (queued signal or equivalent) so camera-thread `get_gaze_info()` is not consumed unsafely on the Qt thread. Sequential after T009; both tasks modify `lifecycle.py`.
- [X] T011 Implement geometry-audit **schema/helper only** in `gazekey/backend/geometry.py` (and a session record helper under `gazekey/backend/`): field definitions for screeninfo size, pygame mode, Qt `QScreen.geometry()`, `devicePixelRatio`, monitor origin, keyboard `mapToGlobal(0,0)`, and chosen transform `identity` | `origin` | `origin+dpr`. Do **not** treat T011 as live keyboard proof. Live values and proof remain T028/T029/T030.
- [X] T012 **HARD STOP GATE (mechanism/policy only)**: in `gazekey/backend/geometry.py`, implement and test that the only allowed conversions are identity, origin offset, and/or DPR scaling; any other transform (mapper, bias, affine, `generate_points` change) is forbidden and must STOP/report. Stage A MUST NOT claim live keyboard geometry has passed (Qt keyboard / live QRects do not exist yet). Do not treat T012 as a live-coordinate PASS; Stage B may proceed once this policy is implemented/tested. Live proof is T028–T030.
- [X] T013 Add pytest dependency-isolation tests in `tests/contract/test_backend_isolation.py` that fail if `gazekey.backend` imports `gazekey.features`, `gazekey.mapping`, `gazekey.calibration`, or `gazekey.tracking` (FR-011 / `contracts/dependency-isolation.md`)
- [X] T014 [P] Add GazeSample validity unit tests in `tests/unit/test_gaze_sample.py` covering the five `valid=True` rules and that `features` / raw model-space coordinates are not on the contract
- [X] T015 [P] Add invalid-sample tests in `tests/unit/test_gaze_sample_invalid.py` proving openness `<= 10`, non-SUCCESS tracking, non-finite xy, or `status=False` yield `valid=False` with **no hold-last**
- [X] T016 Make GazeFollower lifecycle **fail closed** in `gazekey/backend/lifecycle.py` for failures during GazeFollower construction/import/model initialization, `preview()`, `calibrate()`, `start_sampling()`, or camera opening: report clearly and exit/return failure without starting `TrackingManager`, `MapperRuntime`, PCA4, Ridge, or another estimator. Do **not** describe camera-open failure as necessarily happening during adapter construction.
- [X] T017 [P] Extend isolation tests in `tests/contract/test_backend_isolation.py` to assert `GazeInfo.features` is never copied onto `GazeSample` or passed to any mapper

**Checkpoint**: Thin backend exists; isolation tests fail if the PCA4 stack leaks in; geometry STOP **policy** is implemented/tested (not a live-keyboard PASS). **Do not open dwell or the product typing path.**

---

## Phase 3: Stage B — User Story 1 — Official GazeFollower Startup (Priority: P1)

**Goal**: Normal `python main.py` runs official pygame Preview, then official
13-point Calibration/result (Space accept / R retry), then `start_sampling()`,
then constructs and shows the **existing** GazeKey keyboard. TrackingManager /
EyeDetector / legacy calibration MUST NOT run. No PCA/Ridge fallback.

**Independent Test**: Launch the Feature 005 path. Confirm official Preview →
Calibration → result/accept, then sampling starts, then the existing GazeKey
keyboard is shown. Confirm GazeKey did not host its own calibration-target UI
and that the legacy GazeKey calibration system did not run.

**Depends on**: Stage A (T001–T017), including T012 **implemented and tested** (not a live-keyboard geometry PASS; that cannot exist until Stage C)

- [X] T018 [US1] Change `main.py` so it does **not** construct `QApplication` or `VirtualKeyboard` before official Preview/Calibration; parse args via `gazekey/app_config.py` without starting `TrackingManager`
- [X] T019 [US1] Integrate official `preview()` through `gazekey/backend/lifecycle.py` as a blocking pygame fullscreen using GazeFollower’s own Preview UI unmodified (FR-003); do not recreate Preview in Qt
- [X] T020 [US1] Integrate official `calibrate()` 13-point (`DefaultConfig.cali_mode=13`) through `gazekey/backend/lifecycle.py`, including official result UI Space=accept and R=retry inside `calibrate()`; do not use `keyboard15`, `CalibrationOverlay`, or `pca_vL` 0.15 to accept/reject
- [X] T021 [US1] After accepted calibration, call `pygame.quit()` then `start_sampling()` in `gazekey/backend/lifecycle.py` / `main.py` so camera state is `CLOSING` before sampling; do not overlap pygame and Qt event loops
- [X] T022 [US1] After sampling has started, construct and show the existing `VirtualKeyboard` in `gazekey/ui/virtual_keyboard.py` / `main.py` (the one keyboard used for the rest of the product). `TrackingController` / `TrackingManager` / `EyeDetector` are **not started** and GazeKey camera capture is unused. Stage C must not construct or open a second keyboard.
- [X] T023 [US1] Disable legacy startup calibration in `gazekey/ui/virtual_keyboard.py` (`_init_calibration_on_startup`, `_start_calibration`, `_start_calibration_if_needed`, `CalibrationOverlay`) so the legacy overlay does not run on the production path
- [X] T024 [US1] Fail closed in `main.py` / `gazekey/backend/lifecycle.py` if GazeFollower construction/import/model initialization, `preview()`, `calibrate()`, `start_sampling()`, or camera opening fails: report clearly and exit/return failure; do **not** start `TrackingManager`, `MapperRuntime`, PCA4, Ridge, or another estimator. Camera-open failure is a lifecycle failure, not necessarily adapter-construction failure. Abnormal process exit or failure **during official Preview or Calibration** MUST still attempt `GazeFollower.release()` / camera cleanup where technically possible, and MUST NOT recover via TrackingManager/PCA4/Ridge.
- [X] T025 [P] [US1] Add/extend startup isolation tests in `tests/contract/test_startup_no_legacy.py` proving the production startup path does not import/call `FeatureExtractor` gaze semantics, PCA/PCA4, Ridge, `pca_vL`/`pca_vR`, `keyboard15`, `TrackingManager`, or `MapperRuntime` fit/predict

**Checkpoint**: Official Preview + 13-point Calibration + sampling work; existing GazeKey keyboard is shown once; legacy estimator is not on the startup path.

---

## Phase 4: Stage C — User Story 2 — Official Gaze on the Live Keyboard (Priority: P1)

**Goal**: Use the **existing** GazeKey keyboard already constructed and shown in
Stage B. Add a **temporary** debug gaze dot from official filtered gaze and
run the live geometry USER GATE. Do **not** open a second keyboard. Prove
mapping survived the handoff. **Do not reconnect dwell.**

**Independent Test**: Chin/head support, look across the live layout on the
Stage B keyboard; the debug dot tracks intended regions without a
post-GazeFollower mapper.

**Depends on**: Stage B (T018–T025)

- [X] T026 [US2] Continue on the existing keyboard already constructed and shown in Stage B (`gazekey/ui/virtual_keyboard.py` / `gazekey/ui/keyboard_layout.py`). Do **not** construct or open a second keyboard. Do not redesign visuals and do not start legacy calibration.
- [X] T027 [US2] Add a temporary debug gaze dot driven **only** by official filtered `GazeSample.x/y` (reuse `tools/preview/gaze_preview.py` overlay or an equivalent developer overlay on the keyboard). Do **not** call `GazeTypingRuntime.on_mapped_gaze`, `DwellEngine`, or `ActionDispatcher` yet
- [X] T028 [US2] **Live geometry record**: fill the T011 audit from the live session (screeninfo, pygame mode, Qt geometry, DPR, monitor origin, keyboard origin / live key and suggestion QRects) and apply **only** the T007 identity/origin/DPR transform. This is the first time real keyboard geometry can be proven.
- [ ] T029 [US2] **USER GATE — not PASS**. **USER-ACCEPTED CONTINUATION** 2026-08-24: with chin/head support, integrated GF is close to the official reference; remaining settled error is usually the intended key or one adjacent key. User accepts that residual for downstream integration. Formal T029 is **not** checked PASS. Record: `runs/_feature005/T029_parity_audit.md` (plus geometry audit / probe JSON). **Do not reconnect prediction or dwell early just to populate suggestion text.** Dwell stays disconnected until T031 then T032+. Stage D is authorized by this continuation, not by a falsified PASS.
- [X] T030 [US2] T012 STOP **not invoked**. T028/T029 did **not** show that identity/origin/DPR cannot align official filtered gaze with live QRects: Step C PASS kept `origin+dpr`; residual 0–1 adjacent key is accepted. Do not add mapper, bias, affine, extra smoothing, or `generate_points` changes to “make it look calibrated”
- [X] T031 [P] [US2] Confirm the Stage C pointing path does not stack `GazeSmoother` or `PcaFeatureSmoother` on official HeuristicFilter output (audit `gazekey/ui/virtual_keyboard.py`, `gazekey/runtime/gaze_loop.py`, `gazekey/typing/gaze_smoother.py`, `gazekey/features/feature_smoother.py`)

**Checkpoint**: T029 **USER-ACCEPTED CONTINUATION** (not PASS); T030 STOP not invoked; dwell still off. **Do not start Stage D until T029 PASS or USER-ACCEPTED CONTINUATION.** Next: T031, then T032–T041.

---

## Phase 5: Stage D — User Story 3 — Existing Typing Product (Priority: P1)

**Goal**: `GazeSample` → `MappedGazePoint` → live QRect hit-test → existing
dwell → ActionDispatcher / OS typing, preserving editing keys, prediction
context, three suggestions, and autocomplete. Invalid gaze (including
openness `<= 10`) cancels dwell and never types. No hold-last. No extra
smoothing.

**Independent Test**: After T029, dwell-select letters and editing keys, type
into an external app, confirm three suggestions, gaze-select a suggestion,
suffix + Space. Interaction matches Feature 003 / 004 closeout except gaze source.

**Depends on**: Stage C USER GATE T029 PASS **or USER-ACCEPTED CONTINUATION**

- [X] T032 [US3] Wire `GazeSample` → existing `MappedGazePoint` in `gazekey/runtime/gaze_loop.py` (and `gazekey/typing/gaze_typing_runtime.py`) using `x`, `y`, `valid` only; do not call `MapperRuntime.key_accuracy_predict_screen_xy`, Ridge, or FeatureExtractor
- [X] T033 [US3] Keep focus resolution on live layout QRects via existing `gazekey/typing/key_hit_tester.py` (`hit_test_layout_keys`) and `gazekey/layout/`; do not introduce a duplicated coordinate table
- [X] T034 [US3] Reconnect existing dwell in `gazekey/typing/dwell_engine.py` / `gazekey/typing/gaze_typing_runtime.py` / `gazekey/ui/dwell_progress_overlay.py` without changing dwell timing or treating dwell as a smoother
- [X] T035 [US3] Reconnect existing `ActionDispatcher` and OS typing in `gazekey/typing/action_dispatcher.py` / `gazekey/input/` so selected keys type into the focused external application
- [X] T036 [P] [US3] Preserve existing editing keys (Shift / Backspace / Space / Enter and other active editing controls) through current `gazekey/typing/key_action.py` / `gazekey/typing/key_semantics.py` / keyboard layout; no Feature 002/003 redesign
- [X] T037 [P] [US3] Preserve prediction context, three suggestion slots, and autocomplete suffix+Space via `gazekey/prediction/` and existing suggestion dispatch; do not retune ranking to compensate for mapping
- [X] T038 [US3] Map invalid `GazeSample` (including either openness `<= 10`) to `MappedGazePoint.valid=False` so `DwellEngine.update(..., gaze_valid=False)` cancels immediately, dwell does not complete, and no OS inject occurs; do **not** implement `GazeSmoother.filter_or_reject` hold-last
- [X] T039 [US3] Ensure the production pointing path does not apply `GazeSmoother`, `PcaFeatureSmoother`, extra EMA, or any additional smoothing after GazeFollower HeuristicFilter (`gazekey/runtime/gaze_loop.py`, `gazekey/ui/virtual_keyboard.py`)
- [X] T040 [P] [US3] Add contract tests in `tests/contract/test_gazesample_hit_test_isolation.py` that `GazeSample` → `MappedGazePoint` → `hit_test_layout_keys` never imports/calls FeatureExtractor, Ridge, PCA4, or `MapperRuntime` predict
- [X] T041 [P] [US3] Add tests in `tests/unit/test_invalid_gaze_cancels_dwell.py` that invalid samples cancel in-progress dwell and publish no `KeyAction` / OS inject

**Checkpoint**: Typing product is restored on GazeFollower gaze; invalid gaze cannot type

---

## Phase 6: Stage E — User Story 4 — Recalibrate and Shut Down (Priority: P2)

**Goal**: Keyboard Calibrate invokes official Preview + Calibration. Stop
sampling first. Hide Qt while pygame owns the screen. Resume after accepted
calibration. Clean shutdown: `stop_sampling` + `release`.

**Independent Test**: From the keyboard, recalibrate via official UI, return to
a usable keyboard, then exit and confirm camera/resources released.

**Depends on**: Stage D (T032–T041)

- [X] T042 [US4] Rewire Calibrate (`VirtualKeyboard.on_calibrate_clicked` / `GazeTypingRuntime` `on_calibrate`) in `gazekey/ui/virtual_keyboard.py` to official Preview + Calibration via `gazekey/backend/lifecycle.py`; do **not** call `_start_calibration()` or show `CalibrationOverlay`
- [X] T043 [US4] Before recalibration, set `os_inject_enabled=False`, stop consuming samples, and `stop_sampling()` in `gazekey/backend/lifecycle.py` (required; sampling→preview/calibrate raises `RuntimeError`)
- [X] T044 [US4] Hide/minimize the Qt keyboard while pygame owns the screen during official Preview/Calibration; do not keep a visible competing fullscreen; do not embed pygame in a Qt widget
- [X] T045 [US4] After accepted recalibration: `pygame.quit()`, `start_sampling()`, show keyboard, resume consume; pointing must be usable again without PCA4
- [X] T046 [US4] If calibration is not accepted (pygame window closed / unaccepted): do not continue as if a new accepted calibration existed; keep previous accepted model if one exists, otherwise fail closed without PCA4 (`gazekey/backend/lifecycle.py`, `contracts/lifecycle.md`)
- [X] T047 [US4] On application exit, stop the Qt sample consumer, `stop_sampling()` if SAMPLING, then `GazeFollower.release()`, then quit Qt (`main.py`, `gazekey/backend/lifecycle.py`, `gazekey/ui/virtual_keyboard.py` close path). Abnormal process exit or failure during official pygame Preview/Calibration MUST also attempt `release()` / camera cleanup where technically possible and MUST NOT start TrackingManager/PCA4/Ridge as recovery.
- [X] T048 [P] [US4] Add/extend tests in `tests/contract/test_calibrate_dwell_path.py` (and/or `tests/contract/test_recalibrate_official_flow.py`) so Calibrate invokes the official backend flow and does not call `_start_calibration` / `CalibrationOverlay`

**Checkpoint**: Recalibration and shutdown use sequential pygame then Qt ownership

---

## Phase 7: Stage F — User Story 5 — Integrated Acceptance (Priority: P2)

**Goal**: Independent evaluation consumes `GazeSample` + live layout only.
At least three chin/head-support USER GATE sessions on the integrated product.
Cleanup remains **blocked** until this stage passes.

**Independent Test**: Three product-condition sessions covering SC-001–SC-020
on the real keyboard and real OS typing path. Written pass/fail record exists.
Feature 004 T060 numbers are reference only and MUST NOT gate this stage.

**Depends on**: Stage E (T042–T048)

- [X] T049 [US5] Rewire `tools/evaluation/` ingest (`tools/evaluation/benchmark_runner.py`, `tools/evaluation/benchmark_session.py`, `tools/evaluation/session.py`) so scoring consumes `GazeSample` screen points + **live** layout QRects; remove `FeatureExtractor` / Ridge / `MapperRuntime.key_accuracy_predict_screen_xy` from the GazeFollower evaluation path
- [X] T050 [US5] Keep evaluation tools-only (not product enablement): product modules in `gazekey/ui/` and `gazekey/typing/` MUST NOT import `tools.evaluation` (preserve/extend `tests/contract/test_evaluation_isolation.py`)
- [X] T051 [P] [US5] Add tests in `tests/contract/test_evaluation_gazesample_isolation.py` proving evaluation scoring for this path does not import/call FeatureExtractor, Ridge, PCA4, or `pca_vL` gates
- [X] T052 [US5] Record mapped-key, row, pixel error, latency/update rate, and FR-022/FR-041 provenance (upstream commit, `base.mnn` hash, cali_mode=13, camera 0/640×480/30, geometry/DPR/origin, license, HeuristicFilter look-ahead 3) in `tools/evaluation/run_summary.py` / `tools/evaluation/experiment_record.py`; cite Feature 004 A/B `14938da0bdf0`, `34fb259ccdfd` and Feature 004 T060 `689c8a8ce90c`, `4f665467b260` as `eval_before` only
- [X] T053 [P] [US5] Replay capture remains **where practical** (gaze samples, timestamps, live layout, provenance). If a full replay writer is not implemented, live Stage F sessions remain valid. The T062 acceptance record MUST explicitly state replay availability or incompleteness. Keep captures gitignored. No raw webcam/face/eye frames may be committed. Do not add product infrastructure only to satisfy replay. Helper: `tools/evaluation/gazesample_scoring.write_gaze_replay` (optional JSONL; not wired into the product keyboard).
- [ ] T054 [US5] **USER GATE session 1** (chin/head support): full integrated sweep on the live keyboard — all letters, Space, Backspace, Shift/Enter/active controls, all three suggestion slots; record pass/fail + metrics under `runs/<session_id>/`. Also reconfirm the already-implemented Stage E recalibration flow once: official GazeFollower Preview + Calibration, return to the keyboard, resume usable gaze sampling.
- [ ] T055 [US5] **USER GATE session 2** (chin/head support): repeat the T054 control sweep on a distinct session (letters, editing, suggestions). Recalibration is **not** required in this session. One successful calibration MUST NOT decide cleanup.
- [ ] T056 [US5] **USER GATE session 3** (chin/head support): repeat the T054 control sweep; three sessions required (SC-001). Recalibration is **not** required in this session.
- [ ] T057 [US5] **USER GATE**: type `hadar` with suggestions disabled on the integrated path; record wrong-focus vs dwell; `hadar` MUST NOT override vertical-collapse or unreachable-control failures
- [ ] T058 [US5] **USER GATE**: natural blink / eye closure does **not** complete dwell and does **not** type. When the approved GazeSample validity rule produces `valid=False` (status / tracking / finite xy / openness `> 10` rule), dwell cancels immediately and there is no OS typing. Do **not** require every physical blink to produce a sampled openness `<= 10` frame (camera sampling may miss the minimum). Do **not** tune the openness threshold to make this gate pass. Do not add hold-last.
- [ ] T059 [US5] **USER GATE**: real typing into an external application through existing ActionDispatcher / OS inject
- [ ] T060 [US5] **USER GATE (Feature 005 suggestion selection)**: suggestion gaze-selection works; accepting a suggestion types the expected suffix + Space. This is not Feature 004 T060.
- [ ] T061 [P] [US5] Optional second-user smoke test before cleanup; record it or an explicit skip in `runs/_feature005/integrated_acceptance.md` (FR-035 / SC-019)
- [ ] T062 [US5] Write `runs/_feature005/integrated_acceptance.md` (pass / fail / inconclusive) covering SC-001–SC-020, SC-024, and FR-037 quiet summary. For **SC-012**, the record MUST explicitly cite Stage E recalibration evidence (T042–T047) **and** the Stage F session that reconfirmed the live official Preview + Calibration flow (T054). Also state replay availability/incompleteness per T053. Feature 004 T060 formulas MUST NOT be used as the cleanup trigger.
- [ ] T063 [US5] **Cleanup hold release**: if T062 `integrated_acceptance` is **PASS** and T054–T060 USER GATEs passed, **release** the cleanup hold so Stage G may begin at T064. If fail/inconclusive, keep the hold in place, document in `runs/_feature005/integrated_acceptance.md`, leave legacy code on disk unused, and rollback via Git only. T063 does **not** create the Git checkpoint and does **not** start deletions.

**Checkpoint**: Integrated product accepted on three chin-support sessions (T062 PASS) and cleanup hold released (T063), or cleanup stays blocked. Stage G may then begin at T064.

---

## Phase 8: Stage G — User Story 5 — Inventory cleanup (starts at T064)

**Purpose**: After T062 PASS and T063 hold release, Stage G **begins at T064**
(pre-cleanup Git checkpoint), then T065 inventory freeze, then explicit
reviewable deletions T066–T078, then T079 Feature 004 preserve check, then
T080 one-pipeline verification. Preserve all Feature 004 specs/runs/tags/commits.

**Independent Test**: Checkpoint restores pre-cleanup product. After deletions,
only GazeFollower production gaze remains; `specs/004-gaze-mapping-accuracy/`,
`runs/_feature004/`, tags `004-pca4-investigation-closeout-20260820` and
`004-pre-pivot-exact-20260820` still exist and are readable.

**Depends on (to enter Stage G / start T064)**: T062 `integrated_acceptance` **PASS** **and** T063 cleanup hold **released**. Entering Stage G does **not** depend on T064 (T064 is the first Stage G task).

- [ ] T064 [US5] Create an explicit Git pre-cleanup checkpoint/tag of the post-F product (restore point before any deletion). Tag name: `005-pre-cleanup-YYYYMMDD` using the **actual implementation date** when this task is executed. Depends on T062 PASS + T063 hold released. Do not start deletions in the same task
- [ ] T065 [US5] Freeze and verify the Stage G deletion inventory from `plan.md` against the tree (list each path; no deletions yet); confirm Feature 004 artifacts are marked preserve-only. Depends on T064 checkpoint existing

**Destructive deletions T066–T078** — each is a separate reviewable task and **must explicitly depend on all four**: T062 PASS, T063 hold released, T064 checkpoint exists, T065 inventory freeze completed. Do not start any of these until those four are done. The four cleanup gates are unchanged.

- [ ] T066 [US5] Delete or stop shipping `gazekey/tracking/` (`tracking_manager.py`, `video_capture.py`, `eye_detector.py`, `tracking_bridge.py`) from the production tree after confirming it is unused (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T067 [P] [US5] Delete `gazekey/features/` (`extractor.py`, `feature_types.py`, `feature_smoother.py`) from the production tree after confirming it is unused (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T068 [P] [US5] Delete `gazekey/mapping/` (`ridge.py`, `row_bias.py`, `base.py`, `config.py` PCA/keyboard15 constants) from the production tree after confirming it is unused (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T069 [P] [US5] Delete `gazekey/calibration/` (`session.py`, `targets.py`, `fixation_gate.py`, `quality.py`, `outliers.py`, `region_quality.py`) from the production tree after confirming it is unused (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T070 [P] [US5] Delete GazeKey calibration UI `gazekey/ui/calibration_overlay.py`, `gazekey/ui/calibration_controller.py`, `gazekey/ui/calibration_finish.py`, `gazekey/ui/camera_preview_window.py` after confirming official GF UI is the only calib path (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T071 [US5] Delete `gazekey/runtime/mapper_runtime.py` and `gazekey/runtime/tracking_controller.py` after rewiring `gazekey/runtime/gaze_loop.py` so it no longer references them (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T072 [US5] Remove `gazekey/typing/gaze_smoother.py` from the production path (delete only after confirming no tools still need it) (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T073 [US5] Remove legacy calib/mapper fields from `gazekey/ui/virtual_keyboard.py` (`_gaze_mapper`, `_gaze_bias_*`, `_feature_smoother`, `_init_calibration_on_startup` overlay path) (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T074 [US5] Remove GazeKey-owned `mediapipe` / `models/face_landmarker.task` tracking dependencies from `requirements.txt` and the tree (GazeFollower still uses its own mediapipe internally) (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T075 [US5] Remove product `--calib-mode` / `keyboard15` override as a product flag from `gazekey/app_config.py` (tools-only leftovers only if still required for historical Feature 004 replay, not product enablement) (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T076 [US5] Drop or rewrite PCA4 / u/v / ridge mapper tests (`tests/test_ridge_mapper_selection.py`, `tests/test_feature_smoother.py`, `tests/test_row_y_bias_path.py`); keep typing/prediction/layout tests (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T077 [US5] Drop or rewrite fixation-gate tests (`tests/test_fixation_head_gate.py`); keep typing/prediction/layout tests (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T078 [US5] Drop or rewrite calibration-only tests (`tests/test_calibration2_*.py`, `tests/unit/test_calibration_*.py`, `tests/test_region_quality.py`); keep typing/prediction/layout tests (**depends on T062 PASS, T063 hold released, T064 checkpoint, T065 inventory freeze**)
- [ ] T079 [US5] **Preserve Feature 004** (after T066–T078): verify `specs/004-gaze-mapping-accuracy/`, `runs/_feature004/`, tags `004-pca4-investigation-closeout-20260820` and `004-pre-pivot-exact-20260820`, and cited commits remain intact; do not resume, delete, renumber, or rewrite Feature 004 tasks
- [ ] T080 [US5] **Final one-pipeline verification** (after T079): verify one production gaze pipeline remains (`GazeFollower → GazeSample → live geometry → dwell → OS`) in `main.py` / `gazekey/backend/` / `gazekey/runtime/gaze_loop.py`, confirm no second live estimator can start, and record SC-021/SC-022 in `runs/_feature005/integrated_acceptance.md`

**Checkpoint**: One production gaze pipeline; Feature 004 history intact; pre-cleanup tag can restore the pre-G product

---

## Dependencies & Execution Order

### Stage order (binding)

```text
A (T001–T017; T012 = STOP mechanism/policy implemented+tested, not live-geometry PASS)
  → B (T018–T025)   # depends on T012 implemented/tested, not a live-coordinate PASS
  → C (T026–T031; T028 live record, USER GATE T029 not PASS / USER-ACCEPTED CONTINUATION, T030 STOP not invoked; dwell still off until T031 then T032+)
  → D (T032–T041)   # blocked until T029 PASS or USER-ACCEPTED CONTINUATION
  → E (T042–T048)
  → F (T049–T063; USER GATEs T054–T060; T062 PASS → T063 hold released)
  → G starts at T064 after T062 PASS + T063 release
      T064 checkpoint → T065 inventory freeze
      → T066–T078 deletions (each needs T062 PASS + T063 released + T064 + T065)
      → T079 Feature 004 preserve → T080 one-pipeline verify
```

### User story mapping

| Stage | Story | Priority |
|-------|--------|----------|
| A | Foundational (blocks all stories) | — |
| B | US1 Official startup | P1 |
| C | US2 Live keyboard gaze + USER GATE | P1 |
| D | US3 Typing product | P1 |
| E | US4 Recalibrate / shutdown | P2 |
| F | US5 Integrated acceptance + USER GATEs | P2 |
| G | US5 Inventory cleanup | P2 |

### User Story Dependencies

- **US1 (Stage B)**: after Stage A, including T012 **implemented and tested** (not a live-keyboard geometry PASS)
- **US2 (Stage C)**: after US1; live geometry proof is T028/T029/T030
- **US3 (Stage D)**: after US2 USER GATE **T029 PASS or USER-ACCEPTED CONTINUATION**
- **US4 (Stage E)**: after US3
- **US5 acceptance (Stage F)**: after US4; ends at T062 PASS → T063 hold released
- **US5 cleanup (Stage G)**: may **begin at T064** after T062 PASS **and** T063 hold released. T064 is the first G task, not a prerequisite for entering G. Deletions T066–T078 additionally require T064 checkpoint **and** T065 inventory freeze. Then T079, then T080.

Stories MUST NOT start in parallel across stages. `[P]` applies only within a
stage, on different files, with no incomplete prerequisite in that stage.

### Parallel opportunities (within a stage only)

- Stage A: T005 after T004 (provenance.py requires `gazekey/backend/`); T006/T007 after T004; T009 then T010 sequential on `lifecycle.py`; T014/T015/T017 after T008
- Stage B: T025 after T018–T024
- Stage C: T031 after T027
- Stage D: T036/T037; T040/T041 after T038
- Stage E: T048 after T042
- Stage F: T051/T053/T061 with evaluation rewire; USER GATE sessions T054–T056 are sequential live sessions
- Stage G: T064 after T062 PASS + T063 release; T065 after T064; T067–T070 only after T062 PASS + T063 released + T064 + T065, and only if those packages are already unused; T079 after T066–T078; T080 after T079

---

## Parallel Example: Stage A foundational tests

```text
Task: "Add pytest dependency-isolation tests in tests/contract/test_backend_isolation.py"
Task: "Add GazeSample validity unit tests in tests/unit/test_gaze_sample.py"
Task: "Add invalid-sample tests in tests/unit/test_gaze_sample_invalid.py"
```

## Parallel Example: Stage G inventory deletions (only after T062 PASS, T063 released, T064 checkpoint, and T065 inventory freeze)

```text
Task: "Delete gazekey/features/ after confirming unused"
Task: "Delete gazekey/mapping/ after confirming unused"
Task: "Delete gazekey/calibration/ after confirming unused"
```

Do **not** parallelize Stage G with Stage F. Do **not** delete Feature 004.

---

## Implementation Strategy

### MVP first (Stage A + B + C USER GATE)

1. Stage A env + adapter + isolation + geometry STOP
2. Stage B official Preview/Calibration/sampling and show the existing keyboard
3. Stage C debug dot + geometry USER GATE on that same keyboard (do not open a second keyboard)
4. **STOP and VALIDATE T029** before dwell (PASS **or USER-ACCEPTED CONTINUATION**; 2026-08-24 continuation recorded, residual 0–1 adjacent key)

### Incremental delivery

1. D: reconnect existing typing product
2. E: recalibrate + clean shutdown
3. F: three chin-support USER GATE sessions
4. G: after T062 PASS + T063 hold release: T064 checkpoint, T065 inventory freeze, then T066–T078 deletions, then T079, then T080

### Suggested MVP scope

Stages A–C through USER GATE T029 (**USER-ACCEPTED CONTINUATION**, not PASS).
That proves official GazeFollower is the startup path and that standalone
mapping survived the keyboard handoff with a known 0–1 adjacent-key residual.
Typing (D) is the next increment after T031.

---

## Notes

- [P] = different files, no incomplete dependencies **within the same stage**
- USER GATE tasks cannot be fully automated; they require the chin/head support
  and the live keyboard
- T011 is geometry-audit **schema/helper only**. Live keyboard values and
  proof remain T028/T029/T030. T012 is the geometry HARD STOP
  **mechanism/policy** (identity/origin/DPR only), implemented and tested
  in implementation Stage A. It is **not** a live-keyboard PASS.
- Isolation proof is pytest (T013, T017, T025, T040, T048, T051) plus Stage G
  ending at one pipeline (T080)
- Stage G order: T062 PASS → T063 hold released → T064 checkpoint → T065 freeze
  → T066–T078 deletions (each depends on those four) → T079 preserve Feature 004
  → T080 one-pipeline verify. T079 is preserve-only; T080 is verify-only.
- Commit after each task or logical group; do not implement in this command
