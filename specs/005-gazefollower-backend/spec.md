# Feature Specification: GazeFollower Backend Migration

**Feature Branch**: `005-gazefollower-backend`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Create Feature 005: GazeFollower Backend
Migration. Feature 004 showed that the current MediaPipe landmarks →
handcrafted u/v → PCA4/Ridge gaze pipeline has a persistent vertical
(Y-axis) accuracy problem. Multiple isolated fixes did not produce a
reliable improvement. Feature 004 is preserved at tag
004-pca4-investigation-closeout-20260820. Goal: implement a new
gaze-estimation backend based on GazeFollower and determine whether it
provides substantially better and more reliable 2D screen gaze mapping,
especially on the Y axis. Two stages: (1) validate GazeFollower as an
isolated research/evaluation backend while keeping the current PCA4
product path unchanged; evaluate with GazeKey's existing benchmark under
the chin/head-support product condition; measure key accuracy, row
accuracy, median error, Y range/compression, stability, latency, and
reachability of all keyboard regions including bottom row and suggestion
row; multiple sessions required. Do not modify typing, dwell,
suggestions, keyboard UI, blink detection, or unrelated behavior. (2)
Migrate and clean up only if GazeFollower succeeds: stop for review
before migration; after approval make GazeFollower the production gaze
backend for main.py, calibration, and evaluation; then clean obsolete
gaze-specific runtime code while preserving historical specs/, runs/,
Git tags, and Feature 004 evidence. Architecture: clean gaze-backend
boundary so downstream focus/dwell/typing consumes screen-space (x, y).
Safety: do not delete/rewrite Feature 004 history; do not remove PCA4
before the evaluation gate; keep a Git rollback checkpoint before
migration/cleanup; if GazeFollower fails, the current product remains
intact; do not introduce another gaze backend. Data: locally stored
replayable gaze captures where practical; raw webcam/eye/face data
gitignored; only derived results may be committed. Outcome A: migrate to
one clean production pipeline, or B: preserve current product and
document without destructive cleanup. Upstream: official GazeFollower
repository is the primary technical reference
(https://github.com/GanchengZhu/GazeFollower/tree/main). Do not
recreate GazeFollower from scratch or approximate it from the paper.
Record the exact upstream commit/version before implementation. If
upstream architecture conflicts with this spec, report the conflict
during planning rather than silently redesigning GazeFollower."

**Guidance**: GazeKey Constitution v1.3.0 (binding). This is a
**mapping-foundation** feature: it may replace the current gaze estimator
only after independent mapping benchmarks show a clear win, and only
after explicit review. During **Stage 1**, downstream typing stays on
the current product path so the comparison is fair. After a win,
production architecture is built **around GazeFollower**, not by
forcing GazeFollower through the historical estimator stack. Feature
004 is a **closed historical record** (paused, not completed); this
feature MUST NOT delete, renumber, or rewrite it.

## Clarifications

### Session 2026-08-20 (from Feature 004, still binding)

- **Product condition is head-stabilized**: All accuracy evaluation,
  `hadar` word checks, and repeatability runs are captured **with** the
  chin/head support. Free-head sessions are diagnostic only.
- **Accuracy must not depend on head motion**: A backend that needs the
  user's head to move in order to produce a usable vertical signal is a
  defect, not a keep.
- **Passing calibration gates is necessary, not sufficient**: Gate pass
  MUST NOT be reported as mapping success.
- **Focus vs dwell**: Wrong mapped-key focus is already a mapping
  failure, even if dwell never activates a key.
- **Word checks vs baseline**: Practical typing checks compare
  wrong-focus outcomes with suggestions unused.

### Session 2026-08-20 (Feature 005 defaults)

These are specified here so planning does not reopen Feature 004's
closed investigations as a substitute for this backend trial.

- **Two stages, hard stop between them**: Stage 1 is validation only.
  Stage 2 (production switch + cleanup) MUST NOT start until Stage 1
  meets the outperform gate **and** the user explicitly approves
  migration.
- **One candidate estimator**: GazeFollower is the only new backend in
  this feature. Do not add a third estimator, an ensemble, or a
  paper-only reimplementation.
- **Current product stays the default until migration is approved**:
  Normal application typing continues to use the current estimator
  throughout Stage 1.
- **Comparison baseline**: Every validation experiment cites Feature 004
  free-head A/B (`14938da0bdf0`, `34fb259ccdfd`) and the product-condition
  T060 pair (`689c8a8ce90c`, `4f665467b260`) as `eval_before`. The
  current product tree is the Feature 004 closeout
  (`004-pca4-investigation-closeout-20260820`).
- **Multiple sessions**: One successful calibration is not a keep.
  Stage 1 requires **at least three** product-condition calibration +
  evaluation sessions on the candidate, plus the same primary metrics
  reported for each.
- **"Clearly outperforms" is relative to the current backend, then
  review**: See SC-001–SC-006. Historical 67% / 55 px / 80% row floors
  remain **reference** bars, not an automatic migration trigger.
- **Suggestion-row reachability is measured, not used to hide letter
  error**: Feature 003 suggestion keys are a required **reachability**
  slice in Stage 1. They MUST NOT replace letter / editing mapped-key
  accuracy as the primary Stage 1 comparison (SC-001). Before
  production cleanup, all three suggestion slots are still part of
  the full interactive-control sweep (SC-017).
- **Upstream source of truth**: The official GazeFollower repository is
  the implementation reference. Conflicts with this spec are reported
  at planning time; they are not silently papered over.
- **Do not assume `keyboard15`**: GazeKey's existing calibration layout
  is **not** the default GazeFollower protocol. See Session
  2026-08-20 (calibration, geometry, reachability).

### Session 2026-08-20 (calibration, geometry, reachability)

User-provided decisions (encoded; no further questions asked):

- Q: How must Stage 1 and pre-migration acceptance cover the real keyboard? → A: Stage 1 evaluates reachability from the **actual runtime layout**. Before production migration/cleanup, a **full interactive-control sweep** covers every active control: all letter keys, Space, Backspace, Enter/Shift and other active editing controls, and **all three suggestion slots**. Targets and hitboxes come from **live runtime layout geometry**, not a duplicated hard-coded coordinate list.
- Q: Which calibration protocol does GazeFollower use? → A: Do **not** assume GazeKey `keyboard15`. Planning inspects the official GazeFollower calibration implementation (supported **5 / 9 / 13-point** modes, default mode, exact target placement, collection timing/sampling, and calibration model). Stage 1 starts from **one pinned official/native** protocol. Calibration MUST spatially cover the complete product interaction range, especially **top-to-bottom Y**. Calibration and benchmark remain **logically independent** so training-target overlap cannot falsely inflate evaluation.
- Q: What is the coordinate/geometry contract? → A: Planning MUST verify that GazeFollower screen coordinates, Windows/Qt coordinates, keyboard window geometry, hitboxes, calibration targets, benchmark targets, and suggestion-row rectangles use the **same screen coordinate system**. Audit DPI / display scaling, `devicePixelRatio`, screen resolution, monitor selection/origin, window position, and any screen/camera physical-geometry configuration used by upstream. Do **not** copy upstream hard-coded camera/screen constants without proving they apply.
- Q: May current-estimator quality gates accept or reject GazeFollower calibration? → A: **No.** Current-estimator-specific gates/features (including `pca_vL` and its 0.15 threshold) MUST NOT accept or reject GazeFollower calibration. Candidate validity/calibration semantics come from the candidate backend. Independent GazeKey mapping evaluation remains the **acceptance authority**.
- Q: How are filtering, timestamps, and stale predictions handled? → A: Audit GazeFollower's own filtering versus GazeKey smoothing so filtering is not applied twice by accident. Record raw and filtered gaze where available, frame / prediction / target timestamps, update rate, and end-to-end latency. Benchmark scoring MUST NOT measure stale predictions from the previous target.
- Q: What must every candidate run record for reproducibility? → A: Upstream commit, model/checkpoint hash, calibration mode and target positions, camera ID / resolution / FPS, preprocessing / mirroring, screen / DPI geometry, and relevant runtime config. Replayable local captures include enough information for offline investigation and remain **gitignored**.
- Q: May shared code bake this developer's anatomy or calibration? → A: Feature 005 may be validated primarily with the current developer, but production architecture MUST NOT bake user-specific anatomical or calibration constants into shared code. GazeFollower personalization/calibration is **session/user-specific**. If practical, a **second-user smoke test** runs before final production migration.
- Q: When is a backend production-ready? → A: After the architecture-win gate and **before cleanup**, require production-level validation of **both** independent mapping metrics **and** the full real keyboard path. Regional reachability or average correlations improving is **not** enough.

### Session 2026-08-20 (legacy isolation and production contract)

User-provided decisions (encoded; no further questions asked):

- Q: May the GazeFollower candidate reuse the current estimator stack? → A: **No.** GazeFollower is a genuinely independent pipeline from the official repository. The current estimator is a **historical baseline**, not a blueprint or component. Stage 1 MUST NOT depend on or reuse estimator-specific pieces (handcrafted u/v or FeatureExtractor gaze semantics, PCA/PCA4, Ridge, `pca_vL`/`pca_vR`, PCA-specific gates including 0.15, legacy aggregation/clamps/outlier logic/vertical normalization, or legacy estimator calibration assumptions/constants). Candidate preprocessing, eye/face preparation, inference, calibration/personalization, validity, and filtering follow official GazeFollower unless planning documents a real integration conflict. Existing GazeKey code may be reused **only** when backend-agnostic (live keyboard geometry, independent benchmark scoring, product interaction, generic display/camera that does not alter GazeFollower preprocessing). Planning MUST publish a dependency audit (official components used; GazeKey modules allowed; forbidden legacy gaze modules; exact handoff). Where practical, an import/isolation test MUST fail if the candidate starts depending on the handcrafted/PCA4 stack. If GazeFollower conflicts with existing calibration/tracking, **adapt the integration around GazeFollower** rather than routing it through the old estimator.
- Q: Is the production prediction contract permanently `(x, y)` only? → A: **No.** Stage 1 keeps downstream behavior stable enough for a fair estimator comparison. Planning MUST inspect official GazeFollower outputs and decide whether the eventual backend-agnostic production contract stays `(x, y)` or also preserves useful semantics (validity, timestamp, confidence/quality, raw/filtered gaze). Downstream redesign (smoothing, validity, timing, focus stability, dwell integration) MAY occur **only after** the candidate has passed the required gates, **only** for documented technical reasons, and MUST NOT be used in Stage 1 to hide poor accuracy or inflate the benchmark. Fair isolated comparison first; if GazeFollower wins, build the cleanest production architecture around it rather than forcing it into the historical estimator architecture.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Try a New Gaze Estimator Without Changing Typing (Priority: P1)

The developer can run GazeFollower as an isolated research/evaluation
path while the shipped product still uses the current gaze estimator.
The candidate is calibrated with the **pinned official GazeFollower
protocol** (not assumed `keyboard15`). The existing mapping **scoring**
method then scores screen gaze against **live** key hitboxes: intended
key, row, and pixel error under the chin/head support. Typing, dwell,
suggestions, keyboard layout, and blink behavior stay as they are.

**Why this priority**: Feature 004 showed the current estimator's
vertical mapping is not reliably fixable by small internal changes.
The first value of Feature 005 is a fair trial of a different estimator
without risking the working Feature 003 product.

**Independent Test**: With the product still on the current estimator,
complete a candidate session that uses the pinned native calibration
protocol, then developer evaluation against live layout hitboxes, with
the chin/head support. Confirm evaluation artifacts exist for the
candidate, that current-estimator gates did not accept/reject that
calibration, and that launching the normal product still uses the
unchanged current estimator.

**Acceptance Scenarios**:

1. **Given** the current product estimator is the default, **When** the
   developer runs candidate evaluation, **Then** GazeFollower produces
   screen-space gaze that the existing mapping benchmark can score, and
   the product typing path is not switched.
2. **Given** a candidate evaluation session, **When** it finishes,
   **Then** a simple run summary reports pass/fail plus primary mapping
   metrics (mapped-key, median error, row) without requiring the
   evaluation tool to become part of product typing.
3. **Given** Stage 1 is in progress, **When** the user launches the
   normal application, **Then** dwell typing, suggestions, keyboard UI,
   and blink handling behave as on the Feature 004 closeout product.
4. **Given** GazeFollower cannot start (missing model, dependency, or
   device), **When** the developer attempts candidate evaluation,
   **Then** the failure is reported and the current product remains
   usable.
5. **Given** Stage 1 candidate code, **When** its imports and calls are
   inspected, **Then** it does not use the historical estimator's
   handcrafted features, PCA/PCA4, Ridge, or PCA-specific gates; it
   only reuses backend-agnostic GazeKey pieces (live layout, scoring,
   product interaction, generic camera/display).

---

### User Story 2 - Know Whether Vertical Mapping and Whole-Keyboard Reach Actually Improved (Priority: P1)

The developer can tell, from **multiple** product-condition sessions
rather than one lucky calibration, whether the candidate maps gaze to
the intended keys more accurately and more reliably than the current
estimator — especially vertically — and whether gaze can reach **every
active product control** on the live keyboard, not only the home row.

**Why this priority**: Feature 004's product-condition references
already showed usable horizontal mapping and ignored vertical range.
A backend that tidies correlations but still ignores Y, or that cannot
reach Space / suggestions / other live controls, is not a migration
candidate.

**Independent Test**: Capture at least three chin/head-support
sessions using the **pinned official GazeFollower calibration
protocol**, then score gaze against **live runtime layout** hitboxes
(not a hard-coded duplicate list). Compare mapped-key, median error,
row, Y range/compression (or equivalent “is Y used?” measure),
stability, latency, and per-control reachability to the Feature 004
`eval_before` sessions. One session MUST NOT decide keep. Calibration
targets and benchmark targets MUST be treated as independent sets.

**Acceptance Scenarios**:

1. **Given** three product-condition candidate sessions, **When**
   results are compared to Feature 004 T060 and A/B, **Then** mapped-key
   accuracy, median error, and row accuracy are reported per session
   and as a set, including session-to-session spread.
2. **Given** those sessions, **When** vertical behavior is scored,
   **Then** the record states whether predicted Y actually travels with
   the target (range / compression / equivalent), not only whether
   horizontal error improved.
3. **Given** the Feature 003 keyboard as currently laid out at runtime,
   **When** Stage 1 evaluation runs, **Then** reachability is scored
   using that session's live key and suggestion-slot rectangles,
   covering all letter keys, Space, Backspace, Enter/Shift and other
   active editing controls, and all three suggestion slots — reported
   separately from the letter + editing primary mapped-key rate.
4. **Given** live candidate inference, **When** latency/stability are
   recorded, **Then** the tester can say whether gaze updates remain
   usable for existing dwell (not “accurate but seconds late”), and
   that a target's score used predictions from **that** target's
   window, not the previous one.
5. **Given** session 1 looks strong and session 2 or 3 does not,
   **When** the Stage 1 decision is made, **Then** the outcome is
   **inconclusive** or **fail**, not migrate — one calibration is not
   enough.

---

### User Story 3 - Compare Fairly Now; Do Not Freeze the Old Contract Forever (Priority: P1)

During Stage 1, the product typing path stays as it is so GazeFollower
can be compared without changing dwell, smoothing, or focus rules to
make the candidate look better. After a win, the production gaze
contract is **not** permanently locked to today's screen-point-only
shape: planning inspects official GazeFollower outputs and may preserve
validity, timestamps, confidence, and raw vs filtered gaze if that
makes a cleaner architecture.

**Why this priority**: A fair trial needs a stable downstream. A good
production architecture must be built around the winning estimator, not
forced through the historical stack.

**Independent Test**: In Stage 1, confirm product typing still uses the
current estimator and that candidate evaluation scores GazeFollower
screen gaze against live hitboxes without changing dwell/smoothing to
help the score. In planning (and only after a gate for implementation),
record the chosen production prediction contract and why.

**Acceptance Scenarios**:

1. **Given** Stage 1, **When** the keyboard resolves focus for
   **product typing**, **Then** behavior matches the Feature 004
   closeout path (current estimator, existing dwell/smoothing) and
   does not call GazeFollower.
2. **Given** Stage 1 candidate evaluation, **When** mapped-key is
   scored, **Then** scoring uses the candidate's screen gaze and live
   layout hitboxes, without extra GazeKey estimator stages or extra
   smoothing added to hide error.
3. **Given** a screen gaze sample from the candidate, **When**
   evaluation maps it to a key, **Then** the result depends on that
   sample and live geometry, not on a copied coordinate table and not
   on PCA4/Ridge internals.
4. **Given** Stage 2 is approved, **When** production is integrated,
   **Then** downstream uses the planning-chosen backend-agnostic
   contract (at least screen position; plus validity / timestamp /
   confidence / raw-vs-filtered if official outputs justify them), in
   the same screen system as the keyboard window, and any smoothing /
   validity / dwell redesign is documented and was **not** used to
   inflate Stage 1.

---

### User Story 4 - Switch Production Gaze Only After a Clear Win and Review (Priority: P2)

If GazeFollower clearly outperforms the current backend on the Stage 1
gate, work **stops for review**. After approval, the normal application,
calibration, and evaluation all use GazeFollower as the production gaze
backend. **Before cleanup**, production-level validation covers both
independent mapping metrics and a full interactive sweep of every
active keyboard control on the live layout. A Git rollback checkpoint
exists immediately before the switch so the current product can be
restored.

**Why this priority**: Migration is the payoff, but Feature 004's
lesson is not to replace a working (if inaccurate) product path without
a measured gate and a way back. Architecture-win on Y or regional
reachability is not by itself production-ready.

**Independent Test**: After the Stage 1 record shows the outperform
gate and written approval, switch production to the candidate, run
calibration + independent mapping evaluation + a `hadar` check with
suggestions unused + the full live-layout control sweep, and confirm
the normal application no longer depends on the old estimator.
Confirm the pre-migration Git checkpoint can restore the old path.
Cleanup MUST NOT start until that production-level validation is
recorded.

**Acceptance Scenarios**:

1. **Given** Stage 1 has not met the outperform gate, **When** someone
   proposes switching the normal application, **Then** production stays on the
   current estimator.
2. **Given** Stage 1 meets the gate, **When** migration is about to
   start, **Then** work stops until review approval, and a Git
   checkpoint of the pre-migration product exists.
3. **Given** approval, **When** Stage 2 production switch lands but
   cleanup has not started, **Then** the normal application,
   calibration, and evaluation all use GazeFollower for screen gaze,
   independent mapping metrics are recorded, **and** every active
   control on the live keyboard (letters, Space, Backspace,
   Enter/Shift/active editing, all three suggestion slots) has been
   swept from live hitboxes.
4. **Given** only regional reachability or average correlations
   improved, **When** the full keyboard path still misses active
   controls or mapping metrics fail, **Then** the backend is **not**
   production-ready and cleanup MUST NOT start.
5. **Given** the pre-migration checkpoint, **When** rollback is needed,
   **Then** the current (pre-GazeFollower-production) product is
   recoverable without reconstructing it from memory.

---

### User Story 5 - Leave One Clean Gaze Path, or Leave the Current Product Intact (Priority: P2)

If migration is approved, obsolete current-estimator runtime, flags,
tests, and dependencies that are no longer needed are removed so only
one production gaze pipeline remains — without erasing Feature 004
history. If GazeFollower does **not** prove better, none of that
cleanup happens: the current product stays, and the negative result is
written down.

**Why this priority**: Cleanup without a win would destroy the only
shipping estimator. Cleanup after a win avoids carrying two gaze stacks
forever.

**Independent Test**: On the fail path, show the product tree still
matches the Feature 004 closeout estimator and a written Stage 1
result exists. On the success path after approval, show production has
one gaze backend and `specs/004-*`, `runs/` Feature 004 artifacts, and
the closeout tag still exist.

**Acceptance Scenarios**:

1. **Given** Stage 1 fails or is inconclusive, **When** the feature
   closes, **Then** the current product estimator remains the default,
   GazeFollower is not the production path, and no destructive cleanup
   of the current estimator has occurred.
2. **Given** Stage 2 migration is approved, production-level
   validation has passed, and cleanup is complete, **When** leftover
   current-estimator product code is removed, **Then** each deletion
   is an explicit approved task, and Feature 004 specs, runs, tags,
   and evidence remain.
3. **Given** either outcome, **When** a later reader opens the repo,
   **Then** they can tell which estimator is production and where the
   Feature 004 record lives.

---

### Edge Cases

- GazeFollower model files, weights, or dependencies are missing:
  evaluation fails closed; product typing is unchanged.
- A candidate session is blocked before evaluation (candidate
  calibration validity, tracker loss, user abort): it counts toward
  “not a single lucky session” and MUST NOT be treated as a keep.
  Current-estimator gates such as `pca_vL` / 0.15 MUST NOT be the
  blocker.
- Candidate accuracy is better horizontally but Y remains ignored
  (predicted Y barely moves as targets move from top row to Space):
  **fail** the outperform gate even if mapped-key ticked up on the
  home row.
- Candidate reaches letter keys but not Space, Backspace, Enter,
  Shift, or any of the three suggestion slots on the **live** layout:
  **fail** reachability; do not migrate.
- Evaluation uses a duplicated hard-coded coordinate list instead of
  live runtime hitboxes: the run is invalid for Stage 1 and Stage 2.
- Calibration targets overlap the benchmark set and that overlap is
  used as the primary mapped-key rate: the run is invalid; report
  calib-location repeatability separately.
- Candidate is accurate but too slow for existing dwell: **fail**
  (not interactive).
- Benchmark scores a sample against the previous target because
  timestamps were ignored: the run is invalid.
- GazeKey smoothing and GazeFollower filtering are stacked without
  an audit: treat as a defect until proven single-filter.
- Replay capture is unavailable (disk, privacy, or camera-only mode):
  live evaluation may still proceed; lack of replay is recorded, not
  silently skipped as if replay existed.
- Raw webcam / face / eye frames must never be committed; if a capture
  is saved locally, it stays gitignored.
- Official GazeFollower 5/9/13-point protocol cannot cover the full
  product Y range, cannot stay independent of the benchmark, or cannot
  run with GazeKey's minimal fixation UI / Windows webcam setup:
  **stop and report at planning** — do not invent a different
  estimator and do not silently fall back to `keyboard15`.
- Upstream ships hard-coded camera/screen constants (focal length,
  screen cm, origin): they MUST NOT be copied until proven to match
  this machine's DPI, `devicePixelRatio`, monitor origin, and window
  position.
- Shared product code contains this developer's anatomical or
  calibration constants: **defect**; session/user-specific data only.
- Feature 004 tasks remain unchecked/paused: do not resume them as
  part of this feature and do not rewrite them to look completed.
- Two estimators MUST NOT be blended in one live predict (no averaging
  current features with GazeFollower, no fallback cascade in this
  feature).
- Stage 1 candidate imports or calls FeatureExtractor gaze semantics,
  PCA/PCA4, Ridge, `pca_vL`/`pca_vR`, or PCA-specific gates: **defect**;
  the run is not a valid GazeFollower trial.
- Camera/display helpers used by the candidate alter GazeFollower
  preprocessing (mirroring, crop, color) away from official behavior
  without a documented conflict: **defect**.
- Stage 1 adds extra GazeKey smoothing, validity, or dwell changes so
  the candidate benchmark looks better: **defect**; those changes are
  allowed only after the gate, with documented technical reasons.
- Production is designed as “GazeFollower features fed into Ridge/PCA4”:
  **forbidden**; if integration conflicts, wrap GazeKey around
  GazeFollower, not the reverse.

## Requirements *(mandatory)*

### Functional Requirements

**Stage 1 — validate, do not switch the product**

- **FR-001**: System MUST integrate GazeFollower as a **genuinely
  independent** research/evaluation gaze pipeline based on the official
  repository, adapted through a GazeKey handoff rather than
  reimplemented from the paper or copied into unrelated modules. The
  current estimator is a **historical baseline**, not a blueprint or
  component of the candidate (see FR-030).
- **FR-002**: Before evaluation code is treated as the candidate path,
  planning/implementation MUST record the **exact upstream
  commit/version** of GazeFollower used. Every candidate run MUST also
  record the provenance in FR-028.
- **FR-003**: During Stage 1, the current product gaze path MUST remain
  the default for the normal application. Candidate evaluation MUST NOT
  silently replace it.
- **FR-004**: During Stage 1, typing, dwell, suggestions, keyboard UI,
  blink detection, and unrelated Feature 002/003 behavior MUST NOT be
  modified to compensate for estimator error, to hide poor gaze
  accuracy, or to inflate benchmark results. After the candidate has
  passed the required gates, downstream redesign (smoothing, validity
  handling, timing, focus stability, or dwell integration) MAY occur
  **only** for documented technical reasons arising from official
  GazeFollower outputs (FR-032).
- **FR-005**: Candidate evaluation MUST use GazeKey's existing mapping
  **scoring method** (mapped-key focus inside the intended live rect +
  focus stability, held-out vs calibration-location reporting, median
  error, row accuracy) under the **chin/head-support product
  condition**. Evaluation **targets and hitboxes MUST come from the
  live runtime keyboard layout** of that session (letter keys, editing
  controls, and suggestion-row rectangles). They MUST NOT come from a
  duplicated hard-coded coordinate list.
- **FR-006**: Candidate evaluation MUST also record vertical mapping
  quality (whether predicted Y travels with target Y: range and/or
  compression, or an equivalent documented “Y used” measure),
  stability, update rate, and end-to-end latency. Raw and filtered
  gaze MUST be recorded where the candidate exposes both. Frame,
  prediction, and target timestamps MUST be recorded so a sample is
  scored against the target that was actually shown, not the previous
  one.
- **FR-007**: Stage 1 MUST evaluate reachability from the **actual
  runtime layout** across the complete product interaction range,
  especially top-to-bottom Y. The evaluated live controls MUST include
  **all letter keys**, **Space**, **Backspace**, **Enter / Shift and
  other active editing controls**, and **all three suggestion slots**.
  Suggestion-slot scores remain a reachability/diagnostic slice for
  the Stage 1 primary comparison (SC-001 still uses letter + editing);
  they are **required** members of the pre-cleanup interactive-control
  sweep (FR-029).
- **FR-008**: Stage 1 MUST include **at least three** product-condition
  calibration + evaluation sessions on the candidate. A single
  successful session MUST NOT be treated as proof.
- **FR-009**: Each Stage 1 session MUST produce a simple pass/fail
  summary with primary metrics (Constitution Principles VII and X).
  Developer evaluation remains infrastructure only and MUST NOT
  participate in product enablement (same isolation rule as Feature
  004).
- **FR-010**: Calibration fixation UI hosted by GazeKey MUST remain
  limited to the target dot and optional simple progress; no metrics
  or debug text during fixation (Principle XI). Stage 1 MUST **not**
  assume GazeKey `keyboard15`. Planning MUST inspect the official
  GazeFollower calibration implementation — supported **5 / 9 / 13-point**
  modes, default mode, exact target placement, collection
  timing/sampling, and calibration model — and Stage 1 MUST start
  from **one pinned official/native protocol**. That protocol MUST
  spatially cover the complete product interaction range, especially
  top-to-bottom Y. Calibration and the mapping benchmark MUST remain
  **logically independent**: training-target overlap MUST NOT be used
  as the primary mapped-key rate. If the native protocol conflicts
  with Principle XI, with full-product Y coverage, with benchmark
  independence, or with the Windows product setup, planning MUST
  record the conflict and stop — not silently redesign GazeFollower
  and not silently fall back to `keyboard15`.

**Gaze-backend boundary**

- **FR-011**: **Stage 1** keeps the product typing path on the current
  estimator so the comparison is fair. Candidate **evaluation** consumes
  GazeFollower screen gaze against live keyboard geometry without
  extra GazeKey estimator stages. Planning MUST verify that
  GazeFollower output, Windows/Qt coordinates, keyboard window
  geometry, live hitboxes, calibration targets, benchmark targets, and
  suggestion-row rectangles share **one screen coordinate system**,
  including DPI / display scaling, `devicePixelRatio`, screen
  resolution, monitor selection/origin, window position, and any
  upstream screen/camera physical-geometry settings. Upstream
  hard-coded camera or screen constants MUST NOT be copied unless
  proven to apply on this machine.
- **FR-012**: This feature MUST NOT introduce a third gaze backend, an
  ensemble, or a blended predict path (no GazeFollower-plus-PCA4
  hybrid).
- **FR-030**: During Stage 1 the candidate MUST NOT depend on or reuse
  legacy estimator-specific components, including: handcrafted u/v
  features or FeatureExtractor gaze semantics; PCA / PCA4; Ridge
  mapping; `pca_vL` / `pca_vR`; PCA-specific quality gates such as the
  0.15 gate; legacy feature aggregation, clamps, outlier logic, or
  vertical normalization; legacy estimator-specific calibration
  assumptions or constants. Candidate preprocessing, eye/face
  preparation, model inference, calibration/personalization, validity
  semantics, and filtering MUST follow official GazeFollower unless
  planning identifies and documents a real integration conflict.
  Existing GazeKey code MAY be reused **only** when backend-agnostic:
  runtime keyboard geometry, independent benchmark scoring, product
  interaction logic, and generic display/camera infrastructure that
  does **not** alter GazeFollower preprocessing. If GazeFollower
  conflicts with existing calibration/tracking architecture, the
  integration MUST be adapted **around GazeFollower**, not routed
  through the old estimator.
- **FR-031**: Planning MUST include a **dependency audit** that
  explicitly identifies: (1) official GazeFollower components used,
  (2) existing GazeKey modules the candidate may reuse, (3) legacy
  gaze modules the candidate is **forbidden** to import or call, and
  (4) the exact handoff between the candidate and GazeKey. Where
  practical, an import/dependency isolation test MUST fail if the
  candidate starts depending on the PCA4 / handcrafted-feature stack.
- **FR-032**: Planning MUST inspect official GazeFollower outputs and
  decide the eventual **backend-agnostic production prediction
  contract**. It MUST NOT be permanently locked to today's
  `(x, y)`-only shape. The contract MUST include screen position and
  MAY also preserve useful official semantics such as validity,
  timestamp, confidence/quality, and raw vs filtered gaze. That
  decision is recorded in the plan. Downstream changes that implement
  it MUST wait until after the required gates (FR-004).

**Stage 1 decision**

- **FR-013**: If the candidate does not meet the outperform gate
  (Success Criteria Stage 1), the current product MUST remain intact
  and recoverable. The result MUST be documented. Destructive cleanup
  of the current estimator MUST NOT occur.
- **FR-014**: If the candidate meets the outperform gate, work MUST
  **stop for review** before any production switch or cleanup.

**Stage 2 — migrate then clean, only after approval**

- **FR-015**: After explicit approval, GazeFollower MUST become the
  production gaze backend used by the normal application, calibration,
  and evaluation, integrated through the production contract chosen in
  FR-032 — not by feeding GazeFollower into PCA4/Ridge.
- **FR-016**: A Git rollback checkpoint MUST exist **before**
  production migration and before cleanup, restoring the pre-migration
  product.
- **FR-017**: After a successful production switch **and**
  production-level validation (FR-029), obsolete current-estimator
  runtime, configuration, flags, tests, and dependencies that are no
  longer needed MUST be removed so one production gaze pipeline
  remains. Each deletion MUST be its own approved task (Principle IX).
  Cleanup MUST NOT start merely because Stage 1 regional reachability
  or average correlations improved.
- **FR-018**: Cleanup MUST NOT delete, rewrite, or renumber Feature
  004 specifications, run artifacts, Git tags, or investigation
  records. Historical `specs/` and `runs/` remain auditable.
- **FR-019**: Feature 004's paused A–F task sequence MUST NOT be
  resumed, completed, or rewritten as if it had finished. Feature 005
  replaces that continuation with this backend trial.

**Safety, data, and logging**

- **FR-020**: The current estimator MUST NOT be removed from the
  product tree until Stage 1 has passed and Stage 2 migration is
  approved.
- **FR-021**: Where practical, the system MUST support locally stored
  **replayable** captures of a session so the same session can be
  analyzed offline. Captures MUST include enough information for
  offline investigation (gaze samples, timestamps, live layout
  geometry, calibration mode/targets, and the FR-028 provenance
  fields). Raw webcam, eye, and face data MUST remain local and
  gitignored. Only derived results (summaries, metrics, written
  records) MAY be committed.
- **FR-022**: Normal product use MUST keep terminal output short;
  optional verbose output is for investigation (Principle X).
- **FR-023**: If upstream GazeFollower architecture, license,
  dependencies, or runtime requirements conflict with this
  specification or with the constitution (for example calibration UX,
  5/9/13-point coverage vs full-product Y, platform, or mapping
  isolation), planning MUST record the conflict and stop for a
  decision. Silently redesigning GazeFollower to fit the historical
  estimator, or routing GazeFollower through that estimator, is out of
  scope. Adapt GazeKey around GazeFollower.
- **FR-024**: Mapping accuracy remains independently measured.
  Internal training losses, vendor demo metrics, regional
  reachability alone, or average correlations MUST NOT be the sole
  acceptance criteria (Principle II).
- **FR-025**: Current-estimator-specific quality gates and features
  (including `pca_vL` and its 0.15 threshold, and other PCA4-only
  checks) MUST NOT be used to accept or reject GazeFollower
  calibration. Candidate validity and calibration semantics come from
  the candidate backend. Independent GazeKey mapping evaluation
  remains the acceptance authority for mapping success.
- **FR-026**: Planning/implementation MUST audit GazeFollower's own
  filtering against GazeKey smoothing so filtering is not applied
  twice by accident. The audit result MUST be recorded. Stage 1 MUST
  not add GazeKey smoothing on top of GazeFollower to improve scores.
  After a win, the live product path MUST use one intentional filter
  policy consistent with FR-032.
- **FR-027**: Shared product code MUST NOT bake user-specific
  anatomical or calibration constants. GazeFollower
  personalization/calibration MUST be session- or user-specific data,
  not compiled-in defaults for the current developer. Feature 005 MAY
  be validated primarily with the current developer. If practical, a
  **second-user smoke test** MUST run before final production
  migration; if it is skipped, the Stage 2 record MUST say so.
- **FR-028**: Every candidate run MUST record: upstream commit,
  model/checkpoint hash, calibration mode and target positions,
  camera ID / resolution / FPS, preprocessing / mirroring, screen /
  DPI geometry (including `devicePixelRatio` and monitor origin), and
  relevant runtime config.
- **FR-029**: After the architecture-win / Stage 1 gate and review
  approval, and **before cleanup**, the production path MUST pass
  **both** independent mapping metrics **and** a full
  interactive-control acceptance sweep on the live runtime layout
  covering every active keyboard control listed in FR-007. A backend
  is not production-ready merely because regional reachability or
  average correlations improved.

### Key Entities

- **Current estimator**: The Feature 004 closeout production gaze
  path (landmark-based handcrafted features and the existing mapping
  stack). **Historical baseline** for comparison. Default product path
  until Stage 2 is approved. Not a component of the GazeFollower
  candidate.
- **Candidate estimator**: The official GazeFollower system as an
  independent pipeline, handed off to GazeKey only at a documented
  boundary, used for Stage 1 evaluation and — only if approved —
  Stage 2 production.
- **Gaze-backend handoff**: The documented Stage 1 join between
  GazeFollower outputs and backend-agnostic GazeKey pieces (live
  layout, independent scoring). Not a reuse of PCA4/Ridge.
- **Production prediction contract**: The backend-agnostic record
  production downstream will consume after a win. Chosen in planning
  from official GazeFollower outputs. Always includes screen position;
  may include validity, timestamp, confidence/quality, and
  raw vs filtered gaze. **Not** permanently locked to `(x, y)` only.
- **Pinned native calibration protocol**: The single official
  GazeFollower calibration mode (one of upstream's 5 / 9 / 13-point
  modes, chosen after inspecting the official default, placement,
  timing, and model) used for all Stage 1 sessions until a later
  measured experiment changes it. Not GazeKey `keyboard15` unless
  planning proves they are the same protocol.
- **Live runtime layout**: The keyboard and suggestion-slot
  rectangles actually shown in that session (window position, DPI,
  hitboxes). The source of evaluation targets; not a stored duplicate
  coordinate table.
- **Interactive-control sweep**: Pre-cleanup evaluation of **every**
  active product control from live hitboxes: all letters, Space,
  Backspace, Enter/Shift/active editing, all three suggestion slots.
- **Mapped gaze**: Predicted screen/keyboard position used for key
  focus. Sealed upstream for typing. Must share the audited screen
  coordinate system.
- **Mapped key (focus)**: Keyboard control identified from mapped gaze
  via **live** key-hit geometry, before dwell.
- **Product-condition session**: One calibration + evaluation (and
  `hadar` / sweep when required) captured **with** the chin/head
  support.
- **Stage 1 record**: Written comparison of the candidate against
  Feature 004 `eval_before` sessions, including Y behavior, live-layout
  reachability, stability, latency, provenance, and a keep / fail /
  inconclusive decision — never migrate without review.
- **Run provenance**: Per-run record of upstream commit,
  model/checkpoint hash, calibration mode/targets, camera
  ID/resolution/FPS, preprocessing/mirroring, screen/DPI geometry, and
  runtime config.
- **Replay capture**: Local, gitignored recording sufficient to replay
  a session offline (including timestamps and live layout); derived
  metrics may be committed.
- **Pre-migration checkpoint**: Git commit/tag of the product
  immediately before Stage 2 switch/cleanup.
- **Feature 004 record**: Specs, runs, and tags including
  `004-pca4-investigation-closeout-20260820` and
  `004-pre-pivot-exact-20260820`; read-only history for this feature.

## Success Criteria *(mandatory)*

All Stage 1 and Stage 2 mapping measurements use the **chin/head
support**. Free-head runs MUST NOT decide migration.

Developer evaluation may measure these outcomes; it remains outside
product typing.

Historical 67% mapped-key / 55 px median / 80% row figures remain
**reference floors** from the mapping foundation. They are comparison
bars, not an automatic Feature 005 migration trigger.

### Stage 1 — validation gate (must pass before any review-for-migration)

- **SC-001**: **Mapped-key accuracy (primary)** — On at least **three**
  product-condition candidate sessions, mean intended-key focus rate
  on the letter + editing/control evaluation set **beats the Feature
  004 product-condition reference** by more than that pair's own
  session noise (**6 percentage points** above the better T060 session
  of 29%, i.e. mean **> 35%**), and no candidate session falls below
  the worse T060 session (23%) by more than that 6 pp envelope.
- **SC-002**: **Spatial error** — Mean median error on that same set
  is **better** than the better T060 median (78.2 px) by more than
  T060's 2.8 px envelope (mean **< 75.4 px**). Pixel error alone is
  not enough if Y is still ignored (SC-004) or keys are still missed
  (SC-001).
- **SC-003**: **Row accuracy** — Mean row correctness **beats** the
  better T060 row rate (39%) by more than T060's 4 pp envelope (mean
  **> 43%**), because vertical failure in Feature 004 showed up as
  wrong-row focus.
- **SC-004**: **Vertical mapping is actually used** — On **every**
  Stage 1 session, predicted Y must travel with target Y rather than
  stay nearly constant. Operational bar, matching Feature 004's
  last keep test for this symptom: slope of vertical error vs target
  Y is **better than −0.80** (a slope of −1 means predicted Y is
  constant). Equivalent documented compression/range evidence MAY
  supplement; it MUST NOT replace this “Y is used” requirement.
- **SC-005**: **Live-layout reachability** — Stage 1 scores the
  **actual runtime layout**, not a hard-coded duplicate list. All
  letter keys, Space, Backspace, Enter/Shift and other active editing
  controls, and all three suggestion slots are evaluated. A session
  that never places mapped gaze on the bottom band or suggestion band
  (predicted Y collapsed to one letter row), or that skips those live
  controls, fails this criterion even if home-row letters look
  improved. Suggestion-slot hits MUST NOT replace letter + editing as
  the SC-001 primary rate.
- **SC-006**: **Repeatability, latency, and freshness** — The three
  sessions agree on the direction of SC-001–SC-004 (not one win and
  two collapses). Gaze updates remain usable for existing dwell
  (continuous pointing, not multi-second lag). Measured latency,
  update rate, and timestamps are recorded on each session. A
  target's score MUST use predictions from that target's time window,
  not the previous target.
- **SC-007**: **No product regression during Stage 1** — Normal
  application typing still uses the current estimator; Feature 003
  dwell, suggestions, and keyboard UX still work without GazeFollower
  running. Stage 1 does not add downstream smoothing/validity/dwell
  changes to improve candidate scores.
- **SC-015**: **Pinned native calibration** — All Stage 1 sessions use
  the same planning-pinned official GazeFollower calibration protocol
  (one of 5 / 9 / 13 after inspecting the official default). That
  protocol covers the full product Y range. Primary mapped-key
  (SC-001) is not computed solely on those training targets.
- **SC-016**: **One screen geometry** — Before Stage 1 results are
  treated as on-screen mapping evidence, planning has recorded that
  candidate coordinates, Qt/Windows coordinates, live hitboxes,
  calibration targets, benchmark targets, and suggestion rectangles
  share one screen system (DPI, `devicePixelRatio`, resolution,
  monitor origin, window position). Unproven upstream camera/screen
  constants were not copied.
- **SC-019**: **Estimator isolation** — Stage 1 candidate code does not
  import or call the forbidden historical estimator stack (FR-030).
  Planning's dependency audit exists. Where practical, an isolation
  test fails if that dependency appears.

Meeting SC-001–SC-007, SC-015, SC-016, and SC-019 makes GazeFollower a
**migration candidate**. It does **not** by itself switch production
(FR-014) or permit cleanup (FR-029).

### Stage 2 — only after review approval

- **SC-008**: Production application, calibration, and evaluation all
  obtain screen gaze from the approved candidate estimator through the
  FR-032 production contract (not through PCA4/Ridge). A
  product-condition independent mapping evaluation and a
  suggestions-off `hadar` wrong-focus check are recorded on that
  production path and are not worse than the Stage 1 candidate set.
- **SC-020**: The plan records the chosen production prediction
  contract after inspecting official GazeFollower outputs, including
  whether validity, timestamp, confidence/quality, and raw/filtered
  gaze are preserved. Downstream redesign implementing that contract
  is documented and was not used during Stage 1 scoring.
- **SC-017**: **Full interactive-control sweep (before cleanup)** —
  Every active live control is evaluated from live hitboxes: all
  letters, Space, Backspace, Enter/Shift/active editing, and all
  three suggestion slots. Systematic holes (a required control never
  reached) fail this criterion. Passing SC-005 regional reachability
  or improved average correlations is **not** sufficient.
- **SC-018**: Shared product code contains no baked-in user-specific
  anatomical or calibration constants. Calibration/personalization is
  session- or user-specific. If practical, a second-user smoke test
  is recorded before final production migration; if skipped, the
  record says so.
- **SC-009**: A Git checkpoint taken before migration/cleanup can
  restore the pre-migration product.
- **SC-010**: After cleanup, one production gaze pipeline remains, and
  Feature 004 history (specs, runs, tags) is still present and
  readable.

Cleanup MUST NOT start until SC-008, SC-017, SC-018, and SC-020 are
recorded on the production path (FR-029).

### Fail / inconclusive (outcome B)

- **SC-011**: If any of SC-001–SC-006, SC-015, SC-016, or SC-019 fail, or
  sessions disagree so the result is inconclusive, the current product
  estimator remains the default, GazeFollower is not production,
  cleanup of the current estimator has not occurred, and a written
  Stage 1 record explains the result.

### Cross-cutting

- **SC-012**: **Run clarity** — After each candidate session a tester
  can state pass/fail and the primary metrics without reading verbose
  logs. The FR-028 provenance fields are present on the run record.
- **SC-013**: **Calibration UX** — No on-screen text distractions
  beyond the target and optional progress during active fixation.
- **SC-014**: **Practical word check (reported, does not alone
  migrate)** — `hadar` with suggestions unused is recorded on
  candidate sessions that reach evaluation, compared to Feature 004
  wrong-focus. It informs review; it MUST NOT override SC-004 (Y
  unused), SC-017 (full keyboard path), or a single-session spike.

## MVP Scope *(mandatory for GazeKey)*

**In scope**:

- Isolated GazeFollower research/evaluation backend (Stage 1) as an
  **independent** official pipeline, not a wrapper around PCA4/Ridge
- Stage 1 product typing unchanged for a fair comparison
- Planning-time production prediction contract (screen position plus
  any justified official semantics); not permanently `(x, y)`-only
- Dependency audit and, where practical, import isolation tests
- Gaze-backend handoff to backend-agnostic GazeKey pieces only, with
  an audited shared screen/DPI/window geometry contract
- One pinned official/native GazeFollower calibration protocol
  (chosen in planning from upstream 5 / 9 / 13); not an assumed
  `keyboard15` copy
- Product-condition multi-session evaluation vs Feature 004
  `eval_before`, using **live runtime layout** hitboxes, including Y
  behavior, full-control reachability, stability, timestamps, and
  latency
- Independent calibration vs benchmark target sets
- Candidate calibration validity from the candidate backend (no
  PCA4/`pca_vL` 0.15 accept/reject)
- Filter/smoothing audit (no accidental double filtering)
- Per-run provenance and local gitignored replay captures
- Written Stage 1 decision (candidate / fail / inconclusive) and
  mandatory review stop before migration
- After approval only: production switch + rollback checkpoint +
  production-level mapping metrics **and** full interactive-control
  sweep **before** targeted removal of obsolete current-estimator
  product code
- Session/user-specific calibration data; optional second-user smoke
  test before final migration
- Preservation of Feature 004 historical artifacts

**Out of scope**:

- Resuming or rewriting Feature 004's paused A–F task sequence
- Inventing a new gaze estimator or approximating GazeFollower from
  the paper
- Using the historical estimator as a blueprint or routing
  GazeFollower through PCA4 / Ridge / handcrafted u/v
- Introducing any additional backend besides current vs GazeFollower
- Stage 1 downstream smoothing/validity/dwell changes to inflate
  candidate scores
- Permanently locking production to an `(x, y)`-only contract before
  inspecting official GazeFollower outputs
- Silently falling back to GazeKey `keyboard15` without an upstream
  conflict report
- Copying unproven upstream camera/screen physical constants
- Baking this developer's anatomy or calibration into shared code
- Changing dwell timing, suggestion ranking, keyboard visual design,
  blink policy, or OS injection to compensate for mapping error
- Saved multi-user profiles / language switching / multi-monitor as
  product features (session-specific calibration is in scope)
- Making evaluation part of product enablement
- Deleting Feature 004 specs, runs, or tags
- Removing the current estimator before the Stage 1 gate, review, and
  pre-cleanup production validation
- Treating historical 67% / 55 px / 80% as an automatic migrate
- Treating regional reachability or average correlations as
  production-ready
- Silently redesigning GazeFollower to fit the historical estimator,
  or routing it through that estimator, instead of adapting GazeKey
  around GazeFollower

## Assumptions

- **Product baseline**: Feature 003 remains the user-facing product.
  Feature 004 closeout (`004-pca4-investigation-closeout-20260820`) is
  the current estimator and the mapping-evidence baseline. Feature 004
  is paused/historical, not an input backlog of unfinished patches.
- **Why this feature exists**: Repeated Feature 004 evidence showed
  the current handcrafted vertical-feature + existing mapping stack
  ignores most of the vertical range under the product condition.
  Isolated feature tweaks (T020 A/B/C) did not yield a keepable Y
  signal. The next mapping-foundation step is a different estimator,
  not another one-change iteration inside that stack.
- **Official GazeFollower**: Primary technical reference is
  https://github.com/GanchengZhu/GazeFollower/tree/main
  The candidate **is** that system, handed off to GazeKey, not a
  GazeKey reimplementation and not a PCA4 add-on. Exact commit/version
  is pinned before the candidate is evaluated.
- **Historical estimator is baseline only**: Feature 004 closeout
  mapping is the comparison product, not a library for the candidate.
- **Stage 1 vs production contract**: Stage 1 keeps downstream stable
  for fairness. After a win, production architecture follows
  GazeFollower. Planning inspects official outputs and may keep more
  than `(x, y)`. Constitution “mapped gaze” still means independently
  measured screen mapping; it does not require Ridge/PCA4 to remain
  the production implementation. Planning MUST record this
  constitution check.
- **Allowed GazeKey reuse**: live keyboard geometry, independent
  benchmark scoring, product interaction, generic camera/display that
  does not change GazeFollower preprocessing.
- **Forbidden GazeKey reuse in the candidate**: FeatureExtractor gaze
  semantics, PCA/PCA4, Ridge, `pca_vL`/`pca_vR`, 0.15 and other
  PCA-specific gates, legacy aggregation/clamps/outliers/vertical
  normalization, legacy estimator calibration constants.
- **Calibration protocol is official/native, not `keyboard15`**:
  Planning inspects GazeFollower's 5 / 9 / 13-point modes, default,
  placement, timing/sampling, and model, then pins **one** protocol
  for Stage 1. That protocol must cover full product Y. GazeKey
  `keyboard15` is not assumed appropriate. If native calibration
  cannot satisfy coverage, benchmark independence, Principle XI, or
  the Windows setup, planning reports the conflict.
- **Calibration ⊥ benchmark**: Training targets and evaluation
  targets are logically independent. Calibration-location
  repeatability MAY be reported; it MUST NOT be the primary mapped-key
  rate.
- **Live layout is the geometry source**: Hitboxes for letters,
  editing controls, and all three suggestion slots are read from the
  runtime layout of that session.
- **T060 comparison slices stay fair**: Stage 1 primary mapped-key
  (SC-001) remains letter + editing so it can be compared to Feature
  004. Suggestion slots are required reachability (Stage 1) and
  required sweep members (Stage 2), not a substitute primary rate.
- **T060 envelope is the noise bar**: mapped-key 6 pp, median 2.8 px,
  row 4 pp, `hadar` 1 letter. Stage 1 must beat that envelope, not
  land inside it.
- **Y slope −0.80**: Reuses Feature 004's last operational definition
  of “mapper starts using Y.” A backend that leaves slope near −0.9
  has not solved the problem this feature exists to solve.
- **Three sessions minimum**: Matches constitution repeatability
  intent; one calibration is forbidden as a keep.
- **`hadar` is a development word** (SC-006 in Feature 004): reported
  in Stage 1; does not alone migrate or replace SC-017.
- **Single monitor, Windows desktop**, webcam already used by GazeKey.
  Primary validation may use the current developer; architecture must
  still be user-independent. Second-user smoke test before final
  migration if practical.
- **Replay includes timestamps and live layout** and stays gitignored;
  live sessions remain valid if replay is incomplete, provided that
  incompleteness is recorded.
- **No third backend**: If GazeFollower is the wrong family of
  solution, outcome B is document-and-keep-current, not “try another
  model in this feature.”
- **Cleanup is inventory-first and task-gated**: no mass delete; not
  before FR-029 production validation.
- **KEEP/FAIL/INCONCLUSIVE still apply** to Stage 1 as a whole, not
  to stacked internal GazeFollower tweaks. Tuning GazeFollower against
  GazeKey MUST still be one logical change per measured iteration if
  planning finds configuration choices (including a later change of
  5 vs 9 vs 13); unproven candidate tweaks are not stacked.
- **Which of 5 / 9 / 13 is pinned** is a **planning** outcome after
  inspecting the official repository, not a specify guess.
- **Platform Python/Windows constraints** of the current app remain;
  if official GazeFollower cannot run in that environment, that is a
  planning conflict, not a silent rewrite.
