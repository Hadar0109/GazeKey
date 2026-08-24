# Contract: GazeFollower pygame ↔ GazeKey Qt lifecycle

**Feature**: `005-gazefollower-backend`

## Ownership

| Phase | Screen | Camera | Event loop |
|-------|--------|--------|------------|
| Process start | none | closed | none |
| Official Preview | pygame fullscreen | GazeFollower PREVIEWING | pygame (blocking) |
| Official Calibration / result | pygame fullscreen | GazeFollower CALIBRATING | pygame (blocking) |
| Keyboard runtime | PySide6 keyboard | GazeFollower SAMPLING | Qt |
| Recalibrate | pygame (Qt hidden) | CLOSING then PREVIEWING/CALIBRATING | pygame |
| Shutdown | none | `stop_sampling` + `release` | Qt then process exit |

GazeKey MUST NOT create a Qt Preview or Calibration UI (Principle XI
**approved 2026-08-24**: official Preview/Calibration/result UI as-is).
Product runtime is **Python 3.11**. Do not start `TrackingManager` /
`EyeDetector` for blink or any other reason.

## Startup sequence (required)

1. Parse GazeKey CLI; do not start tracking.
2. Construct official `GazeFollower()` with `DefaultConfig` (`cali_mode=13`,
   `screen_physical_size=None`). Do not copy `camera_position` into
   GazeKey constants.
3. `preview()` then `calibrate()` using official APIs (optional shared
   pygame `win` as in `example/pygame_example.py`).
4. Leave pygame (`pygame.quit()`).
5. `start_sampling()`.
6. `QApplication` + existing `VirtualKeyboard` with tracking/calibration
   overlay **disabled**.
7. Stage C: debug dot from `GazeSample`. Stage D: reconnect dwell/typing.

## Recalibration sequence (required)

1. Calibrate control (existing keyboard action) requests official flow.
2. `os_inject_enabled=False`; stop consuming samples.
3. Hide Qt keyboard; `stop_sampling()`.
4. Official `preview()` + `calibrate()`.
5. `pygame.quit()`; `start_sampling()`; show keyboard; resume consume.

Must `stop_sampling` before preview/calibrate or official `Camera` raises
`RuntimeError`.

## Shutdown sequence (required)

1. Stop Qt sample timer/subscriber.
2. `stop_sampling()` if SAMPLING.
3. `GazeFollower.release()`.
4. Quit Qt.

## Fail closed

Missing model, camera open failure, or unaccepted calibration: report and
**do not** start `TrackingManager` / PCA4.
