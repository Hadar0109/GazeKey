# T080 — one-pipeline verification

**Date**: 2026-08-24  
**After**: T079

**SC-021 / SC-022**: one production gaze pipeline. No second live estimator.

Verified in source:

- `main.py`: `run_official_startup` → Qt keyboard → `wire_official_gaze_typing`
- `gazekey/backend/startup.py`: `wire_official_gaze_typing` connects GazeSample to
  `GazeLoopController.on_gaze_sample`
- `gazekey/runtime/gaze_loop.py`: GazeSample → MappedGazePoint → dwell only
- `gazekey/tracking/`, `gazekey/features/`, `gazekey/mapping/`,
  `gazekey/calibration/`, `mapper_runtime.py`, `tracking_controller.py` deleted
- Product CLI has no `--calib-mode` / keyboard15 override
- Pytest: **228 passed** (Python 3.11 venv)

Residual gaze error remains accepted. Accuracy work and key resize were not
reopened. T057 `hadar` is still not scored.
