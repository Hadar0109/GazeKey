# MEMORY_BANK.md — GazeKey (Virtual Keyboard)

This file is **architectural memory** for future agents. It captures how the system actually works (threads, data contracts, calibration math, persistence), plus fragilities and implied TODOs.

---

## 1. Project Overview

### What the project does
**GazeKey** is a webcam-based, eye-tracking driven virtual keyboard overlay for hands-free typing. It uses **MediaPipe Face Landmarker** to extract **eye contour + iris landmarks**, converts them into **eye-relative gaze ratios**, maps them to **screen coordinates via calibration**, and triggers keys using **dwell selection** (no click/blink confirm).

### Main goals
- Provide a **transparent, always-on-top** keyboard overlay (PySide6/Qt).
- Track gaze in real time on a background thread and feed UI safely.
- (Not working well) Calibrate gaze-to-screen mapping robustly for typical laptop distances.
- (Not working well) Support stable gaze selection via **hit testing + smoothing + dwell**.
- (Not finished) Inject keystrokes into other apps (pynput planned; currently internal buffer only).

### Main technologies
- **PySide6**: UI (overlay keyboard, calibration overlay, optional camera preview).
- **OpenCV** (`opencv-python`): webcam capture.
- **MediaPipe Tasks** (`mediapipe.tasks.python.vision.FaceLandmarker`): facial landmarks, iris landmarks.
- **NumPy**: calibration fitting, stats.
- **pytest**: unit tests (calibration + dwell/hit-testing + text buffer).

### High-level workflow
1. `main.py` creates `QApplication`, shows `VirtualKeyboard`.
2. `VirtualKeyboard` loads saved calibration from `calibration_data.json` (project root).
3. `TrackingManager` starts camera capture and runs detection loop on a **background thread**.
4. Worker thread emits `EyeData` to main thread via `TrackingBridge` (Qt signal).
5. Main thread:
   - If calibrating: convert `EyeData` → gaze ratios, feed `CalibrationOverlay` session.
   - If calibrated: gaze ratios → mapper → UI coordinate stretch → smoothing → hit test → dwell → activate key action.
6. Key activation updates an internal `QLineEdit` buffer (`TextBufferController`).

---

## 2. Architecture Summary

### Important folders / responsibilities
- `main.py`
  - **App entrypoint**. Instantiates `VirtualKeyboard`.
- `gazekey/ui/`
  - `virtual_keyboard.py`: main overlay keyboard UI + orchestrator for calibration and gaze typing.
  - `calibration_overlay.py`: full-screen 5-point calibration UX and timers.
  - `camera_preview_window.py`: optional floating preview widget (currently not wired into main UI flow).
- `gazekey/tracking/`
  - `video_capture.py`: OpenCV camera wrapper; captures frames and converts BGR→RGB.
  - `eye_detector.py`: MediaPipe Face Landmarker wrapper; returns `EyeData` (iris centers + eye contours). Has simple EAR-based blink detection.
  - `tracking_manager.py`: background thread loop; calls `EyeDetector.detect()`; manages stats; exposes latest frame for preview.
- `gazekey/calibration/`
  - `gaze_features.py`: converts `EyeData` into **(horizontal_ratio, vertical_ratio)** (0..1-ish) using eye-relative bounding boxes; also legacy `average_iris_pixels`.
  - `calibration_session.py`: session state machine; per-point validation; IQR filtering; final validation; fit mapper.
  - `calibration_validation.py`: global sanity checks across 5 points to reject “no real eye movement”.
  - `gaze_mapper.py`: `InterpolationGazeMapper` (IDW/Shepard interpolation) + mirroring selection (`flip_x`).
  - `calibration_store.py`: versioned JSON persistence, legacy model rejection.
  - `tracking_bridge.py`: Qt signal bridge for thread-safe EyeData forwarding.
- `gazekey/typing/`
  - `gaze_typing_controller.py`: glues hit-testing + dwell + focus feedback callbacks.
  - `key_hit_tester.py`: caches global rects of keys; hit test with margins/snap; ambiguity rejection.
  - `dwell_selector.py`: dwell state machine with miss tolerance + cooldown + single-fire lock.
  - `gaze_smoother.py`: adaptive EMA smoothing for mapped screen coords.
  - `gaze_ui_mapper.py`: stretches calibrated screen bounds into the actual typing UI region (control bar + keyboard).
  - `text_buffer.py`: internal QLineEdit text editing (NOT OS-level typing).
  - `key_semantics.py`: maps key labels to action strings (e.g., `"⌫" → "BACKSPACE"`).

### Main execution / data flow (real code)
**Worker thread**
- `TrackingManager._tracking_loop()`:
  - `VideoCapture.get_frame()` → RGB frame
  - `EyeDetector.detect(frame, timestamp_ms)` → `EyeData`
  - Calls callback (if set) with `EyeData`

**Thread boundary**
- `VirtualKeyboard._ensure_tracking_started()` starts tracking with callback = `TrackingBridge.forward`.
- `TrackingBridge.forward()` emits Qt signal `eye_data_received`.

**Main/UI thread**
- `VirtualKeyboard._on_eye_data_main_thread(eye_data)`:
  - Updates status label based on detection state / calibration state.
  - If calibrating: `gaze_ratios(eye_data)` → `CalibrationOverlay.add_sample(h,v)`.
  - Else if calibrated and keyboard expanded:
    - `gaze_ratios(eye_data)` → `mapper.map_point(h,v)` → `map_gaze_to_typing_ui()` stretch
    - `GazeSmoother.filter(x,y)` → `GazeTypingController.tick(x,y,dt)`
    - Hit-test → dwell progress → activate → `action_from_button()` → `on_key_pressed()` → `TextBufferController.apply_key()`.

### Component communication conventions
- **Tracking → UI**: *only* through `TrackingBridge` Qt signal to avoid cross-thread UI calls.
- **Calibration**:
  - `VirtualKeyboard` owns calibration lifecycle, but `CalibrationOverlay` owns timers and uses `CalibrationSession`.
  - Gaze sampling only occurs during `CalibrationSession` `COLLECT` phase.
- **Typing**:
  - `GazeTypingController` is UI-agnostic except it receives a `keyboard_root` QWidget and returns `QPushButton` targets via callbacks.

### External integrations / services
- **Webcam** via OpenCV.
- **MediaPipe model file**: `models/face_landmarker.task` (expected relative path). Downloading is mentioned in README but not implemented in code; the file must exist or MediaPipe init raises.

No network services, no server API, no database.

---

## 3. Core Design Decisions (with “why”)

### Use gaze ratios (eye-relative) instead of raw iris pixels
- Implemented in `gazekey/calibration/gaze_features.py:gaze_ratios()`.
- **Why**: raw camera-space positions vary heavily with head distance/position; ratios computed within each eye’s contour bounding box are more stable across face sizes and allow consistent calibration at typical webcam distances.
- Ratios follow **GazeTracking** semantics (roughly right=0, center≈0.5, left=1; top=0, bottom=1).

### Background thread tracking + Qt signal bridge
- `TrackingManager` runs capture + MediaPipe detection in a daemon thread.
- `TrackingBridge` emits EyeData to main thread.
- **Why**: MediaPipe + OpenCV per-frame work can block UI; Qt requires UI updates on main thread.

### 5-point calibration + strong validation
- Calibration overlay collects 5 points: TL, TR, center, BL, BR (`compute_calibration_targets()`).
- Each point: **PREPARE 2s** (ignore samples) then **COLLECT 2s** (sample each valid frame).
- Validations:
  - Per-point: minimum sample count, max std spread, and minimum shift from previous point mean.
  - Global: minimum span on both axes, diagonal TL↔BR span, consecutive shifts, and corner ordering separation.
- **Why**: Without explicit validation, users often “don’t move eyes enough” or move head instead, producing a mapper that causes random key activations.

### Interpolation mapper (IDW/Shepard) instead of affine polynomial
- `InterpolationGazeMapper` stores the 5 gaze-ratio points and their 5 screen targets and maps by inverse-distance weighting in (h,v) space.
- **Why**: With only 5 sparse points and small gaze feature movements, simple interpolation keeps exactness at calibration points and avoids overfitting/instability of higher-order fits.

### Dwell selection designed to be forgiving but not spammy
- `DwellSelector`:
  - dwell duration default **1.25s**
  - **miss tolerance**: up to 5 consecutive `None` frames before resetting (handles brief face/iris drops)
  - **global cooldown**: 0.25s to prevent double-fire
  - **single-fire lock**: same key cannot re-fire until gaze leaves it
- **Why**: Webcam iris tracking is jittery and occasionally drops; dwell must survive short gaps while preventing accidental repeated activations.

### Gaze-to-UI “stretch” layer
- `map_gaze_to_typing_ui()` takes mapper output in global screen space and remaps it into the actual typing region (control bar + keyboard widget), with extra bottom extrapolation.
- **Why**: Calibration targets cover the full screen, but typing targets are concentrated at the bottom overlay; without remapping, keys near the bottom row (Space/Ctrl) would be hard to reach.

---

## 4. Important Business / Logic Rules

### Tracking / EyeData rules
- `EyeDetector` returns `EyeData(face_detected=False)` when:
  - no face landmarks, OR
  - **both** iris centers are invalid, OR
  - detect() throws an exception.
- Blink is detected by EAR (`_EAR_BLINK_THRESHOLD=0.20`); when blinking:
  - `EyeDetector` returns `EyeData(face_detected=True, is_blinking=True)` with no iris/eye lists.
  - `gaze_ratios()` explicitly returns `None` for blinking frames.

### Calibration rules (must remain consistent)
- Five targets with 10% margins; order is fixed and relied on by validation and diagnostics.
- Each point collection must have:
  - ≥ `MIN_SAMPLES=20`
  - std spread ≤ `MAX_SPREAD_RATIO=0.08`
  - shift from previous dot mean ≥ `MIN_SHIFT_FROM_PREVIOUS=0.012`
- After collection: IQR filter (1.5×IQR on X and Y) must still leave ≥ 20 samples.
- Global validation thresholds:
  - span_x ≥ 0.015 AND span_y ≥ 0.015
  - TL↔BR diagonal ≥ 0.025
  - consecutive shift ≥ 0.012 for each step
  - corner separation: left vs right AND top vs bottom ≥ 0.012 (polarity-agnostic; supports mirrored cameras)

### Mapping rules
- Mapper chooses `flip_x` by trying both `False`/`True` and picking lowest RMS, but requires gaze spread ≥ `MIN_GAZE_SPREAD=0.015`.
- `InterpolationGazeMapper.map_point()` clips output to min/max rect of the 5 calibration screen points; prints a throttled warning if clipping is large (>50px).

### Typing rules
- Gaze typing is only active when:
  - keyboard is expanded (`is_expanded`)
  - not calibrating
  - `_gaze_mapper` is loaded
- Hit-testing:
  - only `QPushButton` with `objectName` in `{ "keyboardKey", "gazeTarget" }` is considered.
  - uses tight rect containment first; else chooses nearest snap rect if distance ≤ 40px and not ambiguous (second-best within 4px => return None).
- Text actions are internal:
  - `CTRL`, `ALT`, `SHIFT` are ignored by `TextBufferController`.
  - `ENTER` appends `"\n"` to a `QLineEdit` (note: QLineEdit is single-line; this is logically inconsistent UI-wise).

---

## 5. API Contracts

### In-process data contracts

#### `EyeData` (`gazekey/tracking/eye_detector.py`)
Fields (subject-centric):
- `face_detected: bool`
- `is_blinking: bool`
- `subject_left_iris_center: Optional[(x,y)]` in normalized coordinates
- `subject_right_iris_center: Optional[(x,y)]`
- `subject_left_eye_landmarks: Optional[List[(x,y)]]` (16 contour points)
- `subject_right_eye_landmarks: Optional[List[(x,y)]]`

Properties:
- `.left_iris_center`, `.right_iris_center`, `.left_eye_landmarks`, `.right_eye_landmarks` map to subject_* fields.

**Implicit contract**: All landmark coords are normalized (0..1) in frame space.

#### Tracking callback contract
- `TrackingManager.start_tracking(callback)` calls `callback(eye_data)` every loop iteration, regardless of detection success. The callback must be thread-safe (in this project: it just emits a Qt signal).

#### `gaze_ratios(eye_data)` (`gazekey/calibration/gaze_features.py`)
Returns:
- `Optional[(h,v)]` where values are clipped to [0,1].
- Returns `None` if no face, blinking, or insufficient landmarks.

#### Gaze typing controller contract (`gazekey/typing/gaze_typing_controller.py`)
- `tick(screen_x, screen_y, dt)` accepts `None` for missing tracking; it calls dwell update with `None` and can preserve progress (miss tolerance is in `DwellSelector`).

### Persistence / file formats

#### `calibration_data.json` (project root)
Path: `DEFAULT_CALIBRATION_PATH = <repo_root>/calibration_data.json`

Stored by `CalibrationStore.save()` with:
- `version`: 5
- `timestamp`: ISO UTC
- `screen_targets`: 5 points (global desktop pixels)
- `iris_means`: 5 gaze-ratio points (means per target)

Plus mapper data:
- For interpolation (current):
  - `model`: `"interpolation"`
  - `feature`: `"gaze_ratio"` (required to load)
  - `iris_points`: 5 gaze points used internally by mapper (may incorporate flip handling)
  - `screen_points`: 5 screen points used by mapper
  - `flip_x`: bool
  - `frame_w`: float (legacy/aux; ratios don’t use it)
- For legacy affine:
  - `model`: `"affine"`
  - `matrix`: 2x3
  - `flip_x`, `frame_w`

Load rules:
- Versions allowed: 1..5, but **interpolation data with version < 5 is rejected** and forces recalibration.
- Explicit legacy models (`quadratic`, `normalized_affine`, `separate_linear`) are rejected.

---

## 7. Environment Variables

**None are defined or used** in the codebase. Configuration is currently hardcoded:
- Camera id: `TrackingManager(camera_id=0)`
- Model path: `"models/face_landmarker.task"`
- Calibration path: `<repo_root>/calibration_data.json`
- Timing constants: `PREPARE_MS`, `COLLECT_MS`, dwell durations, etc.

If adding env vars, the most likely candidates are:
- `GAZEKEY_CAMERA_ID`
- `GAZEKEY_MODEL_PATH`
- `GAZEKEY_CALIBRATION_PATH`
- `GAZEKEY_TARGET_FPS`
- `GAZEKEY_DWELL_SEC`

---

## 8. Known Issues / Technical Debt

### Functional gaps
- **OS-level typing injection not implemented**: typing currently only updates the on-screen `QLineEdit` via `TextBufferController`. README mentions `pynput` integration as next step.
- **Camera preview not actually wired** in `VirtualKeyboard`:
  - `camera_preview_window` exists and `_on_eye_data_main_thread()` tries to update it if present, but nothing creates/shows it in the main UI flow.
- **`QLineEdit` newline behavior**: `TextBufferController.apply_key("ENTER")` appends `"\n"` to a QLineEdit which is typically single-line; UI may not display/handle it as intended.

### Potential correctness/robustness problems
- **Camera preview color space mismatch**:
  - `TrackingManager` stores RGB frames (because `VideoCapture` converts BGR→RGB).
  - `CameraPreviewWindow.update_frame()` docstring says BGR; it comments out BGR→RGB conversion and uses the frame “as-is”.
  - Net: preview may have swapped colors depending on source.
- **`EyeDetector` returns `face_detected=False` when both iris centers are missing**, even if a face is detected (eye contours are still extracted before iris checks). This collapses “face present but iris missing” into “no face” at the EyeData level.
- **Calibration assumes “head stays mostly still”**; no explicit head pose normalization is done. Users moving head can pass some checks but still produce unstable mapping.
- **Multi-monitor / non-primary screens**: calibration overlay uses `QApplication.primaryScreen().geometry()` and typing region mapping assumes primary screen coords. Secondary-monitor placement may break mapping/targets.
- **Hard-coded camera settings** (640x480@30) may not be honored by all webcams; downstream assumptions may drift.

### Fragile areas (handle carefully)
- Thread boundary: only `TrackingBridge` should cross threads. Avoid direct UI updates from tracking thread.
- Calibration versioning: loader is strict; if you change mapper schema, bump version and update load rules.
- Hit testing: depends on `objectName` conventions (`keyboardKey`, `gazeTarget`) and visibility; layout changes must call `mark_keyboard_dirty()`.

---

## 10. Useful Commands

### Run application
```bash
python main.py
```

### Run unit tests
```bash
pytest -q
```

### Run camera / tracking diagnostic scripts (OpenCV windows; press `q` to quit)
```bash
python test_camera_simple.py
python test_camera_face.py
python test_camera_tracking.py
python test_eye_tracking.py
```

### Install dependencies
```bash
pip install -r requirements.txt
```

---

## 11. Glossary (project-specific)

- **EyeData**: Per-frame tracking output containing iris centers + eye contours (normalized coords), plus flags.
- **Gaze ratios**: \((h,v)\) derived from iris position inside each eye’s bounding box; intended to be stable across face size/distance.
- **Calibration overlay**: Full-screen UI showing 5 dots; collects gaze ratios to build a mapper.
- **Calibration session**: State machine for PREPARE/COLLECT per dot, including IQR filtering and validation.
- **Mapper / Gaze mapper**: Component mapping gaze ratios to global screen pixels. Current default: **IDW interpolation** (`InterpolationGazeMapper`).
- **flip_x**: Boolean indicating horizontal mirroring correction; chosen during fit to handle mirrored camera orientation.
- **Typing region stretch**: Remapping from full-screen calibration bounds to the overlay’s actual interactive area (control bar + keyboard).
- **Hit testing**: Selecting which button rect a gaze point corresponds to; includes snap margin and ambiguity rejection.
- **Dwell**: Selecting a key by maintaining gaze focus on it for a time window (default 1.25s).
- **Locked key**: DwellSelector mechanism to prevent repeated firing of the same key until gaze leaves.

