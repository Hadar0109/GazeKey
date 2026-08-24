# Research: GazeFollower Production Integration

**Feature**: `005-gazefollower-backend`  
**Date**: 2026-08-24  
**Sources inspected**: GazeKey tree under `gazekey/`, `main.py`, `tools/`;
official GazeFollower clone at `C:\Users\Lenovo\Desktop\GazeFollower`
(commit `553920edcb7998c029828677f50f6d8eb4a16249`, tag `v1.0.2`); installed
egg `gazefollower-1.0.2-py3.11.egg` in that clone's Python 3.11.9 venv;
standalone session logs under `C:\Users\Lenovo\GazeFollower\log\` from
2026-08-24.

No GazeFollower behavior in this plan is inferred from the spec alone.

**Review session 2026-08-24:** Python 3.11, GazeSample validity (including
openness > 10), CC BY-NC-SA 4.0 license of record, official UI as-is,
geometry STOP gate, and no hold-last are **resolved decisions**, not
pending review. See `plan.md` §Resolved review decisions.

---

## R1. Upstream pin and dependency strategy

**Decision**: Pin official GazeFollower **v1.0.2** at git commit
`553920edcb7998c029828677f50f6d8eb4a16249` (repo
https://github.com/GanchengZhu/GazeFollower, tag `v1.0.2`, message
`update requirements.txt`, 2026-01-05). Install as the **`gazefollower`
package** (PyPI `gazefollower==1.0.2` or `pip install` from that commit).
Do **not** copy upstream modules into `gazekey/`. Adapter code only
`import gazefollower`.

Default model: packaged `gazefollower/res/model_weights/base.mnn`
(6,245,556 bytes). SHA-256
`2f96b95275fe6d7b79e98df3237ebb96e15ef5522c96968f08167da7e1954a96`.
`MGazeNetGazeEstimator()` loads this path when `model_path=""`.

Official runtime dependencies (`setup.py` / egg `requires.txt`):
`mediapipe`, `MNN`, `numpy`, `opencv-python`, `pandas`, `pygame`,
`screeninfo`. **License of record (approved 2026-08-24, conservative):**
repository `LICENSE-CC-BY-NC-SA` and README — **CC BY-NC-SA 4.0**.
Record attribution and the non-commercial/share-alike restriction.
`version.py` prints `Creative Commons Attribution 4.0 (CC BY 4.0)`; treat
that as **upstream metadata inconsistency only**. Do not reinterpret the
project as CC BY 4.0. Commercial use is **outside Feature 005** and would
require a separate licensing review/permission.

**Python (approved 2026-08-24):** Feature 005 and the resulting GazeKey
product runtime use **Python 3.11**. Discovery environment was 3.11.9.
Do **not** spend Feature 005 effort proving GazeFollower on the existing
Python 3.14 `.venv`. Implementation/tasks MUST create/rebuild the GazeKey
environment on Python 3.11 and verify all retained GazeKey dependencies
there.

**Rationale**: Matches the machine already used for Preview, native
calibration, and `example/pygame_example.py`. Thin adapter around the
official library is required by FR-023.

**Alternatives considered**:

- Reimplement from the paper — forbidden.
- Vendor-copy into `gazekey/` and edit until it resembles PCA4 — forbidden.
- Run gazefollower on the existing 3.14 venv — **rejected 2026-08-24**;
  do not spend Feature 005 proving that stack.
- Set `DefaultConfig.camera_position` / `screen_physical_size` from this
  developer's anatomy — forbidden (FR-035). Leave `screen_physical_size=None`
  so labels stay normalized screen fractions (official default).

---

## R2. Official GazeInfo and production GazeSample

**Decision**: Inspected `gazefollower/misc/GazeInfo.py` and
`GazeFollower.process_frame` SAMPLING path. Official fields:

| Official field | Meaning (from source) | Production GazeSample |
|----------------|------------------------|------------------------|
| `timestamp` | Copied from `FaceInfo.timestamp`; camera callback uses `time.time_ns()` | `timestamp_ns` |
| `status` | `True` after successful MNN forward | required; part of `valid` |
| `tracking_state` | `FACE_MISSING`, `SUCCESS`, `OUT_OF_BOUNDARIES`, `FAILURE` | preserve as enum name |
| `filtered_gaze_coordinates` | HeuristicFilter output of **pixel** calibrated gaze | **pointing `x`,`y`** |
| `calibrated_gaze_coordinates` | SVR output after `convert_to_pixel` (screen px) | diagnostic unfiltered screen |
| `raw_gaze_coordinates` | First two values of the MNN embedding (`res[:2]`), **not** screen px | do **not** expose as screen gaze |
| `left_openness` / `right_openness` | Copied from FaceInfo eye polygon area | preserve; blink-adjacent |
| `event` | `EyeMovementEvent`; README lists Event Detection as unimplemented | omit from product contract |
| `features` | Full MNN embedding used by official SVR | **omit** (forbidden Ridge input) |

No official confidence/quality scalar exists. Do not invent one.

`valid` is True iff **all** of the following hold (**approved
2026-08-24**):

1. `GazeInfo.status == True`
2. `tracking_state == SUCCESS`
3. `filtered_gaze_coordinates` is a finite length-2 vector
4. `left_openness >` official `eye_blink_threshold` (10)
5. `right_openness >` official `eye_blink_threshold` (10)

Invalid samples MUST become `MappedGazePoint.valid=False` (dwell
cancels; no OS typing). Do not implement hold-last /
`filter_or_reject`. This is not a new blink-selection feature; see R10.

Product hit-testing uses `x,y` = filtered screen coordinates after the
geometry transform in R7.

**Rationale**: Spec forbids invented fields and forbids feeding GazeFollower
into PCA/Ridge. Raw model coordinates are not screen space.

**Alternatives considered**: `(x,y)`-only contract — rejected; official
validity/timestamp/filtered/calibrated/openness are actually available.
Using `raw_gaze_coordinates` as the pointing signal — rejected; not pixels.
Using `calibrated_gaze_coordinates` as pointing — rejected; spec prefers
official filtered output.

---

## R3. Filter policy (no double-filter)

**Decision**: The first integrated production pointing signal is
`GazeInfo.filtered_gaze_coordinates` from official `HeuristicFilter(look_ahead=3)`.
GazeKey MUST NOT apply:

- `gazekey.typing.gaze_smoother.GazeSmoother` (screen EMA; currently used
  in `MapperRuntime.map_gaze_screen_xy` preview/debug, **not** in the
  product typing `key_accuracy_predict_screen_xy` path)
- `GazeSmoother.filter_or_reject` hold-last (**approved 2026-08-24**: do
  not port; invalid samples cancel dwell)
- `gazekey.features.feature_smoother.PcaFeatureSmoother` (u/v EMA before
  Ridge; **is** on the current typing predict path)

`OneEuroFilter` exists upstream but is **not** the GazeFollower default.
Do not switch filters to dress acceptance.

Dwell (`DwellEngine`, 0.9 s) remains interaction logic, not smoothing.

**Rationale**: Official sampling already filters calibrated pixels
(`GazeFollower.process_frame` SAMPLING). Adding GazeKey smoothers would
double-filter. The pygame example draws `filtered_gaze_coordinates`.

**Alternatives considered**: Bypass HeuristicFilter and use calibrated
pixels — only if a later measured Stage F session proves the look-ahead
delay is unusable for dwell; not the first path. Keep PcaFeatureSmoother
— it requires FeatureExtractor u/v; forbidden.

---

## R4. Official 5/9/13 calibration and the tested protocol

**Decision**: Pin **13-point** (`DefaultConfig.cali_mode = 13`,
`CalibrationMode.THIRTEEN_POINT`). `example/pygame_example.py` constructs
`GazeFollower()` with no config override, so the standalone live-gaze
run used the official default.

Inspected `CalibrationController`:

- Grid: `generate_points()` builds a 5×9 = 45-point normalized mesh with
  50 px margins **hard-coded against 1920×1080**, then indexes:
  - 5-point: `[23, 1, 9, 37, 45, 23]`
  - 9-point: `[23, 1, 5, 9, 19, 27, 37, 41, 45, 23]`
  - 13-point: `[23, 1, 5, 9, 12, 16, 19, 27, 30, 34, 37, 41, 45, 23]`
- Index 0 is a warm-up: samples are **not** stored while
  `_current_index == 0`. Then 13 collection points (45 frames each after
  1.5 s prepare, 0.5 s wait). Matches ~50 s calibrate in the 12:07 log
  (`calibrating shutdowns`).
- Collection rejects frames unless `gaze_info.status` and both eye
  openness values `> eye_blink_threshold` (default 10).
- With `screen_physical_size is None` (default), labels are normalized
  fractions; `convert_to_pixel` multiplies by `config.screen_size`
  (screeninfo monitor 0).
- `CalibrationUI.draw_cali_result`: Space = accept (`True`), R =
  recalibrate (`False`). `GazeFollower.calibrate()` loops until accept.
- Fitting is official `SVRCalibration`, not GazeKey Ridge/PCA4.
- `fine_tuning()` raises `NotImplementedError`.

GazeKey MUST NOT host `keyboard15` / `CalibrationOverlay`. Do not copy
`camera_position = (17.15, -0.68)` into GazeKey; it is unused unless
physical screen size is set.

**Rationale**: Matches the tested standalone flow. 9-point is only shown
in `example/config_example.py`, which was not the live-gaze example.

**Alternatives considered**: Force 9-point because config_example mentions
it — rejected; that file is not the tested pygame example. Fall back to
GazeKey `keyboard15` — forbidden.

---

## R5. pygame / PySide6 lifecycle

**Decision**: Sequential ownership, matching official `Camera` state
machine. `start_previewing` / `start_calibrating` / `start_sampling` each
require `CameraRunningState.CLOSING` and call `open()`. Each stop path
`close()`s the camera. Preview and calibrate are **blocking** pygame
loops (`preview()`, `calibrate()`). Do **not** embed pygame in a Qt
widget and do **not** recreate Preview/Calibration in Qt.

Startup:

1. Do **not** construct `QApplication` yet (avoid Qt setting a different
   DPI awareness before pygame/screeninfo).
2. Construct official `GazeFollower()` (does not open the camera yet).
3. `preview()` — pygame fullscreen at `config.screen_size`, camera
   PREVIEWING, blocking until official UI exits; camera CLOSING.
4. `calibrate()` — same window policy as official API (`win=None` creates
   fullscreen pygame); loop until Space accept; camera CLOSING.
5. `pygame.quit()` and destroy the pygame window.
6. `start_sampling()` — camera SAMPLING thread; `_write_sample` keeps
   `_gaze_info` for `get_gaze_info()`.
7. Construct `QApplication` + existing `VirtualKeyboard` **without**
   `TrackingManager`.
8. Adapter delivers `GazeSample` onto the Qt thread (queued signal;
   `get_gaze_info()` is written from the camera thread without a dedicated
   gaze lock).

Recalibration (keyboard Calibrate / dwell calibrate):

1. Disable OS inject; pause Qt gaze consumption.
2. Hide/minimize the Qt keyboard (do not keep a visible competing
   fullscreen).
3. `stop_sampling()` (required; sampling→preview/calibrate raises
   `RuntimeError`).
4. `pygame.init()`; official `preview()` + `calibrate()`.
5. `pygame.quit()`; `start_sampling()`; show keyboard; resume consume.

Abort/reject: official UI has no separate cancel; Space accepts, R
restarts calibration inside `calibrate()`. If the user closes the pygame
window, treat as unaccepted: do not resume typing as if newly calibrated;
keep previous accepted model if one exists, otherwise fail closed without
PCA4 fallback.

Shutdown: `stop_sampling()` if sampling; `release()` (camera, filter,
estimator, face alignment, calibration); then Qt `app.quit()`.

**Rationale**: Official camera cannot be in two modes. Standalone logs
show open→close→open between preview, calibrate, and sampling.

**Alternatives considered**: Qt-hosted pygame subsurface — extra
complexity, restyles ownership. Keep Qt running and spawn pygame in a
subprocess — splits calibration state. Run pygame after QApplication —
DPI/event-loop risk; only if Stage C proves pre-Qt pygame is worse.

---

## R6. Camera ownership

**Decision**: GazeFollower `WebCamCamera` (`webcam_id=0`, 640×480, 30 FPS)
is the **only** production capture. GazeKey `TrackingManager` /
`VideoCapture` / `EyeDetector` MUST NOT start on the Feature 005
production path.

Upstream `WebCamCamera.close()` joins the capture thread then calls
`_cap.release()` only if `not self._cap.isOpened()` (looks inverted).
Do not patch upstream in GazeKey modules. Adapter shutdown still calls
official `stop_sampling()` + `release()`. If a camera remains busy,
report it; do not start a second OpenCV capture “to help.”

**Rationale**: Spec forbids a competing webcam pipeline.

---

## R7. Screen-coordinate contract

**Decision**: Official filtered coordinates are pixels in the space
`config.screen_size` from `screeninfo.get_monitors()[0]`, origin
top-left, Y down, after `convert_to_pixel` (normalized × screen_size when
`screen_physical_size is None`). The pygame example used a **1920×1080**
fullscreen surface and drew `filtered_gaze_coordinates` directly.

GazeKey hit-testing uses Qt **global** coordinates
(`QWidget.mapToGlobal`, `layout_inspector` QRects).

Allowed transforms only:

1. Add monitor origin if screeninfo/pygame origin is (0,0) of the selected
   monitor and Qt global includes `QScreen.geometry().x/y`.
2. Divide or multiply by `QScreen.devicePixelRatio()` if one toolkit
   reports physical pixels and the other logical pixels.
3. Identity if Stage C shows they already match.

Forbidden: Ridge/PCA, affine “fit,” hand-tuned offsets, GazeKey
`_gaze_bias_x/y`, `clamp_xy` mapper clip bounds, copying
`camera_position` cm constants.

Stage A/C runtime geometry audit is a **hard gate**. First record
actual screeninfo size, pygame mode, Qt global geometry, DPR, monitor
origin, and keyboard origin. Then apply identity, origin offset, and/or
DPR only. If those cannot align official filtered gaze with live key
QRects, **STOP and report** — do not add a mapper, bias, or affine
correction. Do **not** change upstream `generate_points` behavior
preemptively (including its 1920×1080 hard-coded margins).

**Rationale**: Spec allows only legitimate coordinate-space/window
transforms.

---

## R8. Smallest adapter boundary

**Decision**: New production package `gazekey/backend/` (name indicative):

- Wraps `GazeFollower`, `DefaultConfig`, official `preview` / `calibrate`
  / `start_sampling` / `stop_sampling` / `release` / `get_gaze_info`
- Maps official `GazeInfo` → `GazeSample`
- Applies R7 transform
- Exposes a Qt-thread-safe sample callback
- Isolation test: this package MUST NOT import `gazekey.features`,
  `gazekey.mapping`, `gazekey.calibration`, `gazekey.tracking`

Existing downstream stays:

`GazeSample → MappedGazePoint(x,y,valid) → hit_test_layout_keys(live layout)
→ DwellEngine → GazeTypingRuntime → ActionDispatcher → OsInputAdapter`

Do not change dwell timing, suggestion ranking, keyboard visuals, or OS
injection except the gaze source and the Calibrate action invoking
official Preview+Calibration.

**Rationale**: Spec: GazeKey begins at the handoff.

---

## R9. Preserve Feature 002/003 product above the handoff

**Decision**: Keep `DwellEngine`, `ActionDispatcher`, `KeyAction`,
`TypingSession`, `TypingContext`, `WordProvider`, three suggestion slots,
autocomplete suffix+Space, Shift/Backspace/Space/Enter, layout builder,
dwell overlay. Stage C uses a temporary debug dot (reuse
`tools/preview` overlay or an equivalent developer overlay on the
keyboard) **before** reconnecting `GazeTypingRuntime.on_mapped_gaze`.

`on_calibrate_clicked` currently calls `_start_calibration()` (legacy
overlay). After Stage E it must call the official GF flow.

---

## R10. Blink-path audit (resolved 2026-08-24)

**Finding**: Current blink handling **depends on the legacy MediaPipe
camera pipeline**.

1. `TrackingManager` owns OpenCV camera 0 and feeds frames to
   `EyeDetector` (MediaPipe Face Landmarker, `models/face_landmarker.task`).
2. EAR on GazeKey eye contours sets `EyeData.is_blinking`.
3. `FeatureExtractor.from_eye_data` copies `blink`, zeros u/v and
   confidence when blinking.
4. `FixationGate` rejects blink samples during **legacy** calibration.
5. `GazeSmoother.filter_or_reject` exists to hold last screen point
   during blink but **is not called** anywhere; product typing uses
   `key_accuracy_predict_screen_xy` (feature EMA + Ridge), so blink
   currently appears as missing/low-confidence features, not hold-last.

Official GazeFollower:

- README lists **Blink Detection** under “NEED TO IMPLEMENTATION”.
- There is **no** `is_blinking` on `GazeInfo`.
- Calibration already drops frames when eye polygon area
  (`left_eye_openness` / `right_eye_openness`) ≤ `eye_blink_threshold`
  (10). The same openness values are copied onto `GazeInfo` during
  sampling.
- GazeFollower uses **its own** MediaPipe FaceMesh inside
  `MediaPipeFaceAlignment` on **its** camera thread — not GazeKey's
  `EyeDetector`.

**Approved decision**:

1. Do not keep or start `TrackingManager` / `EyeDetector` for blink.
2. Do not recompute GazeKey EAR from GF `face_landmarks`.
3. Use the backend-independent GazeSample validity rule in R2
   (status, SUCCESS, finite filtered xy, both openness values > 10).
4. This preserves rejecting gaze during closed/blinking eyes without
   preserving the legacy EAR implementation. It is **not** a new
   blink-selection feature.
5. Invalid sample → `MappedGazePoint.valid=False`: cancels dwell, does
   not complete dwell, does not cause OS typing. Stage F MUST cover
   natural blinks.
6. Do **not** implement hold-last / `filter_or_reject`.

**Rejected**: Second OpenCV/MediaPipe capture alongside GazeFollower.
**Rejected**: Routing GF frames into GazeKey `EyeDetector`.
**Rejected**: Status-only invalidation (openness thresholds are required).

---

## R11. Constitution check (planning obligation 8)

Constitution v1.3.0 names **PCA4** as the mapping-foundation
implementation. This feature replaces that **implementation** with
official GazeFollower while keeping independently measured screen mapping
as the sealed **measurement** upstream. Downstream still MUST NOT retune
mapping to fix typing. Justified in plan Complexity Tracking.

Principle XI vs official Calibration UI: GazeFollower draws instruction
text, progress **percentage on the target**, beep, and a result screen
with “Calibration succeed/failed”, red/green dots, and
“Press Space … OR R”. **Approved 2026-08-24 as planned:** use official
Preview/Calibration/result UI as-is. Do not recreate or restyle it in
Qt. Principle XI continues to forbid a GazeKey-hosted metric-heavy
overlay.

---

## R12. Stage G inventory (delete only after Stage F)

See `plan.md` Stage G and `contracts/dependency-isolation.md`. Inventory
is recorded now; deletions wait for integrated acceptance + Git
checkpoint.

---

## R13. Evaluation without legacy estimator

Independent mapped-key / row / pixel-error scoring MUST consume
`GazeSample` screen points + **live** layout QRects. Do not call
`FeatureExtractor` / Ridge to score GazeFollower. Reuse
`tools/evaluation` **scoring math** where it is already backend-agnostic;
replace the eye-data ingest. Evaluation remains tools-only (not product
enablement).
