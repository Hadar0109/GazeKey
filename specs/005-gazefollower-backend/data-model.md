# Data Model: GazeFollower Production Integration

**Feature**: `005-gazefollower-backend`  
**Date**: 2026-08-24  
**Source**: Official `GazeInfo` / `FaceInfo` / `DefaultConfig` plus GazeKey
downstream entities that remain unchanged.

## Production gaze record

### GazeSample

Backend-agnostic handoff from official GazeFollower to GazeKey. Defined
only from fields that exist on official `GazeInfo` after SAMPLING
`process_frame`.

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `timestamp_ns` | int | `GazeInfo.timestamp` | Camera callback `time.time_ns()` |
| `valid` | bool | derived | See validation below |
| `x` | float | `filtered_gaze_coordinates[0]` after R7 transform | Product pointing |
| `y` | float | `filtered_gaze_coordinates[1]` after R7 transform | Product pointing |
| `calibrated_x` | float \| None | `calibrated_gaze_coordinates[0]` after same transform | Unfiltered screen; diagnostics |
| `calibrated_y` | float \| None | `calibrated_gaze_coordinates[1]` after same transform | Diagnostics |
| `tracking_state` | str | `TrackingState.name` | `FACE_MISSING`, `SUCCESS`, `OUT_OF_BOUNDARIES`, `FAILURE` |
| `left_openness` | float \| None | `GazeInfo.left_openness` | Eye polygon area; not confidence |
| `right_openness` | float \| None | `GazeInfo.right_openness` | Same |

**Not in GazeSample** (exist upstream but must not enter the product
contract as invented or forbidden fields):

- `GazeInfo.features` — MNN embedding; official SVR input; forbidden Ridge input
- `GazeInfo.raw_gaze_coordinates` — model-space, not screen pixels
- `GazeInfo.event` — event detection not implemented upstream
- confidence/quality — not provided

### Validation rules

`valid` is True iff all of:

1. `GazeInfo.status` is True
2. `tracking_state` is `SUCCESS`
3. `filtered_gaze_coordinates` is a length-2 finite vector
4. `left_openness > 10` (official `DefaultConfig.eye_blink_threshold`)
5. `right_openness > 10` (same threshold)

Approved 2026-08-24. This rejects gaze during closed/blinking eyes
without the legacy EAR path. It is not a new blink-selection feature.

When `valid` is False, downstream builds `MappedGazePoint(x=0, y=0,
valid=False)` (existing typing contract): dwell **cancels** and does not
complete; no OS inject. Do **not** implement hold-last /
`filter_or_reject`. Stage F MUST include natural-blink coverage.

### MappedGazePoint (unchanged role)

Existing `gazekey.typing.gaze_typing_runtime.MappedGazePoint`. Production
fills it from `GazeSample` (`x`, `y`, `valid`) only. No mapper predict.

## Lifecycle

### GazeFollowerRuntimeState

```text
UNINITIALIZED
  -- construct GazeFollower() --> READY_NO_CAMERA

READY_NO_CAMERA
  -- preview() --> PREVIEWING --> READY_NO_CAMERA
  -- calibrate() --> CALIBRATING --> READY_NO_CAMERA
     (inner loop: R restarts CALIBRATING; Space → ACCEPTED)
  -- start_sampling() --> SAMPLING

SAMPLING
  -- get_gaze_info / subscriber --> GazeSample stream
  -- stop_sampling() --> READY_NO_CAMERA
  -- recalibrate request --> STOP_SAMPLING --> PREVIEWING --> CALIBRATING
     --> start_sampling --> SAMPLING

ACCEPTED
  -- required before first SAMPLING and before keyboard typing

SHUTDOWN
  -- stop_sampling if needed --> release() --> terminal
```

Official `CameraRunningState`: `PREVIEWING`, `CALIBRATING`, `SAMPLING`,
`CLOSING`. Adapter must never request a start mode unless current state
is `CLOSING`.

### CalibrationAccept

Official result UI: Space → accept, R → recalibrate. No GazeKey pass/fail
gate (`pca_vL` 0.15 forbidden). `cali_available` / mean Euclidean error
are official result-screen data only, not GazeKey mapper quality.

## Geometry audit record (per session)

| Field | Source |
|-------|--------|
| `gf_screen_size` | `DefaultConfig.screen_size` (screeninfo monitor 0) |
| `pygame_mode` | pygame display size used for Preview/Calibration |
| `qt_geometry` | `QScreen.geometry()` |
| `device_pixel_ratio` | `QScreen.devicePixelRatio()` |
| `monitor_origin` | Qt `geometry.x/y` vs assumed (0,0) |
| `keyboard_origin` | keyboard `mapToGlobal(0,0)` |
| `transform` | `identity` \| `origin` \| `origin+dpr` |

## Run provenance

| Field | Source |
|-------|--------|
| `upstream_repo` | https://github.com/GanchengZhu/GazeFollower |
| `upstream_commit` | `553920edcb7998c029828677f50f6d8eb4a16249` |
| `upstream_version` | `1.0.2` |
| `model_path` | packaged `base.mnn` |
| `model_sha256` | `2f96b95275fe6d7b79e98df3237ebb96e15ef5522c96968f08167da7e1954a96` |
| `cali_mode` | `13` |
| `camera` | webcam_id 0, 640×480, 30 FPS (official WebCamCamera defaults) |
| `python` | 3.11.x (discovery: 3.11.9) |
| `license` | LICENSE-CC-BY-NC-SA |
| `filter` | `HeuristicFilter(look_ahead=3)` |
| `physical_screen_size` | `None` (official default) |

## Unchanged downstream entities

TypingContext, WordSuggestion, SuggestionSet, KeyAction,
DwellFrameResult, TypingSession — Feature 003 contracts unchanged.
Live layout keys / suggestion QRects remain the hit-test source of truth.

## Replay capture (optional, gitignored)

GazeSample stream + timestamps + live layout snapshot + provenance.
Raw webcam/face/eye frames must not be committed.
