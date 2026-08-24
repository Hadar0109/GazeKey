# Contract: Production-path dependency isolation

**Feature**: `005-gazefollower-backend`

## Allowlist (production execution may import/call)

**Official GazeFollower** (`import gazefollower` and public submodules
required by the thin adapter): `GazeFollower`, `DefaultConfig`,
`GazeInfo`, `TrackingState`, `MGazeNetGazeEstimator` only if passing
the pinned `base.mnn` path.

**GazeKey backend-agnostic product**:

- `gazekey.typing.gaze_typing_runtime` (`MappedGazePoint`, `GazeTypingRuntime`)
- `gazekey.typing.dwell_engine`
- `gazekey.typing.action_dispatcher`
- `gazekey.typing.key_action`
- `gazekey.typing.key_hit_tester`
- `gazekey.typing.key_semantics`
- `gazekey.typing.typing_session`
- `gazekey.prediction.*`
- `gazekey.input.*`
- `gazekey.layout.*`
- `gazekey.ui.virtual_keyboard` (handoff + keyboard chrome only)
- `gazekey.ui.keyboard_layout`
- `gazekey.ui.dwell_progress_overlay`
- `gazekey.app_config` (non-calib-mode flags)
- New `gazekey/backend/` adapter

**Tools-only** (not product enablement): `tools/evaluation` scoring that
consumes `GazeSample` + live layout; `tools/preview` overlay for Stage C
if reused as developer debug.

## Forbidden on the production gaze path

Must not import, call, or route gaze through:

- `gazekey.features.extractor.FeatureExtractor` and gaze u/v helpers
- `gazekey.features.feature_types` as a live gaze contract
- `gazekey.features.feature_smoother.PcaFeatureSmoother`
- `gazekey.mapping` (`ridge`, `Pca4BaselineMapper`, `fit_calibration_mapper`,
  `row_bias`)
- `gazekey.mapping.config` PCA gates (`MIN_CATASTROPHIC_SCREEN_Y_AVG_V_CORR`
  0.15, `pca_vL` / `pca_vR`, `CALIBRATION_MODE = keyboard15`)
- `gazekey.calibration.session`, `targets`, `fixation_gate`, `quality`,
  `outliers`, `region_quality`
- `gazekey.ui.calibration_overlay`, `calibration_controller`,
  `calibration_finish`
- `gazekey.runtime.mapper_runtime.MapperRuntime` predict/fit
- `gazekey.tracking.tracking_manager`, `video_capture`, `eye_detector`
- `gazekey.typing.gaze_smoother.GazeSmoother` on the live pointing path
- `VirtualKeyboard._gaze_bias_x/y` as a learned remap
- Any mapper/correction after GazeFollower screen coordinates

Where practical, a pytest isolation test fails if `gazekey.backend`
imports a forbidden module.

## Dual-pipeline rule

Do not keep or start GazeKey `TrackingManager` / `EyeDetector` “for blink”
or “for safety.” Blink-during-dwell is handled by GazeSample validity
(status, SUCCESS, finite filtered xy, openness > 10) and
`MappedGazePoint.valid=False`. Rollback is Git, not a PCA4 fallback
cascade.
