# GazeKey

Eye-tracking virtual keyboard using a standard webcam and MediaPipe face landmarks.

## What it does today

On launch the app **calibrates every session** (no loading saved mappers from disk), fits a **PCA4 ridge gaze mapper** on 15 keyboard-aligned targets, then keeps a **usable mapped-gaze** path ready for the product UI. Keys are activated by **mouse click** today; dwell-based gaze typing and OS injection are in progress under feature `002-gaze-typing-os` (not enabled yet on the default product path).

**Product** launch does **not** start gaze preview or the accuracy benchmark. Those are **developer tools**.

See **`docs/CURRENT_PIPELINE.md`** for the runtime flow and **`docs/TYPING_CANDIDATE.md`** for frozen mapper configuration.

## Quick start

### Requirements

- Python 3.10+ (tested on 3.14)
- Webcam
- Windows / Linux / macOS

### Install

```bash
git clone <repository-url>
cd "Virtual Keyboard"
pip install -r requirements.txt
```

MediaPipe model: `models/face_landmarker.task` (downloaded on first run if missing).

### Run (product)

```bash
python main.py
```

1. App opens the virtual keyboard and starts calibration automatically.
2. Fixate each on-screen dot until the session completes.
3. On success, a usable mapper is available for the product path.
4. Click keys with the mouse to type into the text field.
5. Use **RECALIBRATE** to run calibration again.

### Developer tools (optional)

```bash
python -m tools.preview          # read-only gaze preview (devtools attached)
set GAZEKEY_DEV_BENCHMARK=1
python -m tools.evaluation       # 15-key accuracy benchmark after calib+preview
```

Details: **`tools/README.md`**.

## Project layout

```
Virtual Keyboard/
├── main.py                      # Product entry point
├── docs/                        # Pipeline, structure, typing-candidate notes
├── runs/<session_id>/           # Per-session artifacts
├── gazekey/                     # Product runtime only
│   ├── ui/                      # VirtualKeyboard + calibration UI
│   ├── runtime/                 # Gaze loop, mapper fit, session id
│   ├── calibration/             # Target collection, fixation gate, quality
│   ├── mapping/                 # PCA4 ridge (config.py, ridge.py, row_bias.py)
│   ├── features/                # EyeData → FrameFeatures + PCA smoother
│   ├── tracking/                # Webcam + MediaPipe thread
│   ├── layout/                  # Key geometry inspection
│   └── typing/                  # Hit testing, text buffer, gaze smoother
├── tools/                       # Developer preview / evaluation / debug
├── archive/                     # Legacy v1 calibration and experiment code
├── tests/                       # Pytest suite
└── specs/                       # Spec Kit feature docs
```

Deeper maps: **`docs/gazekey_code_structure.md`**, **`docs/PROJECT_STRUCTURE.md`**.

## Session artifacts

All runtime-generated files go under **`runs/<session_id>/`** (not the repo root):

| File | Purpose |
|------|---------|
| `calibration_summary.txt` | Console-style pass/fail summary |
| `calibration_v2.json` | Fitted mapper snapshot (inspection only; not loaded on startup) |
| `keyboard_layout.csv` | Key geometry at calibration time |
| `coverage.json` | Calibration anchor vs key coverage |
| `calibration_debug.csv` | Per-target train/LOOCV diagnostics |
| `calibration_ratio_space.csv` | Row-level avg_v stats |
| `benchmark_summary.txt` | 15-key benchmark result (tools) |
| `benchmark_diag.json` | Full benchmark diagnostics (tools) |

## Environment variables

### Product

| Variable | Effect |
|----------|--------|
| `GAZEKEY_VERBOSE=1` | Verbose logs |
| `GAZEKEY_CALIB_MODE` | Override calibration layout (re-evaluate; may become tools-only later) |
| `GAZEKEY_CALIB_DEBUG=1` | Verbose calibration overlay (re-evaluate) |
| `GAZEKEY_GAZE_DEBUG=1` | Extra gaze/predict logs (re-evaluate) |
| `GAZEKEY_CAMERA_PREVIEW_DURING_CALIB=1` | Camera PiP during fixation (re-evaluate) |

### Tools only

| Variable | Effect |
|----------|--------|
| `GAZEKEY_DEV_BENCHMARK=1` | Auto 15-key benchmark via `python -m tools.evaluation` |
| `GAZEKEY_CALIB_GEOM_DEBUG=1` | Post-fit geometry overlay (tools sessions) |

## Tests

```bash
python -m pytest tests/ -q
```

## Technical notes

- **Eye tracking**: MediaPipe Face Landmarker, ~30 FPS background thread
- **Features**: PCA eye-local `uL/vL/uR/vR` + ratio `avg_h/avg_v`
- **Mapper**: `pca4_baseline` ridge regression; optional row-Y bias wrapper
- **Default calibration**: `keyboard15` (15 points on real key centers)

## Troubleshooting

**Camera not opening** — check OS privacy settings; close other apps using the webcam.

**Calibration fails** — keep head still, move eyes only, tap RECALIBRATE.

**Low detection rate** — improve lighting; face the camera directly.

## License

[Your License Here]
