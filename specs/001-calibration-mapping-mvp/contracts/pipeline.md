# Contract: MVP Pipeline

**Version**: 1.0.0  
**Feature**: `001-calibration-mapping-mvp`

## Purpose

Define the single active processing pipeline from camera frame to benchmark result.

## Stages (in order)

| Stage | Input | Output | Owner module |
|-------|-------|--------|--------------|
| Capture | Webcam frame | `EyeData` | `gazekey/tracking/` |
| Features | `EyeData` | `FrameFeatures` | `gazekey/features/extractor.py` |
| Calibrate | `FrameFeatures` stream | `CalibrationSession` + samples | `gazekey/calibration/` |
| Fit | `CalibrationSession` | `GazeMapping` (`pca4_baseline`) | `gazekey/mapping/ridge.py` |
| Preview | `FrameFeatures` + `GazeMapping` | screen `(x, y)` dot | `gazekey/ui/gaze_preview` |
| Benchmark | `GazeMapping` + test keys | `BenchmarkRun` | `gazekey/evaluation/` |
| Summarize | Session/benchmark outcome | `RunSummary` | `gazekey/evaluation/` |

## Invariants

1. Only **one** calibration path is reachable from `main.py` → `VirtualKeyboard`.
2. `GazeMapping` exists only after `CalibrationSession.status == passed`.
3. `BenchmarkRun` requires a valid `GazeMapping`; blocked otherwise.
4. Preview and benchmark use the **same** `GazeMapping.predict()` — no alternate runtime mappers.
5. Intent scoring, dwell selection, and OS injection are **not** stages in this pipeline.
6. Only `pca4_baseline` is used for Fit/Predict — no poly12, IDW, or multi-candidate switching.
7. Camera preview window is **not** shown on the calibration fixation overlay (CQ-4).

## Threading

- Capture + `EyeDetector` run on `TrackingManager` worker thread.
- `TrackingBridge` delivers `EyeData` to main Qt thread.
- Calibration, fit, preview, benchmark, and UI run on main thread.

## Failure propagation

| Failure | Behavior |
|---------|----------|
| No face / camera | Calibration cannot start or pauses; message off fixation overlay |
| Calibration failed | No mapping, no preview, no benchmark |
| Benchmark failed | Summary records fail; user may recalibrate |
