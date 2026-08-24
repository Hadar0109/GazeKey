# Quickstart (after implementation — not now)

**Feature**: `005-gazefollower-backend`  
**Do not run this as a substitute for `/speckit.tasks` or implementation.**

## Environment

- Windows desktop, chin/head support for acceptance sessions
- **Python 3.11** product runtime (discovery: 3.11.9). Rebuild/create the
  GazeKey environment on 3.11 and verify retained GazeKey dependencies
  there. Do **not** prove GazeFollower on the existing Python 3.14 `.venv`
- Pinned package: `gazefollower==1.0.2` at commit
  `553920edcb7998c029828677f50f6d8eb4a16249`
- Model: packaged `base.mnn` (SHA-256
  `2f96b95275fe6d7b79e98df3237ebb96e15ef5522c96968f08167da7e1954a96`)
- License of record: **CC BY-NC-SA 4.0** (attribution + non-commercial /
  share-alike). `version.py` CC BY 4.0 string is upstream inconsistency
- GazeKey deps remain PySide6, pynput; GazeFollower pulls mediapipe, MNN,
  pygame, screeninfo, pandas, opencv, numpy

## Expected product flow

1. `python main.py` (3.11 env)
2. Official GazeFollower Preview (pygame)
3. Official Calibration (13-point default); Space accept or R retry
4. Stage B: existing GazeKey keyboard (shown once after sampling)
5. Stage C: debug gaze dot from official filtered gaze on that same keyboard
6. Stage D: dwell → OS typing → suggestions
7. Recalibrate from the keyboard Calibrate control: same official flow
8. Close window: `stop_sampling` + `release`

## Isolation smoke

`pytest` isolation test: `gazekey.backend` does not import forbidden
legacy gaze modules.

## Acceptance (Stage F)

At least three chin-support sessions on the **integrated** app (real
keyboard, real OS typing), not standalone `pygame_example.py`. Include
natural-blink coverage: blinks cancel/do not complete dwell and do not
cause OS typing. Cleanup (Stage G) only after that record plus a Git
checkpoint.
