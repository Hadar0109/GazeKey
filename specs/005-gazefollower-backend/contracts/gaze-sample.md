# Contract: GazeSample handoff

**Feature**: `005-gazefollower-backend`  
**Direction**: official GazeFollower → GazeKey interaction layer  
**Not**: GazeFollower → PCA/Ridge → keyboard

## Producer

Official `GazeFollower` after `start_sampling()`. Samples come from
`get_gaze_info()` / `_write_sample` subscriber, populated in
`process_frame` when `CameraRunningState.SAMPLING`.

Pointing coordinate (pre-transform): `GazeInfo.filtered_gaze_coordinates`
(HeuristicFilter of pixel-converted calibrated gaze).

## Consumer

GazeKey `GazeTypingRuntime.on_mapped_gaze` via `MappedGazePoint`.
Hit-test: `hit_test_layout_keys` on that session's live layout.

Stage C consumer: debug gaze dot only (no dwell).

## Schema

See [data-model.md](../data-model.md) `GazeSample`.

## Invariants

1. Adapter MUST NOT import `gazekey.features`, `gazekey.mapping`,
   `gazekey.calibration`, or `gazekey.tracking`.
2. Adapter MUST NOT write `GazeInfo.features` into GazeSample or into
   any mapper.
3. `x,y` used for hit-test MUST be the selected official filtered
   coordinate after the documented geometry transform only.
4. `valid` is True only when `GazeInfo.status == True`,
   `tracking_state == SUCCESS`, filtered coordinates are finite, and
   both `left_openness` and `right_openness` are `>` official
   `eye_blink_threshold` (10).
5. Invalid samples MUST set `MappedGazePoint.valid=False` (dwell
   cancels; dwell does not complete; no OS typing). Do not implement
   hold-last / `filter_or_reject`.
6. No extra GazeKey screen EMA or feature EMA on this path.
7. Natural blinks are Stage F acceptance coverage, not a new blink
   feature.
