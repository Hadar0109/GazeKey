# Feature Specification: GazeFollower Production Integration

**Feature Branch**: `005-gazefollower-backend`

**Created**: 2026-08-20

**Updated**: 2026-08-24

**Status**: Draft

**Input**: User description: "Substantially rewrite Feature 005 in place.
The purpose is no longer to keep GazeFollower as a long-lived isolated
research candidate while PCA4 remains the normal product path. Official
GazeFollower has now been run standalone on the target Windows machine
with Python 3.11: Preview worked, native calibration completed, and the
official pygame live-gaze example produced visually strong real-time
screen mapping. That discovery evidence justifies proceeding to
integration; it is not sufficient to delete the old pipeline. New goal:
replace GazeKey's gaze-estimation and calibration subsystem with the
official GazeFollower pipeline, while preserving the existing GazeKey
keyboard, dwell interaction, OS typing, predictive text, autocomplete,
and other working downstream product behavior. After the integrated
GazeFollower product passes acceptance, remove obsolete legacy gaze
runtime code. GazeFollower owns camera-to-calibrated/filtered screen
gaze, including official Preview and Calibration UI. GazeKey begins at
the backend handoff and continues to own keyboard geometry, hit testing,
focus, dwell, KeyAction/ActionDispatcher, OS typing, and predictive
text. Production MUST NOT route GazeFollower through PCA/Ridge or any
legacy mapper. Prefer official filtered gaze; do not double-filter.
Planning defines a GazeSample contract from official GazeInfo. pygame
Preview/Calibration and PySide6 keyboard use sequential screen
ownership. Recalibration uses the official GazeFollower flow. Integrated
product usability across at least three chin/head-support sessions is
the cleanup gate. Feature 004 T060 numerical thresholds are historical
reference only and MUST NOT gate whether integration may begin. Feature
004 remains closed historical evidence."

**Guidance**: GazeKey Constitution v1.3.0 (binding). This is a
**mapping-foundation replacement**: the production gaze and calibration
subsystem becomes official GazeFollower, while independently measured
screen mapping remains the sealed **measurement** upstream for
downstream typing. Downstream keyboard, dwell, OS typing, and
predictive-text behavior MUST consume that screen gaze and MUST NOT
retune or compensate mapping to “fix” typing. Feature 004 is a
**closed historical record** (paused, not completed); this feature
MUST NOT delete, renumber, resume, or rewrite it. Constitution text
that still names PCA4 as the runtime foundation is a **planning
constitution check**, not a reason to keep PCA4 on the new production
path.

## Clarifications

### Session 2026-08-20 (from Feature 004, still binding)

- **Product condition is head-stabilized**: All accuracy evaluation,
  `hadar` word checks, and repeatability runs are captured **with** the
  chin/head support. Free-head sessions are diagnostic only.
- **Accuracy must not depend on head motion**: A backend that needs the
  user's head to move in order to produce a usable vertical signal is a
  defect, not a keep.
- **Passing calibration gates is necessary, not sufficient**: Gate pass
  MUST NOT be reported as mapping or product success.
- **Focus vs dwell**: Wrong mapped-key focus is already a mapping
  failure, even if dwell never activates a key.
- **Word checks vs baseline**: Practical typing checks compare
  wrong-focus outcomes with suggestions unused.

### Session 2026-08-24 (production integration architecture)

These decisions **supersede** the 2026-08-20 Feature 005 defaults that
kept PCA4 as the normal application path throughout a long Stage 1
research trial, required GazeFollower to exist only as a separate
evaluation backend, and forbade application integration until Feature
004 T060 percentage/noise formulas were beaten.

- **Integration is now the Feature 005 goal**: Replace GazeKey's
  gaze-estimation and calibration subsystem with official GazeFollower.
  Preserve the working GazeKey product above that handoff. After
  integrated acceptance, remove obsolete legacy gaze runtime.
- **Standalone discovery is integration evidence, not cleanup
  evidence**: Manual official-repository Preview, native calibration,
  and pygame live-gaze success on the target Windows / Python 3.11
  machine justifies proceeding to integration. Integrated product
  acceptance is still required before destructive cleanup.
- **T060 is not an integration-start gate**: Feature 004 T060
  numerical thresholds MUST NOT decide whether integration may begin.
  Feature 004 results remain historical/reference evidence and
  `eval_before` citation for mapping experiments.
- **Binding ownership**: GazeFollower owns the complete gaze pipeline
  from camera to final calibrated/filtered screen gaze, including
  official Preview UI, Calibration UI, calibration-result UI, native
  calibration/personalization, candidate validity, official filtering,
  and final screen-space gaze. GazeKey MUST NOT recreate, approximate,
  restyle, or replace those official UIs. GazeKey begins only at the
  backend handoff.
- **GazeKey ownership unchanged below the handoff**: keyboard
  UI/layout, live key and suggestion geometry, screen-point → control
  hit testing, focus, existing dwell, same-key lockout / existing
  interaction semantics, KeyAction / ActionDispatcher, OS typing,
  Shift/Backspace/Space/editing, prediction context, three word
  suggestions, and autocomplete acceptance.
- **Intended production flow**:
  `GazeFollower calibrated/filtered screen gaze → live GazeKey
  geometry → focus/dwell`. Forbidden:
  `GazeFollower → PCA/Ridge → keyboard` and
  `GazeFollower → legacy mapper → keyboard`.
- **One production execution path**: Do not maintain two blended live
  gaze pipelines. Legacy code may remain in the repository until
  acceptance solely for rollback/history; it MUST NOT participate in
  the new production execution path. If integrated GazeFollower is
  unusable, rollback through Git.
- **Official filtered gaze is the default pointing signal**: Audit
  official GazeFollower filtering against existing GazeKey smoothing
  so filtering is not applied twice. Prefer official filtered gaze
  unless planning finds a concrete upstream reason not to. Dwell is
  interaction logic, not smoothing. Do not add tuning or extra
  smoothing to make acceptance look better.
- **Official native calibration, not GazeKey `keyboard15`**: The
  product uses GazeFollower's official calibration system. GazeKey
  MUST NOT host its own calibration target UI. Planning inspects and
  records the tested native protocol.
- **Sequential UI ownership**: Official GazeFollower Preview/Calibration
  (pygame) then GazeKey keyboard (PySide6). Do not recreate the
  GazeFollower UI in Qt to make integration easier.
- **No extra remapping**: Only legitimate coordinate-space/window
  transforms are allowed. Do not apply a learned or hand-tuned
  remapping to make coordinate systems match.
- **Cleanup only after integrated acceptance**: At least three
  product-condition sessions on the real keyboard and real OS typing
  path. Then inventory-based removal of obsolete legacy gaze runtime.
  Preserve Feature 004 specs, runs, commits, and tags.
- **One candidate estimator**: GazeFollower is the only new backend.
  Do not add EyeTheia, a third estimator, an ensemble, or a gaze
  fallback cascade.
- **Upstream source of truth**: The official GazeFollower repository
  is the implementation reference. Conflicts with this spec are
  reported at planning time; they are not silently papered over.

### Session 2026-08-20 (calibration, geometry, reachability — still
binding where not superseded)

User-provided decisions that remain in force, reinterpreted for
production integration rather than an isolated Stage 1 trial:

- Coverage uses the **actual runtime layout**. Integrated acceptance
  requires a **full interactive-control sweep** of every active
  control: all letter keys, Space, Backspace, Enter/Shift and other
  active editing controls, and **all three suggestion slots**. Targets
  and hitboxes come from **live runtime layout geometry**, not a
  duplicated hard-coded coordinate list.
- Do **not** assume GazeKey `keyboard15`. Planning inspects the
  official GazeFollower calibration implementation (supported **5 / 9 /
  13-point** modes, default mode, exact target placement, collection
  timing/sampling, calibration model, result/accept/recalibrate
  behavior) and records the **tested native protocol**. Calibration
  MUST spatially cover the complete product interaction range,
  especially **top-to-bottom Y**. Calibration and any reused mapping
  benchmark remain **logically independent** so training-target overlap
  cannot falsely inflate evaluation.
- Planning MUST verify that GazeFollower screen coordinates, Windows
  desktop coordinates, Qt screen coordinates, keyboard window position,
  key QRect geometry, suggestion QRect geometry, display resolution,
  Windows DPI scaling, `devicePixelRatio`, and monitor origin are
  compatible. Do **not** copy upstream hard-coded camera/screen
  constants without proving they apply.
- Current-estimator-specific gates/features (including `pca_vL` and
  its 0.15 threshold) MUST NOT accept or reject GazeFollower
  calibration. Candidate validity/calibration semantics come from
  GazeFollower. Independent GazeKey mapping evaluation remains
  valuable evidence but is **not** a reason to route GazeFollower
  through old mapping infrastructure.
- Audit GazeFollower's own filtering versus GazeKey smoothing so
  filtering is not applied twice. Record raw and filtered gaze where
  officially available and useful, plus timestamps, update rate, and
  end-to-end latency. Benchmark scoring MUST NOT measure stale
  predictions from the previous target.
- Every run records upstream commit, model/checkpoint identification
  or hash where practical, calibration mode, camera configuration,
  preprocessing/mirroring, screen/DPI geometry, dependency/version
  record, license/attribution, and relevant runtime config. Replayable
  local captures remain **gitignored**.
- Feature 005 may be validated primarily with the current developer,
  but production architecture MUST NOT bake user-specific anatomical
  or calibration constants into shared code. GazeFollower
  personalization/calibration is **session/user-specific**. If
  practical, a **second-user smoke test** runs before cleanup; if
  skipped, the acceptance record MUST say so.
- A backend is production-ready only after the **integrated product**
  is reliably usable on the real keyboard and real OS typing path.
  Regional reachability or average correlations improving is **not**
  enough.

### Session 2026-08-20 (legacy isolation and production contract —
still binding, Stage 1 comparison language superseded)

- GazeFollower is a genuinely independent pipeline from the official
  repository. The current estimator is a **historical baseline**, not
  a blueprint or component. The **production GazeFollower path** MUST
  NOT depend on or reuse estimator-specific pieces (handcrafted u/v or
  FeatureExtractor gaze semantics, PCA/PCA4, Ridge, `pca_vL`/`pca_vR`,
  PCA-specific gates including 0.15, legacy aggregation/clamps/outlier
  logic/vertical normalization, or legacy estimator calibration
  assumptions/constants). Preprocessing, eye/face preparation,
  inference, calibration/personalization, validity, and filtering
  follow official GazeFollower unless planning documents a real
  integration conflict. Existing GazeKey code may be reused **only**
  when backend-agnostic (live keyboard geometry, independent benchmark
  scoring that does not require the legacy estimator, product
  interaction, generic display/camera that does not alter GazeFollower
  preprocessing). Planning MUST publish a dependency audit. Where
  practical, an import/isolation test MUST fail if the production path
  starts depending on the handcrafted/PCA4 stack. If GazeFollower
  conflicts with existing calibration/tracking, **adapt the
  integration around GazeFollower**.
- Planning MUST inspect official GazeFollower GazeInfo/output APIs and
  define a clean backend-agnostic **GazeSample-style** contract. It
  MUST contain screen position and SHOULD preserve useful upstream
  semantics when actually available (validity/status, timestamp,
  filtered gaze, raw/unfiltered gaze for diagnostics, confidence/
  quality only if provided). Do not invent unavailable fields. The
  product hit-testing path uses the intentionally selected official
  gaze coordinate, expected initially to be GazeFollower's filtered
  screen coordinate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Official GazeFollower Startup, Then the Existing Keyboard (Priority: P1)

The user launches the normal application. The official GazeFollower
backend initializes and the official GazeFollower Preview UI appears.
The user continues with the official upstream interaction, then the
official GazeFollower Calibration UI, then the official calibration
result / accept / recalibrate behavior. After successful accepted
calibration, GazeFollower sampling starts, the GazeFollower calibration
experience is closed or left, and the existing GazeKey keyboard is
shown. GazeKey does not present a substitute Preview or Calibration
screen.

**Why this priority**: The standalone official Preview and Calibration
flow already worked on the target machine. The first product value is
to use that same official experience as application startup, not to
rebuild it inside GazeKey or keep PCA4/`keyboard15` as the normal
path.

**Independent Test**: Launch the Feature 005 application path. Confirm
official Preview then official Calibration then official result/accept
behavior, then the existing keyboard appears only after accepted
calibration and sampling start. Confirm GazeKey did not host its own
calibration-target UI and that the legacy GazeKey calibration system
did not run.

**Acceptance Scenarios**:

1. **Given** a normal application launch, **When** startup proceeds,
   **Then** the user sees official GazeFollower Preview and
   Calibration UI rather than the legacy GazeKey calibration system.
2. **Given** official calibration completes and is accepted, **When**
   the calibration experience is left, **Then** GazeFollower sampling
   has started and the existing GazeKey keyboard is shown.
3. **Given** the user chooses official recalibrate on the GazeFollower
   result UI before accepting, **When** that official flow finishes
   and is accepted, **Then** the existing keyboard still appears only
   after successful accepted calibration.
4. **Given** GazeFollower cannot start (missing model, dependency, or
   device), **When** the user launches the application, **Then** the
   failure is reported and the application does not silently fall back
   to PCA4 or another estimator.
5. **Given** the production startup path, **When** imports and calls
   are inspected, **Then** it does not use the historical estimator's
   handcrafted features, PCA/PCA4, Ridge, or PCA-specific gates to
   produce or accept calibration.

---

### User Story 2 - Official Screen Gaze Points at the Live Keyboard (Priority: P1)

After accepted calibration, GazeFollower gaze samples are handed
continuously to GazeKey. A temporary developer/debug gaze dot shows
the official GazeFollower output on the existing keyboard so testers
can see that the strong standalone mapping survived integration. Focus
is resolved from live keyboard and suggestion hitboxes. No extra
learned or hand-tuned remapping is applied.

**Why this priority**: Integration is only justified if the visually
strong standalone mapping is preserved after the handoff. This story
proves coordinate compatibility and live geometry before reconnecting
dwell and typing.

**Independent Test**: After official calibration, open the existing
keyboard, display the debug gaze dot from official GazeFollower
output, look around the live layout with the chin/head support, and
confirm the dot tracks the intended screen regions without a
post-GazeFollower mapper.

**Acceptance Scenarios**:

1. **Given** accepted official calibration and sampling, **When** the
   keyboard is shown, **Then** a temporary debug gaze dot follows the
   selected official GazeFollower screen coordinate.
2. **Given** that live handoff, **When** the user looks across the
   keyboard including top letter rows, bottom editing controls, and
   suggestion slots, **Then** the official gaze visibly spans the
   required interaction area and does not systematically collapse
   vertically.
3. **Given** a GazeFollower screen sample, **When** GazeKey resolves
   focus, **Then** the result uses that sample and **live** key /
   suggestion rectangles, not a duplicated coordinate table and not
   PCA4/Ridge internals.
4. **Given** the geometry audit, **When** GazeFollower, Windows, Qt,
   window position, QRect hitboxes, DPI, `devicePixelRatio`, and
   monitor origin are compared, **Then** any conversion is a
   legitimate coordinate-space or window transform, not a learned
   remapping added to make systems match.
5. **Given** official filtering already exists, **When** the debug
   pointing signal is chosen, **Then** GazeKey has not accidentally
   stacked its old smoothing on top of GazeFollower unless planning
   recorded a concrete upstream reason.

---

### User Story 3 - Existing Typing Product Continues Above the New Gaze Foundation (Priority: P1)

Once official gaze is reaching live controls, the existing GazeKey
interaction layer is reconnected: dwell selects controls, the existing
action pipeline types into the external OS application, and existing
predictive-text / autocomplete behavior continues unchanged. Keyboard
visual design, dwell algorithm, and prediction algorithm are not
redesigned unless integration reveals a real backend-interface
requirement.

**Why this priority**: The product above mapping already works. Feature
005 replaces the gaze/calibration foundation; it must not become a
redesign of typing, dwell, or suggestions.

**Independent Test**: After official calibration and live handoff,
dwell-select letters and editing keys, type into an external
application, confirm three suggestion slots appear from existing
prediction, gaze-select a suggestion, and confirm suffix + Space
acceptance. Compare interaction behavior with Feature 003 / Feature
004 closeout except for the gaze source.

**Acceptance Scenarios**:

1. **Given** official gaze on a live key hitbox, **When** the user
   dwells, **Then** the existing dwell interaction selects that
   control using existing same-key lockout / interaction semantics.
2. **Given** a selected key, **When** the existing action pipeline
   runs, **Then** the expected character or editing action is typed
   into the external OS application.
3. **Given** typed context, **When** predictions are shown, **Then**
   three word suggestions appear using the existing prediction
   behavior.
4. **Given** gaze on a suggestion slot, **When** dwell selects it,
   **Then** accepting the suggestion types the expected suffix +
   Space.
5. **Given** this restored interaction path, **When** product behavior
   is compared with the Feature 004 closeout keyboard, **Then** dwell
   timing, suggestion ranking, keyboard visual design, and OS
   injection have not been changed to compensate for mapping error.

---

### User Story 4 - Recalibrate with GazeFollower and Shut Down Cleanly (Priority: P2)

From the GazeKey keyboard, recalibration invokes the same official
GazeFollower Preview + Calibration flow rather than the legacy GazeKey
calibration system. After accepted recalibration, the user returns to
a usable keyboard with GazeFollower sampling. On exit, sampling stops
and GazeFollower resources, including the camera, are released without
conflicting UI event loops or leftover capture ownership.

**Why this priority**: A pygame calibration experience and a PySide6
keyboard cannot both own the screen, camera, and event loop at once.
Safe recalibration and shutdown are required for a real product, not
only a one-shot startup demo.

**Independent Test**: From the keyboard, start recalibration, complete
the official GazeFollower flow, return to the keyboard, confirm gaze
handoff again, then exit the application and confirm sampling has
stopped and the camera is released.

**Acceptance Scenarios**:

1. **Given** the GazeKey keyboard is showing, **When** the user
   requests recalibration, **Then** the official GazeFollower Preview
   + Calibration flow runs and the legacy GazeKey calibration system
   does not.
2. **Given** recalibration is accepted, **When** the GazeFollower
   calibration experience is left, **Then** the existing keyboard
   returns, sampling is active, and pointing is again usable.
3. **Given** the user aborts recalibration or calibration is not
   accepted, **When** control would return to GazeKey, **Then** the
   application does not continue as if a new accepted calibration
   existed, and planning-recorded recovery behavior is followed
   without falling back to PCA4.
4. **Given** the user exits the application, **When** shutdown runs,
   **Then** GazeFollower sampling stops and GazeFollower resources are
   released cleanly.
5. **Given** pygame Preview/Calibration and the PySide6 keyboard,
   **When** startup, recalibration, or shutdown occurs, **Then** the
   two UI systems do not fight over the event loop or camera.

---

### User Story 5 - Accept the Integrated Product, Then Remove Obsolete Gaze Code (Priority: P2)

The developer runs at least three chin/head-support product-condition
sessions on the **integrated** application: real keyboard, real OS
typing, suggestions, recalibration, and independent mapping metrics
where the existing benchmark can be reused without legacy estimator
dependencies. If the integrated product is reliably usable, a Git
checkpoint of the pre-cleanup product is created and obsolete legacy
gaze runtime is removed by explicit inventory-based tasks. If it is
not usable, the result is documented and rollback uses Git. Feature
004 history remains untouched either way.

**Why this priority**: Standalone Preview success is not cleanup
evidence. Cleanup without integrated acceptance would destroy the only
rollback product. Cleanup after acceptance avoids carrying two gaze
stacks forever.

**Independent Test**: Complete three product-condition integrated
sessions covering the acceptance sweep in Success Criteria. On pass,
confirm a pre-cleanup Git checkpoint exists, then show inventory-based
deletions and surviving Feature 004 artifacts. On fail, show that
destructive legacy-gaze cleanup has not occurred and Git can restore
the pre-cleanup product.

**Acceptance Scenarios**:

1. **Given** fewer than three product-condition integrated sessions,
   **When** cleanup is proposed, **Then** obsolete legacy gaze runtime
   MUST NOT be deleted.
2. **Given** three sessions where the keyboard is not reliably usable
   (vertical collapse, unreachable required controls, unusable dwell,
   or OS typing failure), **When** the feature decision is made,
   **Then** the outcome is fail or inconclusive, cleanup does not
   start, and rollback is through Git rather than a GazeFollower/PCA4
   cascade.
3. **Given** integrated acceptance has passed, **When** cleanup is
   about to start, **Then** a Git checkpoint/tag exists that restores
   the pre-cleanup product.
4. **Given** that checkpoint and passing acceptance, **When** obsolete
   legacy gaze runtime, dependencies, configuration, and tests are
   removed, **Then** each deletion is an explicit approved task, the
   production path is GazeFollower-only, and Feature 004 specs, runs,
   commits, and tags remain.
5. **Given** either outcome, **When** a later reader opens the repo,
   **Then** they can tell which gaze/calibration subsystem is
   production and where the Feature 004 record lives.

---

### Edge Cases

- Official GazeFollower model files, weights, or dependencies are
  missing: startup fails closed; the application MUST NOT silently
  start the legacy PCA4 path.
- Official Preview, Calibration, or sampling cannot start because of
  a pygame / Qt event-loop or camera-ownership conflict: **stop and
  report at planning or implementation** — do not recreate the
  GazeFollower UI in Qt merely to avoid the conflict, and do not
  leave both UIs owning the camera.
- The user aborts official calibration, rejects the result, or
  requests official recalibrate before accept: follow official
  GazeFollower behavior; do not treat an unaccepted calibration as
  production-ready keyboard pointing.
- Recalibration is requested while the keyboard is live: the official
  GazeFollower flow must take sequential screen ownership; the
  keyboard must not keep consuming a dead or double-owned camera
  stream.
- Shutdown occurs during Preview, Calibration, sampling, or keyboard
  use: sampling stops and GazeFollower resources are released; no
  orphan camera capture.
- GazeFollower screen coordinates, Windows/Qt coordinates, window
  position, QRects, DPI, `devicePixelRatio`, or monitor origin do not
  match: only legitimate transforms are allowed; a learned or
  hand-tuned remap to “make it look calibrated” is a **defect**.
- Official GazeFollower 5/9/13-point protocol cannot cover the full
  product Y range, cannot stay independent of the benchmark, or cannot
  run with the Windows webcam setup: **stop and report at planning** —
  do not invent a different estimator and do not silently fall back to
  `keyboard15`.
- Upstream ships hard-coded camera/screen constants (focal length,
  screen cm, origin): they MUST NOT be copied until proven to match
  this machine.
- GazeKey smoothing and GazeFollower filtering are stacked without an
  audit: treat as a **defect** until one intentional pointing-signal
  policy is recorded.
- Extra GazeKey smoothing, validity, or dwell changes are added so
  acceptance looks better: **defect**.
- Production is designed as “GazeFollower features fed into
  Ridge/PCA4” or “GazeFollower then legacy mapper”: **forbidden**.
- Production path imports or calls FeatureExtractor gaze semantics,
  PCA/PCA4, Ridge, `pca_vL`/`pca_vR`, or PCA-specific gates:
  **defect**; not a valid GazeFollower product path.
- Camera/display helpers alter GazeFollower preprocessing (mirroring,
  crop, color) away from official behavior without a documented
  conflict: **defect**.
- Evaluation uses a duplicated hard-coded coordinate list instead of
  live runtime hitboxes: the run is invalid for acceptance.
- Calibration targets overlap the benchmark set and that overlap is
  used as the primary mapped-key rate: the run is invalid; report
  calib-location repeatability separately.
- Benchmark scores a sample against the previous target because
  timestamps were ignored: the run is invalid.
- Candidate is accurate but too slow for existing dwell: **fail**
  (not interactive).
- Gaze reaches letter keys but not Space, Backspace, Enter, Shift, or
  any of the three suggestion slots on the **live** layout: **fail**
  reachability; do not start cleanup.
- Predicted Y barely moves as targets move from top row to Space:
  **fail** for systematic vertical collapse, even if home-row letters
  look improved.
- Replay capture is unavailable: live evaluation may still proceed;
  lack of replay is recorded.
- Raw webcam / face / eye frames must never be committed; if a
  capture is saved locally, it stays gitignored.
- Shared product code contains this developer's anatomical or
  calibration constants: **defect**.
- Feature 004 tasks remain unchecked/paused: do not resume them and
  do not rewrite them to look completed.
- Two estimators MUST NOT be blended in one live predict (no averaging
  with PCA4, no fallback cascade).
- Official GazeFollower UI contains more on-screen content than
  Constitution Principle XI would allow for a GazeKey-hosted
  calibration surface: **do not restyle or replace the official UI**.
  Planning records the Principle XI conflict. Principle XI continues
  to forbid GazeKey from hosting its own metric-heavy calibration
  surface.
- Standalone official Preview success is treated as permission to
  delete the old pipeline before integrated acceptance: **forbidden**.

## Requirements *(mandatory)*

### Functional Requirements

**Product goal and ownership**

- **FR-001**: Feature 005 MUST replace GazeKey's gaze-estimation and
  calibration subsystem with the official GazeFollower pipeline, while
  preserving the existing GazeKey keyboard, dwell interaction, OS
  typing, predictive text, autocomplete, and other working downstream
  product behavior.
- **FR-002**: GazeFollower MUST own the complete gaze pipeline from
  camera to final calibrated/filtered screen gaze, including: webcam
  acquisition used by GazeFollower; official face/eye preprocessing;
  official gaze model/inference; official Preview UI; official
  Calibration UI and calibration-result UI; official native
  calibration/personalization; candidate validity semantics; official
  filtering; and final screen-space gaze coordinates.
- **FR-003**: GazeKey MUST NOT recreate, approximate, restyle, or
  replace the official GazeFollower Preview or Calibration UI. The
  startup calibration experience MUST use the official GazeFollower UI
  and behavior directly, matching the standalone flow already tested
  on the target machine.
- **FR-004**: GazeKey MUST begin only at the backend handoff after
  GazeFollower has produced gaze information. GazeKey MUST continue to
  own: existing keyboard UI/layout; live runtime key and suggestion
  geometry; screen-point → control hit testing; focus; existing dwell
  interaction; same-key lockout / existing interaction semantics;
  KeyAction / ActionDispatcher path; OS typing; Shift / Backspace /
  Space / editing behavior; prediction context; three word
  suggestions; and autocomplete acceptance behavior.
- **FR-005**: The intended production flow MUST be `GazeFollower
  calibrated/filtered screen gaze → live GazeKey geometry →
  focus/dwell`. The system MUST NOT build `GazeFollower → PCA/Ridge →
  keyboard` or `GazeFollower → legacy mapper → keyboard`.

**Required application flow**

- **FR-006**: Normal application startup MUST conceptually follow:
  (1) initialize the official GazeFollower backend; (2) show official
  Preview UI; (3) user continues using official upstream interaction;
  (4) show official Calibration UI; (5) show/use official calibration
  result/accept/recalibrate behavior; (6) after successful accepted
  calibration, start GazeFollower sampling; (7) close/leave the
  GazeFollower calibration experience; (8) show the existing GazeKey
  keyboard; (9) continuously hand GazeFollower gaze samples to the
  GazeKey downstream interaction layer; (10) resolve focus from live
  keyboard/suggestion hitboxes; (11) existing dwell selects controls;
  (12) existing action pipeline types into the external OS
  application; (13) existing predictive-text/autocomplete behavior
  continues unchanged.
- **FR-007**: Recalibration requested from the GazeKey keyboard MUST
  invoke the same official GazeFollower Preview + Calibration flow
  rather than the legacy GazeKey calibration system.
- **FR-008**: Shutdown MUST stop sampling and release GazeFollower
  resources cleanly, including camera ownership, without leaving a
  conflicting UI event loop.

**Strict legacy isolation**

- **FR-009**: The production GazeFollower path MUST NOT import, call,
  or route gaze through legacy estimator-specific components,
  including: GazeKey handcrafted gaze u/v features; FeatureExtractor
  gaze semantics; PCA / PCA4; Ridge; `pca_vL` / `pca_vR`; PCA-specific
  calibration gates including the 0.15 gate; legacy vertical
  normalization; legacy gaze aggregation/clamping/outlier corrections;
  legacy gaze calibration targets/protocol; and any mapper/correction
  applied after GazeFollower screen coordinates.
- **FR-010**: Existing legacy gaze code MAY physically remain in the
  repository until integrated acceptance passes, solely for
  rollback/history. It MUST NOT participate in the new production
  execution path. The feature MUST NOT maintain two blended live gaze
  pipelines merely for safety.
- **FR-011**: Planning MUST include a **dependency-isolation audit**
  that identifies: (1) official GazeFollower components used; (2)
  existing GazeKey modules the production path may reuse; (3) legacy
  gaze modules the production path is **forbidden** to import or
  call; and (4) the exact handoff between GazeFollower and GazeKey.
  Where practical, an import/dependency isolation test MUST fail if
  the production path starts depending on the PCA4 / handcrafted-
  feature stack.
- **FR-012**: This feature MUST NOT introduce EyeTheia, a third gaze
  backend, an ensemble, or a gaze fallback cascade. If integrated
  GazeFollower proves unusable, rollback MUST be through Git rather
  than a fallback cascade between GazeFollower and PCA4.

**Filtering and production gaze contract**

- **FR-013**: Planning MUST audit GazeFollower's official filtering
  and the existing GazeKey smoothing. The first integrated production
  path MUST NOT accidentally double-filter gaze.
- **FR-014**: The product pointing signal MUST prefer the official
  GazeFollower filtered gaze output unless planning finds a concrete
  upstream reason not to. That choice MUST be recorded. Do not add
  tuning or additional smoothing simply to make acceptance results
  look better.
- **FR-015**: Dwell MUST remain existing interaction logic and MUST
  NOT be confused with gaze smoothing.
- **FR-016**: Planning MUST inspect the official GazeFollower
  GazeInfo/output API and define a clean backend-agnostic
  GazeSample-style contract. The contract MUST contain screen position
  and SHOULD preserve useful upstream semantics when available:
  validity/status; timestamp; filtered gaze coordinate; raw/unfiltered
  gaze for diagnostics if officially available and technically useful;
  and confidence/quality only if actually provided upstream. The
  contract MUST NOT invent unavailable fields.
- **FR-017**: The product hit-testing path MUST use the intentionally
  selected official gaze coordinate, expected initially to be
  GazeFollower's filtered screen coordinate.

**UI framework boundary**

- **FR-018**: Planning MUST explicitly design the lifecycle boundary
  between GazeFollower's pygame-based Preview/Calibration UI and
  GazeKey's PySide6-based keyboard. GazeKey MUST NOT recreate the
  GazeFollower UI in Qt merely to make integration easier.
- **FR-019**: The application MUST use sequential screen ownership:
  official GazeFollower preview/calibration → GazeFollower sampling →
  GazeKey Qt keyboard. Planning MUST also cover safe recalibration and
  clean shutdown without conflicting event loops or camera ownership.

**Screen geometry**

- **FR-020**: Planning MUST verify compatibility among: GazeFollower
  screen coordinates; Windows desktop coordinates; Qt screen
  coordinates; keyboard window position; key QRect geometry;
  suggestion QRect geometry; display resolution; Windows DPI scaling;
  `devicePixelRatio`; and monitor origin.
- **FR-021**: The system MUST NOT apply a learned or hand-tuned
  remapping to make coordinate systems match. Only legitimate
  coordinate-space/window transforms are allowed. Upstream hard-coded
  camera or screen constants MUST NOT be copied unless proven to apply
  on this machine.

**Upstream provenance and calibration**

- **FR-022**: Planning/implementation MUST record: the exact official
  GazeFollower upstream repository; the exact commit/version used;
  model/checkpoint identification or hash where practical;
  dependency/version record; calibration mode; camera configuration;
  screen/DPI configuration; and license/attribution record.
- **FR-023**: The feature MUST NOT reimplement GazeFollower from its
  paper. The feature MUST NOT copy the upstream repository into
  unrelated GazeKey gaze modules and modify it until it resembles the
  old architecture. Prefer a thin GazeKey backend/adapter around the
  official library.
- **FR-024**: The product MUST use GazeFollower's official/native
  calibration system, not GazeKey `keyboard15`. The UI, target
  behavior, timing, collection, fitting, result screen,
  accept/recalibrate behavior, and personalization remain owned by
  GazeFollower. GazeKey MUST NOT host its own calibration target UI.
- **FR-025**: Planning MUST inspect and record the tested native
  protocol and current upstream behavior, including supported 5 / 9 /
  13-point modes, default mode, exact target placement, collection
  timing/sampling, calibration model, and result/accept/recalibrate
  behavior. That protocol MUST spatially cover the complete product
  interaction range, especially top-to-bottom Y. If the native
  protocol conflicts with full-product Y coverage, benchmark
  independence, the Windows product setup, or sequential UI ownership,
  planning MUST record the conflict and stop — not silently redesign
  GazeFollower and not silently fall back to `keyboard15`.
- **FR-026**: Current-estimator-specific quality gates and features
  (including `pca_vL` and its 0.15 threshold, and other PCA4-only
  checks) MUST NOT be used to accept or reject GazeFollower
  calibration. Candidate validity and calibration semantics come from
  GazeFollower.

**Integration stages**

- **FR-027**: The feature MUST be implemented in the following stages.
  Later stages MUST NOT skip a prior stage's required proof.

  - **Stage A — upstream pin and architecture**: Record upstream
    provenance, dependency approach, GazeInfo contract, lifecycle,
    geometry, filtering, and dependency-isolation audit. No product
    code until this planning work exists.
  - **Stage B — official GazeFollower startup flow**: Normal Feature
    005 branch execution uses official Preview + Calibration +
    start sampling. No legacy calibration/mapping participates.
  - **Stage C — keyboard gaze handoff**: Open the existing GazeKey
    keyboard after calibration and display a temporary
    developer/debug gaze dot from the official GazeFollower output.
    Use this stage to prove that the strong standalone mapping is
    preserved after integration. No extra remapping.
  - **Stage D — restore full interaction path**: Use live Qt geometry
    for focus and reconnect existing dwell, key selection, OS typing,
    editing, predictive text, three suggestion slots, and
    autocomplete. Do not redesign these features unless integration
    reveals a real backend-interface requirement.
  - **Stage E — recalibration and lifecycle**: Recalibrate using the
    official GazeFollower flow and return safely to the keyboard.
    Clean release on exit.
  - **Stage F — integrated production acceptance**: Run at least three
    head/chin-support product-condition sessions on the integrated
    product before legacy cleanup. Acceptance MUST cover the real
    keyboard and real OS typing path, not only an isolated benchmark.
  - **Stage G — cleanup**: Only after integrated acceptance passes,
    remove obsolete legacy gaze runtime code/dependencies/
    configuration/tests in explicit inventory-based tasks. Preserve
    Feature 004 specs, runs, commits, and tags.

**Integrated acceptance, metrics, and cleanup safety**

- **FR-028**: Feature 004 T060 numerical thresholds MUST NOT be the
  architectural gate for whether integration may begin. Feature 004
  results remain historical/reference evidence and MAY be cited as
  `eval_before` on mapping experiments.
- **FR-029**: The decisive acceptance for cleanup MUST be whether the
  new integrated product is reliably usable. Acceptance MUST require
  at least **three** product-condition sessions and MUST verify the
  Success Criteria listed under Integrated production acceptance.
- **FR-030**: Independent mapped-key, row, and pixel-error metrics
  MUST continue to be recorded where the existing benchmark can be
  reused **without** legacy estimator dependencies. These metrics are
  valuable evidence and MUST remain independent of typing success.
  They MUST NOT be a reason to route GazeFollower through old mapping
  infrastructure. Calibration and benchmark target sets MUST remain
  logically independent: training-target overlap MUST NOT be used as
  the primary mapped-key rate.
- **FR-031**: Evaluation targets and hitboxes MUST come from the live
  runtime keyboard layout of that session. They MUST NOT come from a
  duplicated hard-coded coordinate list. The evaluated live controls
  MUST include all letter keys, Space, Backspace, Enter / Shift and
  other active editing controls, and all three suggestion slots.
- **FR-032**: Before destructive cleanup, a Git checkpoint/tag MUST
  exist that restores the pre-cleanup product. The feature branch
  itself provides isolation while the new production path is built.
- **FR-033**: After successful integrated acceptance, obsolete legacy
  gaze runtime, configuration, flags, tests, and dependencies that are
  no longer needed MUST be removed so one production gaze pipeline
  remains. Each deletion MUST be its own approved task (Principle IX).
  Cleanup MUST NOT start merely because standalone Preview succeeded
  or because regional reachability or average correlations improved.
- **FR-034**: Cleanup MUST NOT delete, rewrite, or renumber Feature
  004 specifications, run artifacts, Git tags, commits, or
  investigation records. Feature 004's paused A–F task sequence MUST
  NOT be resumed, completed, or rewritten as if it had finished.
- **FR-035**: Shared product code MUST NOT bake user-specific
  anatomical or calibration constants. GazeFollower
  personalization/calibration MUST be session- or user-specific data.
  If practical, a second-user smoke test MUST run before cleanup; if
  skipped, the acceptance record MUST say so.

**Safety, data, logging, and conflicts**

- **FR-036**: Where practical, the system MUST support locally stored
  **replayable** captures of a session so the same session can be
  analyzed offline. Captures MUST include enough information for
  offline investigation (gaze samples, timestamps, live layout
  geometry, calibration mode/targets, and FR-022 provenance fields).
  Raw webcam, eye, and face data MUST remain local and gitignored.
  Only derived results MAY be committed.
- **FR-037**: Normal product use MUST keep terminal output short;
  optional verbose output is for investigation (Principle X). Each
  integrated acceptance session MUST produce a simple pass/fail
  summary with primary mapping metrics and the usability sweep result
  (Principles VII and X).
- **FR-038**: If upstream GazeFollower architecture, license,
  dependencies, UI framework, calibration protocol, or runtime
  requirements conflict with this specification or with the
  constitution, planning MUST record the conflict and stop for a
  decision. Silently redesigning GazeFollower to fit the historical
  estimator, restyling official Preview/Calibration in Qt, or routing
  GazeFollower through that estimator is out of scope.
- **FR-039**: Mapping accuracy remains independently measured.
  Internal training losses, vendor demo metrics, standalone Preview
  impressions, regional reachability alone, or average correlations
  MUST NOT be the sole acceptance criteria (Principle II).
- **FR-040**: Typing, dwell, suggestions, keyboard UI, blink
  detection, and unrelated Feature 002/003 behavior MUST NOT be
  modified to compensate for estimator error, to hide poor gaze
  accuracy, or to inflate acceptance results. Downstream interface
  changes MAY occur only for documented technical reasons arising
  from the official GazeFollower handoff (FR-016 / FR-018).
- **FR-041**: Every integrated run MUST record the FR-022 provenance
  fields plus calibration mode and target positions, camera ID /
  resolution / FPS, preprocessing / mirroring, screen / DPI geometry
  (including `devicePixelRatio` and monitor origin), and relevant
  runtime config. Raw and filtered gaze MUST be recorded where the
  official API exposes both. Frame, prediction, and target timestamps
  MUST be recorded so a sample is scored against the target that was
  actually shown, not the previous one.

### Planning Obligations *(required before implementation)*

These are specification requirements on `/speckit.plan`. They are
**not** unresolved product-scope questions. Implementation MUST NOT
begin until the plan records them.

1. Pin exact official GazeFollower repository, commit/version,
   model/checkpoint identification or hash where practical,
   dependency/version approach, and license/attribution.
2. Inspect official GazeInfo/output APIs and define the GazeSample
   contract without inventing fields.
3. Audit official filtering versus existing GazeKey smoothing; record
   the single pointing-signal choice (default: official filtered
   gaze).
4. Inspect and record the tested native calibration protocol and
   current upstream Preview / Calibration / result / accept /
   recalibrate behavior.
5. Design the pygame versus PySide6 lifecycle boundary for startup,
   recalibration, abort/reject, and shutdown, including camera
   ownership and event loops.
6. Complete the screen-geometry / DPI / window / QRect compatibility
   audit; list only legitimate transforms.
7. Publish the dependency-isolation audit and the exact GazeFollower
   → GazeKey handoff.
8. Record the constitution check: independently measured screen
   mapping remains the sealed measurement upstream; production
   implementation of gaze/calibration becomes GazeFollower rather than
   PCA4/Ridge; downstream still MUST NOT compensate via mapping
   tweaks.
9. Inventory obsolete legacy gaze runtime, tests, configuration, and
   dependencies for Stage G, to be deleted only after Stage F.

### Key Entities

- **Official GazeFollower pipeline**: The pinned official repository
  system that owns camera acquisition, preprocessing, inference,
  Preview UI, Calibration UI, native calibration/personalization,
  validity, filtering, and final screen-space gaze.
- **GazeKey downstream product**: Existing keyboard UI, live geometry,
  hit testing, focus, dwell, KeyAction / ActionDispatcher, OS typing,
  editing keys, prediction context, three suggestion slots, and
  autocomplete. Consumes gaze after the handoff; does not own
  Preview/Calibration.
- **Backend handoff**: The documented join after GazeFollower has
  produced gaze information. Not a reuse of PCA4/Ridge and not a
  post-GazeFollower learned remap.
- **GazeSample**: Backend-agnostic production gaze record defined in
  planning from official GazeInfo/output. Always includes screen
  position; includes other official semantics only when actually
  available.
- **Selected pointing signal**: The official gaze coordinate used for
  product hit testing. Expected initially to be GazeFollower filtered
  screen gaze. One intentional filter policy.
- **Legacy gaze runtime**: Historical GazeKey estimator stack
  (handcrafted u/v, FeatureExtractor gaze semantics, PCA/PCA4, Ridge,
  PCA-specific gates, legacy calibration protocol and corrections).
  Historical baseline and rollback/history until Stage G. Forbidden on
  the new production execution path.
- **Official Preview / Calibration experience**: GazeFollower-owned
  pygame UI and native protocol, including result/accept/recalibrate
  behavior. Used for startup and keyboard-initiated recalibration.
- **Live runtime layout**: Keyboard and suggestion-slot rectangles
  actually shown in that session (window position, DPI, QRects). The
  source of focus and evaluation targets.
- **Debug gaze dot**: Temporary Stage C developer/debug visualization
  of official GazeFollower output on the GazeKey keyboard. Not a
  replacement for official Preview and not a production visual
  redesign.
- **Mapped gaze**: Predicted screen position used for key focus.
  Sealed measurement upstream for typing. Must share the audited
  screen coordinate system.
- **Mapped key (focus)**: Keyboard control identified from mapped gaze
  via **live** key-hit geometry, before dwell.
- **Product-condition session**: One calibration + integrated product
  evaluation (and `hadar` / sweep when required) captured **with**
  the chin/head support.
- **Integrated acceptance record**: Written result of at least three
  product-condition sessions on the real keyboard and real OS typing
  path, including usability sweep, independent mapping metrics,
  provenance, and a pass / fail / inconclusive decision for cleanup.
- **Run provenance**: Per-run record of upstream commit, model/
  checkpoint identification, calibration mode/targets, camera
  configuration, preprocessing/mirroring, screen/DPI geometry,
  dependency/version, license/attribution, and runtime config.
- **Replay capture**: Local, gitignored recording sufficient to replay
  a session offline; derived metrics may be committed.
- **Pre-cleanup checkpoint**: Git commit/tag of the product
  immediately before Stage G cleanup.
- **Feature 004 record**: Specs, runs, and tags including
  `004-pca4-investigation-closeout-20260820` and
  `004-pre-pivot-exact-20260820`; read-only history for this feature.

## Success Criteria *(mandatory)*

All integrated acceptance measurements use the **chin/head support**.
Free-head runs MUST NOT decide cleanup.

Developer evaluation may measure these outcomes; evaluation tooling
MUST NOT become part of product enablement.

Feature 004 T060 figures (including 29% / 23% mapped-key, 78.2 px
median, 39% row, and the 6 pp / 2.8 px / 4 pp envelopes) and the
historical 67% / 55 px / 80% floors remain **reference evidence
only**. They MUST NOT gate whether integration may begin and MUST NOT
be treated as an automatic cleanup trigger.

Standalone official Preview / Calibration / pygame live-gaze success
is **discovery evidence** for starting integration. It MUST NOT be
treated as integrated product acceptance.

### Integrated production acceptance (must pass before Stage G cleanup)

- **SC-001**: **Repeatable product sessions** — At least **three**
  product-condition sessions are recorded on the integrated
  application. One successful calibration MUST NOT decide cleanup.
- **SC-002**: **Full required interaction area** — On every acceptance
  session, gaze visibly spans the full required X and Y interaction
  area of the live keyboard, including letter rows, editing controls,
  and suggestion slots.
- **SC-003**: **Letter-row reachability** — Letter rows are distinctly
  reachable. All active letter keys are reachable from live hitboxes.
- **SC-004**: **Editing-control reachability** — Space is reachable.
  Backspace is reachable. Shift, Enter, and other active editing
  controls are reachable.
- **SC-005**: **Suggestion-slot reachability** — All three suggestion
  slots are reachable from live hitboxes.
- **SC-006**: **No systematic vertical collapse** — Predicted Y
  travels with the user's vertical look rather than remaining nearly
  constant across top letter rows through Space / suggestions. A
  session that collapses to one letter row fails even if home-row
  letters look improved.
- **SC-007**: **Dwell-usable pointing** — Pointing is stable enough
  for the existing dwell interaction. Focus uses the intended live
  control from live geometry, not a stale or remapped substitute.
- **SC-008**: **Interactive latency** — Gaze updates remain usable for
  existing dwell (continuous pointing, not multi-second lag). Measured
  update rate and end-to-end latency are recorded. A target's score
  MUST use predictions from that target's time window, not the
  previous target.
- **SC-009**: **Real OS typing path** — Actual typing into an external
  application works through the existing action pipeline.
- **SC-010**: **Practical word check** — `hadar` is tested with
  suggestions disabled and recorded. It informs review; it MUST NOT
  override SC-006 (vertical collapse) or SC-003–SC-005 (required
  controls unreachable).
- **SC-011**: **Predictive text preserved** — Predictive suggestions
  work. Gaze-selection of suggestions works. Accepting a suggestion
  types the expected suffix + Space.
- **SC-012**: **Recalibration** — Recalibration uses the official
  GazeFollower flow and returns to a usable keyboard.
- **SC-013**: **Independent mapping metrics (evidence, not T060
  gate)** — Mapped-key, row, and pixel-error metrics are recorded on
  the integrated path where the existing benchmark can be reused
  without legacy estimator dependencies. Feature 004 T060 / A/B
  sessions MAY be cited as `eval_before`. These metrics MUST NOT be
  used as a reason to route GazeFollower through old mapping
  infrastructure, and they MUST NOT replace SC-002–SC-012 as the
  cleanup decision.
- **SC-014**: **Official calibration path** — Startup and
  recalibration use official GazeFollower Preview + Calibration +
  result/accept behavior. GazeKey does not host a substitute
  calibration-target UI. Legacy `keyboard15` / PCA calibration does
  not run on the production path.
- **SC-015**: **Estimator isolation** — Production path code does not
  import or call the forbidden historical estimator stack (FR-009).
  Planning's dependency audit exists. Where practical, an isolation
  test fails if that dependency appears.
- **SC-016**: **One pointing-signal policy** — Official GazeFollower
  filtering versus GazeKey smoothing has been audited. The live path
  uses one intentional pointing signal. Extra smoothing was not added
  to dress acceptance results.
- **SC-017**: **One screen geometry** — Before acceptance results are
  treated as on-screen mapping evidence, planning has recorded that
  GazeFollower coordinates, Qt/Windows coordinates, live hitboxes,
  and suggestion rectangles are compatible (DPI, `devicePixelRatio`,
  resolution, monitor origin, window position). Unproven upstream
  camera/screen constants were not copied. No learned remapping was
  applied.
- **SC-018**: **Lifecycle** — Sequential pygame then Qt ownership
  works for startup, recalibration, and shutdown. Sampling stops and
  GazeFollower resources are released on exit.
- **SC-019**: **User-independent architecture** — Shared product code
  contains no baked-in user-specific anatomical or calibration
  constants. If practical, a second-user smoke test is recorded
  before cleanup; if skipped, the record says so.
- **SC-020**: **GazeSample contract** — The plan records the chosen
  production GazeSample contract after inspecting official GazeInfo
  outputs, including which official fields were preserved and that
  unavailable fields were not invented.

Cleanup MUST NOT start until SC-001–SC-020 are recorded on the
integrated production path (FR-029, FR-033).

### After cleanup

- **SC-021**: A Git checkpoint taken before cleanup can restore the
  pre-cleanup product.
- **SC-022**: After cleanup, one production gaze pipeline remains, and
  Feature 004 history (specs, runs, commits, tags) is still present
  and readable.

### Fail / inconclusive (no destructive cleanup)

- **SC-023**: If any of SC-001–SC-018 fail, or sessions disagree so
  the result is inconclusive, GazeFollower is not accepted for
  cleanup, destructive removal of legacy gaze runtime has not
  occurred, rollback is through Git if needed, and a written
  integrated-acceptance record explains the result.

### Cross-cutting

- **SC-024**: **Run clarity** — After each integrated session a tester
  can state pass/fail, the usability sweep, and the primary mapping
  metrics without reading verbose logs. The FR-041 provenance fields
  are present on the run record.
- **SC-025**: **Principle XI vs official UI** — GazeKey does not host
  a metric-heavy calibration surface. Official GazeFollower UI is
  used as-is; any Principle XI conflict is recorded in the plan
  rather than “fixed” by restyling upstream.
- **SC-026**: **No product-above-gaze regression** — Existing dwell,
  OS typing, editing, predictive text, three suggestion slots, and
  autocomplete remain the Feature 003 / Feature 004 closeout
  behaviors except for the gaze/calibration source, unless a
  documented backend-interface requirement forced a minimal change.

## MVP Scope *(mandatory for GazeKey)*

**In scope**:

- Official GazeFollower as the production gaze-estimation and
  calibration subsystem, via a thin GazeKey adapter around the
  official library
- Official Preview UI, Calibration UI, result/accept/recalibrate
  behavior, native calibration/personalization, validity, and
  filtering
- Sequential pygame Preview/Calibration then PySide6 keyboard
  ownership, including recalibration and clean shutdown
- Backend-agnostic GazeSample contract defined in planning from
  official GazeInfo
- Keyboard gaze handoff with temporary debug gaze dot to prove
  standalone mapping survived integration
- Restore existing dwell, key selection, OS typing, editing,
  predictive text, three suggestion slots, and autocomplete
- Strict production-path isolation from PCA/PCA4/Ridge/handcrafted
  u/v and other forbidden legacy gaze modules
- Filter/smoothing audit (no accidental double filtering; prefer
  official filtered gaze)
- Audited shared screen/DPI/window/QRect geometry contract; no
  learned remapping
- One pinned official/native GazeFollower calibration protocol
  (chosen in planning from upstream 5 / 9 / 13 and the tested
  standalone flow); not an assumed `keyboard15` copy
- Product-condition multi-session **integrated** acceptance on the
  real keyboard and real OS typing path
- Independent mapping metrics where the existing benchmark can be
  reused without legacy estimator dependencies
- Per-run provenance and local gitignored replay captures
- Git rollback checkpoint before cleanup
- After integrated acceptance only: inventory-based removal of
  obsolete legacy gaze runtime
- Session/user-specific calibration data; optional second-user smoke
  test before cleanup
- Preservation of Feature 004 historical artifacts

**Out of scope**:

- Building GazeFollower only as a long-lived isolated research
  backend while PCA4 remains the normal application path
- Delaying integration until Feature 004 T060 percentage/noise
  formulas are beaten
- Making GazeKey host a candidate calibration fixation UI or
  recreating official Preview/Calibration in Qt
- Forcing production architecture to preserve the old estimator
  comparison contract
- Resuming or rewriting Feature 004's paused A–F task sequence
- Inventing a new gaze estimator or approximating GazeFollower from
  the paper
- Copying upstream into unrelated GazeKey modules and modifying it
  until it resembles the old architecture
- Using the historical estimator as a blueprint or routing
  GazeFollower through PCA4 / Ridge / handcrafted u/v / any legacy
  mapper
- Introducing EyeTheia, a third estimator, an ensemble, or a gaze
  fallback cascade
- Maintaining two blended live gaze pipelines for safety
- Adding extra smoothing or dwell/prediction retunes to inflate
  acceptance
- Silently falling back to GazeKey `keyboard15` without an upstream
  conflict report
- Copying unproven upstream camera/screen physical constants
- Baking this developer's anatomy or calibration into shared code
- New keyboard visual redesign, new prediction algorithm, new dwell
  algorithm, or unrelated Feature 002/003 behavior changes
- Saved multi-user profiles / language switching / multi-monitor as
  product features (session-specific calibration is in scope)
- Making evaluation part of product enablement
- Deleting Feature 004 specs, runs, commits, or tags
- Removing legacy gaze runtime before integrated acceptance, review
  of the acceptance record, and the pre-cleanup Git checkpoint
- Treating standalone official Preview success, historical 67% /
  55 px / 80%, T060 beat-formulas, regional reachability, or average
  correlations as cleanup-ready

## Assumptions

- **Product baseline**: Feature 003 remains the user-facing keyboard,
  dwell, OS typing, and predictive-text product. Feature 004 closeout
  (`004-pca4-investigation-closeout-20260820`) is historical mapping
  evidence and the pre-integration estimator. Feature 004 is
  paused/historical, not an input backlog of unfinished patches.
- **Why this feature exists**: Repeated Feature 004 evidence showed
  the current handcrafted vertical-feature + existing mapping stack
  ignores most of the vertical range under the product condition.
  Isolated feature tweaks did not yield a keepable Y signal. Official
  GazeFollower has now been run standalone on the target Windows
  machine with Python 3.11: Preview worked, native calibration
  completed, and the official pygame live-gaze example produced
  visually strong real-time screen mapping. The next mapping-
  foundation step is to integrate that official pipeline as the
  production gaze/calibration subsystem, then remove the obsolete
  legacy gaze runtime only after integrated acceptance.
- **Discovery vs acceptance**: Standalone official-repository success
  is necessary discovery evidence to start integration. It is not
  sufficient evidence to delete the old pipeline.
- **Official GazeFollower**: Primary technical reference is
  https://github.com/GanchengZhu/GazeFollower/tree/main
  The production gaze/calibration subsystem **is** that system,
  handed off to GazeKey, not a GazeKey reimplementation and not a
  PCA4 add-on. Exact commit/version is pinned in planning before
  implementation.
- **Historical estimator is baseline only**: Feature 004 closeout
  mapping is comparison/reference evidence, not a library for the
  production path.
- **Constitution check (planning)**: Constitution v1.3.0 still names
  PCA4 as the mapping-foundation implementation. This spec treats
  independently measured screen mapping as the sealed *measurement*
  upstream and selects GazeFollower as the production implementation
  of gaze/calibration. Downstream still consumes mapped gaze and MUST
  NOT compensate via mapping tweaks. `/speckit.plan` MUST record this
  constitution check.
- **Allowed GazeKey reuse**: live keyboard geometry, independent
  benchmark scoring that does not require the legacy estimator,
  product interaction, generic camera/display that does not change
  GazeFollower preprocessing.
- **Forbidden GazeKey reuse on the production path**: FeatureExtractor
  gaze semantics, PCA/PCA4, Ridge, `pca_vL`/`pca_vR`, 0.15 and other
  PCA-specific gates, legacy aggregation/clamps/outliers/vertical
  normalization, legacy estimator calibration constants, any mapper
  after GazeFollower screen coordinates.
- **Calibration protocol is official/native, not `keyboard15`**:
  Planning inspects the tested standalone protocol and upstream
  5 / 9 / 13-point modes, then records the protocol used by the
  product. GazeKey does not host calibration targets.
- **Calibration ⊥ benchmark**: Training targets and evaluation
  targets are logically independent. Calibration-location
  repeatability MAY be reported; it MUST NOT be the primary mapped-key
  rate.
- **Live layout is the geometry source**: Hitboxes for letters,
  editing controls, and all three suggestion slots are read from the
  runtime layout of that session.
- **T060 comparison is historical only**: Feature 004 free-head A/B
  (`14938da0bdf0`, `34fb259ccdfd`) and product-condition T060
  (`689c8a8ce90c`, `4f665467b260`) remain `eval_before` citations.
  Their percentage/noise formulas are not an integration-start gate
  and not an automatic cleanup trigger.
- **Three sessions minimum**: Matches constitution repeatability
  intent; one calibration is forbidden as a keep.
- **`hadar` is a development word**: recorded with suggestions
  unused; does not alone accept cleanup or replace the full keyboard
  path.
- **Single monitor, Windows desktop**, webcam already used by GazeKey
  and by the standalone GazeFollower discovery run. Primary validation
  may use the current developer; architecture must still be
  user-independent.
- **Replay includes timestamps and live layout** and stays gitignored;
  live sessions remain valid if replay is incomplete, provided that
  incompleteness is recorded.
- **No third backend**: If integrated GazeFollower is the wrong
  family of solution, outcome is document-and-rollback-via-Git, not
  “try another model in this feature.”
- **Cleanup is inventory-first and task-gated**: no mass delete; not
  before Stage F integrated acceptance and the pre-cleanup checkpoint.
- **KEEP/FAIL/INCONCLUSIVE apply** to integrated acceptance as a
  whole. Tuning GazeFollower against GazeKey MUST still be one
  logical change per measured iteration if planning finds
  configuration choices (including a later change of 5 vs 9 vs 13);
  unproven candidate tweaks are not stacked.
- **Which of 5 / 9 / 13 is pinned**, the exact GazeSample field set,
  the exact filter-policy exception if any, and the pygame/Qt
  lifecycle mechanism are **planning** outcomes after inspecting the
  official repository and the already-tested standalone flow, not
  specify guesses.
- **Platform Python/Windows constraints** of the current app remain;
  the standalone Python 3.11 discovery run is evidence that official
  GazeFollower can run on the target machine, not a substitute for
  the integrated lifecycle design.
