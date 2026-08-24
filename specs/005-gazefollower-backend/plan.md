# Implementation Plan: GazeFollower Production Integration

**Branch**: `005-gazefollower-backend` | **Date**: 2026-08-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-gazefollower-backend/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow. **`tasks.md` is not created by this command.**

## Summary

Replace GazeKey's MediaPipe landmarks → handcrafted u/v → PCA4/Ridge
calibration/mapping subsystem with the **official GazeFollower** pipeline
already proven standalone on this Windows machine (Python 3.11.9,
`gazefollower` v1.0.2, commit `553920edcb7998c029828677f50f6d8eb4a16249`).
GazeFollower owns camera, Preview, Calibration, inference, SVR
personalization, HeuristicFilter, and filtered screen gaze. GazeKey
begins at a thin adapter (`GazeSample`) and keeps the existing keyboard,
dwell, OS typing, and predictive-text path.

Standalone Preview/calibration/pygame live-gaze success is **discovery
evidence only**. Stage F integrated acceptance (three chin-support
sessions on the real keyboard and OS typing path) is required before
Stage G deletion of legacy gaze runtime.

## Technical approach

1. **Stage A (this plan)** — pin upstream, GazeSample, filter, 13-point
   protocol, pygame/Qt lifecycle, geometry, isolation, blink validity.
   Implementation tasks MUST rebuild the GazeKey environment on Python
   3.11 and verify retained GazeKey dependencies there.
2. **Stage B** — `main.py` runs official `preview()` + `calibrate()` +
   `start_sampling()` before the Qt keyboard; no legacy overlay.
3. **Stage C** — existing keyboard + temporary debug gaze dot from
   official filtered gaze; prove mapping survived the handoff; no extra
   remap.
4. **Stage D** — `GazeSample` → `MappedGazePoint` → live hit-test →
   existing dwell / ActionDispatcher / OS / suggestions.
5. **Stage E** — Calibrate control invokes official Preview+Calibration;
   clean `release` on exit.
6. **Stage F** — three product-condition integrated sessions, including
   natural-blink coverage (invalid samples cancel dwell; no OS typing).
7. **Stage G** — inventory-based deletion only after F + Git checkpoint.

Do not implement in this command. Do not create `tasks.md`. Do not
modify Feature 004. Do not route GazeFollower through Ridge/PCA4. Do not
recreate Preview/Calibration in Qt.

Details: [research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/), [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: Python **3.11** (discovery: 3.11.9). **Approved.**
The resulting GazeKey product runtime uses 3.11. Do **not** spend Feature
005 effort proving GazeFollower on the existing Python 3.14 `.venv`.
Tasks MUST create/rebuild the GazeKey environment on 3.11 and verify all
retained GazeKey dependencies there.

**Primary Dependencies**: official `gazefollower==1.0.2` (mediapipe, MNN,
numpy, opencv-python, pandas, pygame, screeninfo); GazeKey PySide6,
pynput. Do not add EyeTheia or a third estimator.

**Storage**: GazeFollower session files under user-home `GazeFollower/`
(upstream default); GazeKey `runs/` for derived summaries only. Raw
webcam frames gitignored.

**Testing**: pytest isolation (backend must not import forbidden
modules); contract tests that `GazeSample` → `MappedGazePoint` →
hit-test does not call FeatureExtractor/Ridge; invalid-sample tests
(`valid=False` cancels dwell, no hold-last); Stage C/F live webcam USER
GATEs including natural blinks that cancel dwell and do not type.

**Target Platform**: Windows desktop, single monitor, chin/head support
for acceptance.

**Project Type**: Desktop application (sequential pygame then PySide6).

**Performance Goals**: Interactive pointing for existing 0.9 s dwell;
official camera 30 FPS / 640×480; HeuristicFilter look-ahead 3 frames is
accepted official latency.

**Constraints**: Spec FR-001–FR-041; no double-filter; no learned
geometry remap; no second webcam; Feature 004 read-only; license of
record **CC BY-NC-SA 4.0** (attribution + non-commercial/share-alike;
commercial use out of Feature 005); `screen_physical_size=None`.

**Scale/Scope**: One production gaze path; adapter around official
library; preserve Feature 002/003 product above the handoff.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Reference: `.specify/memory/constitution.md` (GazeKey v1.3.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| Accuracy First | Mapping remains independently validated; downstream consumes mapped gaze only and MUST NOT compensate via mapping changes | ✅ (screen mapping measured independently via SC-013; implementation is GazeFollower not PCA4 — see Complexity Tracking) |
| Measurable Progress | Mapping changes use key-hit / pixel / row / repeatability; other features use their own spec acceptance | ✅ (SC-013 metrics without legacy estimator; SC-001–SC-012 product usability) |
| Simple Pipeline | Sealed upstream through mapped gaze; new mapping layers justified | ✅ (`GF filtered screen gaze → live geometry → focus/dwell`; no post-GF mapper) |
| Spec Before Code | `spec.md`, clarifications, `plan.md`, and `tasks.md` approved before implementation | ✅ (`tasks.md` next; no implementation now) |
| Feature Scope Control | Scope matches the active feature spec | ✅ (no EyeTheia, no dwell/prediction redesign) |
| Testable Architecture | Tracking, calibration, mapping, evaluation, UI, typing/OS separable | ✅ (official GF owns gaze; adapter; existing typing package) |
| Run Clarity | Each mapping run answers pass/fail + key metrics via simple summary | ✅ (FR-037) |
| Documentation Hierarchy | Spec Kit docs are source of truth for this phase | ✅ |
| Targeted Cleanup | Active path unambiguous; inventory-first deletions via approved tasks | ✅ (Stage G deferred) |
| Simple Logging | Readable logs; quiet normal runs; optional verbose | ✅ |
| Minimal Calibration UI | Fixation screen shows only dot + optional progress | ⚠️ justified — official GazeFollower UI is used as-is (progress %, instructions, result screen). GazeKey will not host a substitute overlay. |

**Post-design re-check**: Same. 2026-08-24 review session closed Python
3.11, GazeSample validity (status + SUCCESS + finite filtered xy +
openness > 10), CC BY-NC-SA 4.0, official UI as-is, geometry STOP gate,
and no hold-last. Principle XI remains a justified violation: official
Preview/Calibration/result UI used unmodified.

## Project Structure

### Documentation (this feature)

```text
specs/005-gazefollower-backend/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
│   ├── gaze-sample.md
│   ├── lifecycle.md
│   ├── dependency-isolation.md
│   └── screen-geometry.md
└── tasks.md             # NOT created by /speckit-plan
```

### Source Code (repository root)

```text
main.py                          # Will sequence GF pygame then Qt (Stage B)
gazekey/
  backend/                       # NEW thin adapter (indicative path)
  typing/                        # KEEP dwell, dispatcher, hit-test, session
  prediction/                    # KEEP
  input/                         # KEEP
  layout/                        # KEEP live geometry
  ui/
    virtual_keyboard.py          # KEEP keyboard; stop owning legacy calib
    keyboard_layout.py           # KEEP
    dwell_progress_overlay.py    # KEEP
    calibration_*.py             # LEGACY — unused on production path until G
  tracking/                      # LEGACY camera/EAR — do not start (R10)
  features/                      # LEGACY u/v — forbidden production import
  mapping/                       # LEGACY PCA4/Ridge — forbidden
  calibration/                   # LEGACY keyboard15/gates — forbidden
  runtime/
    gaze_loop.py                 # Rewire to GazeSample
    mapper_runtime.py            # LEGACY until G
    tracking_controller.py       # LEGACY until G
tools/evaluation/                # Rewire ingest to GazeSample; keep scoring
tests/                           # Isolation + contract tests
```

**Structure Decision**: Stay a single Python desktop app. Add a thin
`gazekey/backend/` adapter around `import gazefollower`. Do not vendor
the official repo into unrelated GazeKey gaze modules. Legacy packages
remain in tree until Stage G.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution names PCA4 as mapping-foundation **implementation** | Spec replaces that implementation with official GazeFollower; independently measured screen mapping remains the sealed measurement upstream | Keeping PCA4 as production path contradicts the rewritten spec and the standalone discovery evidence |
| Principle XI vs official Calibration UI (text, % progress on target, result screen) | Spec requires official Preview/Calibration UI unmodified | Restyling in Qt or stripping official chrome would violate FR-003 |
| Two UI toolkits (pygame then Qt) | Upstream Preview/Calibration are pygame; keyboard is PySide6 | Recreating GF UI in Qt is forbidden |
| Blink behavior cannot stay GazeKey EAR without a second camera | **Approved 2026-08-24**: `GazeSample.valid` uses official status/SUCCESS/finite filtered xy and openness > 10; no TrackingManager/EyeDetector; not a new blink-selection feature | Second webcam pipeline forbidden; hold-last `filter_or_reject` rejected |

## Planning obligation register

| Obligation | Resolution |
|------------|------------|
| 1. Upstream pin | R1 — v1.0.2 / `553920ed…` / `base.mnn` SHA-256; CC BY-NC-SA 4.0; Python 3.11 env rebuild |
| 2. GazeSample | R2 — validity approved: status, SUCCESS, finite filtered xy, openness > 10 |
| 3. Filter policy | R3 — official HeuristicFilter; disable GazeKey screen + feature EMA |
| 4. Native protocol | R4 — **13-point** official default; Space/R result UI |
| 5. pygame vs Qt lifecycle | R5 / `contracts/lifecycle.md` |
| 6. Geometry | R7 — Stage A/C hard STOP gate; identity/origin/DPR only |
| 7. Isolation audit | R8 / `contracts/dependency-isolation.md` |
| 8. Constitution check | this plan + Complexity Tracking |
| 9. Stage G inventory | below; delete only after Stage F |

## Architecture before vs after

**Before (Feature 004 closeout product)**

```text
OpenCV VideoCapture (GazeKey)
  → MediaPipe Face Landmarker (EyeDetector)
  → FeatureExtractor (u/v, blink EAR)
  → PcaFeatureSmoother
  → PCA4 / Ridge (keyboard15 + GazeKey overlay + pca_vL gates)
  → optional GazeSmoother (preview path)
  → live QRect hit-test → dwell → ActionDispatcher → OS
  → TypingContext / 3 suggestions
```

**After (Feature 005 production path)**

```text
GazeFollower WebCamCamera
  → official MediaPipeFaceAlignment + MGazeNet (base.mnn)
  → official pygame Preview + Calibration (SVR, 13-point)
  → HeuristicFilter
  → GazeSample (filtered screen xy + validity)
  → legitimate origin/DPR transform only
  → live QRect hit-test → dwell → ActionDispatcher → OS
  → TypingContext / 3 suggestions (unchanged)
```

Forbidden: `GazeFollower → PCA/Ridge → keyboard` and
`GazeFollower → legacy mapper → keyboard`.

## Runtime sequences

### Startup

1. Parse args. Do **not** start `TrackingManager`.
2. `GazeFollower()` with official `DefaultConfig` (`cali_mode=13`,
   `screen_physical_size=None`).
3. Official `preview()` (blocking pygame). Camera opens then closes.
4. Official `calibrate()` until Space accept (R retries inside). Camera
   opens then closes.
5. `pygame.quit()`.
6. `start_sampling()`.
7. `QApplication` + `VirtualKeyboard` without legacy calibration overlay
   and without GazeKey camera.
8. Stage C debug dot, then Stage D typing.

Matches standalone `example/pygame_example.py` plus Qt after sampling
starts. 2026-08-24 logs show the same camera open/close/open pattern.

### Recalibration

Hide Qt keyboard → `stop_sampling()` → official `preview()` +
`calibrate()` → `pygame.quit()` → `start_sampling()` → show keyboard.
Do not call `_start_calibration()` (legacy overlay).

### Shutdown

Stop Qt consumer → `stop_sampling()` → `release()` → quit Qt. No PCA4
fallback if GF fails.

## Dependency allowlist and forbidden modules

See [contracts/dependency-isolation.md](./contracts/dependency-isolation.md).

**Allow**: `gazefollower` public API; `gazekey.backend`; typing /
prediction / input / layout / keyboard UI listed there.

**Forbid on production gaze path**: FeatureExtractor gaze semantics,
PCA/PCA4, Ridge, `pca_vL`/`pca_vR`, 0.15 gate, legacy vertical
normalization, aggregation/clamps/outliers, `keyboard15`,
`MapperRuntime` fit/predict, `GazeSmoother` on live pointing,
`TrackingManager` camera.

## GazeSample contract

See [data-model.md](./data-model.md) and
[contracts/gaze-sample.md](./contracts/gaze-sample.md).

Pointing: official **filtered** screen coordinate after geometry
transform. Diagnostics: calibrated (unfiltered) screen coordinate.
Validity (**approved**): `GazeInfo.status == True`,
`tracking_state == SUCCESS`, filtered coordinates finite,
`left_openness > 10`, `right_openness > 10` (official
`eye_blink_threshold`). Invalid → `MappedGazePoint.valid=False` (dwell
cancels; no OS typing). No hold-last. No invented confidence. No
`features` field.

## Filter policy

Use official `HeuristicFilter` output. Do not apply
`PcaFeatureSmoother` or `GazeSmoother` on the production path. Do not
port `filter_or_reject` hold-last. Dwell is not a smoother. Do not
retune look-ahead to dress Stage F.

## Screen-coordinate contract

See [contracts/screen-geometry.md](./contracts/screen-geometry.md).

Stage A/C runtime geometry audit is a **hard gate**. First record
actual screeninfo size, pygame mode, Qt global geometry, DPR, monitor
origin, and keyboard origin. Then identity/origin/DPR only. If those
cannot align official gaze with live QRects, **STOP and report** — no
mapper, bias, or affine correction. Do not change upstream
`generate_points` preemptively.

## Camera / UI ownership model

One camera: GazeFollower `WebCamCamera`. One screen owner at a time:
pygame during Preview/Calibration, Qt during keyboard. Official camera
state must be `CLOSING` before the next start_* call.

## Blink-path finding

**Approved 2026-08-24.** Do not keep or start `TrackingManager` /
`EyeDetector` for blink. Official GF has no blink event; product
validity uses GazeSample rules (status, SUCCESS, finite filtered xy,
both openness values > official threshold 10). This preserves rejecting
gaze during closed/blinking eyes without the legacy EAR
implementation. It is **not** a new blink-selection feature.

Invalid samples cancel dwell via `MappedGazePoint.valid=False` and must
not complete dwell or cause OS typing. Stage F MUST include natural-blink
coverage. Do not implement hold-last.

## Pinned upstream provenance

| Item | Value |
|------|--------|
| Repository | https://github.com/GanchengZhu/GazeFollower |
| Commit | `553920edcb7998c029828677f50f6d8eb4a16249` |
| Tag / version | `v1.0.2` / `1.0.2` |
| Model | `gazefollower/res/model_weights/base.mnn` |
| Model SHA-256 | `2f96b95275fe6d7b79e98df3237ebb96e15ef5522c96968f08167da7e1954a96` |
| Calibration | official 13-point (`DefaultConfig.cali_mode=13`) |
| Camera | webcam 0, 640×480, 30 FPS |
| Filter | `HeuristicFilter(look_ahead=3)` |
| Python | **3.11** product runtime (discovery 3.11.9). Rebuild GazeKey env on 3.11; do not prove GF on 3.14 |
| License of record | **CC BY-NC-SA 4.0** (`LICENSE-CC-BY-NC-SA` + README). `version.py` “CC BY 4.0” is upstream metadata inconsistency only. Commercial use is outside Feature 005 |
| Tested example | `example/pygame_example.py` (filtered cursor) |

Do not copy `camera_position=(17.15, -0.68)` into GazeKey.

## Stage G cleanup inventory (deferred)

Delete or stop shipping **only after Stage F + Git checkpoint**. Until
then code may remain on disk but MUST NOT run on the production path.

**Gaze runtime / calibration**

- `gazekey/tracking/` (`tracking_manager.py`, `video_capture.py`,
  `eye_detector.py`, `tracking_bridge.py`)
- `gazekey/features/` (`extractor.py`, `feature_types.py`,
  `feature_smoother.py`)
- `gazekey/mapping/` (`ridge.py`, `row_bias.py`, `base.py`, `config.py`
  PCA/keyboard15 constants)
- `gazekey/calibration/` (`session.py`, `targets.py`, `fixation_gate.py`,
  `quality.py`, `outliers.py`, `region_quality.py`)
- `gazekey/ui/calibration_overlay.py`, `calibration_controller.py`,
  `calibration_finish.py`, `camera_preview_window.py`
- `gazekey/runtime/mapper_runtime.py`, `tracking_controller.py`
- `gazekey/typing/gaze_smoother.py` (after confirming no tools need it)
- `VirtualKeyboard` legacy calib/mapper fields (`_gaze_mapper`,
  `_gaze_bias_*`, `_feature_smoother`, `_init_calibration_on_startup`
  overlay path)

**Dependencies / assets (GazeKey-owned copies)**

- Direct `mediapipe` / `models/face_landmarker.task` as GazeKey tracking
  deps (GF still uses its own mediapipe internally)
- `app_config --calib-mode` keyboard15 override as a product flag

**Tests** that exist only to pin PCA4/u/v/fixation-gate/ridge — rewrite
or drop in inventory tasks; keep typing/prediction/layout tests.

**Preserve**: `specs/004-*`, `runs/` Feature 004 artifacts, tags
`004-pca4-investigation-closeout-20260820` and
`004-pre-pivot-exact-20260820`. Do not resume Feature 004 tasks.

## Resolved review decisions (2026-08-24)

All six planning-review items are **closed**. No blocker remains before
`/speckit.tasks`.

1. **Python 3.11 — APPROVED.** Product runtime is Python 3.11 (discovery
   3.11.9). Do not prove GazeFollower on the existing 3.14 venv. Tasks
   include creating/rebuilding the GazeKey environment on 3.11 and
   verifying retained GazeKey dependencies there.
2. **Blink / sample validity — APPROVED.** No legacy camera for blink.
   `GazeSample.valid` requires `status==True`, `tracking_state==SUCCESS`,
   finite filtered coordinates, and both openness values `> 10`.
   Invalid → `MappedGazePoint.valid=False` (dwell cancel, no OS typing).
   Not a new blink-selection feature. Stage F covers natural blinks.
   No hold-last / `filter_or_reject`.
3. **License — APPROVED, conservative.** License of record is
   **CC BY-NC-SA 4.0** (repository `LICENSE-CC-BY-NC-SA` and README).
   Record attribution and non-commercial/share-alike. The CC BY 4.0
   string in `version.py` is upstream metadata inconsistency only. Do
   not reinterpret as CC BY 4.0. Commercial use is outside Feature 005
   and would need a separate licensing review/permission.
4. **Principle XI — APPROVED as planned.** Official GazeFollower
   Preview/Calibration/result UI as-is. Do not recreate or restyle in Qt.
5. **Screen geometry — APPROVED as a hard gate.** Record actual
   screeninfo, pygame mode, Qt global geometry, DPR, monitor origin,
   keyboard origin first. Identity/origin/DPR only. If those cannot
   align gaze with live QRects, STOP and report. Do not change
   upstream `generate_points` preemptively. No mapper/bias/affine.
6. **Invalid sample behavior — APPROVED.** No hold-last. Invalid
   samples cancel dwell through `MappedGazePoint.valid=False`.
