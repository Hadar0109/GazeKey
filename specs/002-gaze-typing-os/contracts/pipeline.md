# Contract: Product Pipeline (002)

**Version**: 1.1.0  
**Feature**: `002-gaze-typing-os`

## Purpose

Active product pipeline from camera frame to OS key delivery. Upstream through
mapping is **unchanged** from `001`.

## Stages (product)

| Stage | Input | Output | Owner |
|-------|-------|--------|-------|
| Capture → Features → Calibrate → Fit → Predict | (as 001) | MappedGazePoint | existing `gazekey/` packages |
| Key detect | MappedGazePoint | OS-bound key? | `gazekey/typing/` + layout |
| Select | key + dt / mouse | KeyAction? or SystemControl | `gazekey/typing/` |
| Dispatch (request) | KeyAction | ActionRequest + adapter call | `gazekey/typing/` |
| OS inject | KeyAction | ActionDelivery / OsInjectResult | `gazekey/input/` |

## Non-product (separate developer entry points)

| Capability | Placement |
|------------|-----------|
| Read-only preview | `tools/preview/` entry (not a product mode) |
| Key-hit benchmark | `tools/evaluation/` entry (not a product mode) |
| Debug/artifact writers | `tools/debug/`, tools evaluation writers |

## Invariants

1. Calibration/mapping fit/predict MUST NOT import typing input or dwell.
2. Dwell/UI MUST NOT import `pynput`.
3. Only `OsInputAdapter` performs native injection.
4. Typing auto-starts after calibration when a **usable** mapper / mapped-gaze
   state is available. **Usable** = normal calibration flow has produced a
   mapper capable of supplying mapped gaze for runtime use. Auto-start MUST NOT
   require `001` benchmark thresholds.
5. Pause/Resume never enters KeyAction→OS path; Pause clears pending Shift.
6. UI layout: fullscreen calib as today → top-half keyboard; no reposition in 002.
7. Obsolete future/intent/selection/dormant typing are not pipeline stages
   (removed in cleanup before new typing build).
8. Implementation order: cleanup → post-cleanup gate → inject skeleton → focus
   validation → full dwell/typing.

## Threading

Unchanged: worker capture; main-thread dwell/dispatch/inject.
