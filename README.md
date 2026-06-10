# GazeKey

Eye-tracking virtual keyboard using a standard webcam and MediaPipe face landmarks.

## What it does today (MVP)

On launch the app **calibrates every session** (no loading saved mappers from disk), fits a **PCA4 ridge gaze mapper** on 15 keyboard-aligned targets, then enables **read-only gaze preview** — a dot that tracks where you look. Keys are activated by **mouse click** only; dwell-based gaze typing is dormant (`gazekey/future/`).

Optional dev tooling:

- **`GAZEKEY_DEV_BENCHMARK=1`** — auto-runs a 15-key accuracy benchmark after calibration
- **`GAZEKEY_VERBOSE=1`** — detailed calibration/runtime logs

See **`CURRENT_PIPELINE.md`** for the exact runtime flow and **`TYPING_CANDIDATE.md`** for frozen mapper configuration.

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

### Run

```bash
python main.py
```

1. App opens the virtual keyboard and starts calibration automatically.
2. Fixate each on-screen dot until the session completes.
3. On success, gaze preview is enabled (mapped dot on the keyboard).
4. Click keys with the mouse to type into the text field.
5. Use **Preview** to toggle the gaze dot; use **RECALIBRATE** to run calibration again.

## Project layout

```
Virtual Keyboard/
├── main.py                      # Entry point
├── CURRENT_PIPELINE.md          # Runtime flow (authoritative)
├── TYPING_CANDIDATE.md          # Frozen mapper / gate configuration
├── runs/<session_id>/           # Per-session artifacts (see below)
├── gazekey/
│   ├── ui/                      # VirtualKeyboard + calibration/benchmark UI
│   ├── runtime/                 # Gaze loop, mapper fit, tracking lifecycle
│   ├── calibration/             # Target collection, fixation gate, quality
│   ├── mapping/                 # PCA4 ridge (config.py, ridge.py, row_bias.py)
│   ├── features/                # EyeData → FrameFeatures + PCA smoother
│   ├── tracking/                # Webcam + MediaPipe thread
│   ├── evaluation/              # Benchmark scoring, run summaries, session paths
│   ├── layout/                  # Key geometry inspection
│   ├── typing/                  # Hit testing, text buffer, gaze smoother
│   ├── debug/                   # Diagnostics exports (CSV, mapper snapshot, geometry)
│   └── future/                  # Dormant intent / dwell typing (not on MVP path)
├── archive/                     # Legacy v1 calibration and experiment code
├── tests/                       # Pytest suite
└── specs/                       # Spec Kit feature docs
```

Deeper module map: **`docs/gazekey_code_structure.md`**.

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
| `benchmark_summary.txt` | 15-key benchmark result (dev) |
| `benchmark_diag.json` | Full benchmark diagnostics (dev) |

## Environment variables

| Variable | Effect |
|----------|--------|
| `GAZEKEY_VERBOSE=1` | Verbose logs |
| `GAZEKEY_DEV_BENCHMARK=1` | Auto 15-key benchmark after calibration |
| `GAZEKEY_CALIB_MODE` | Override calibration layout (e.g. `keyboard15`) |
| `GAZEKEY_CALIB_DEBUG=1` | Verbose calibration overlay |
| `GAZEKEY_CALIB_GEOM_DEBUG=1` | Post-fit geometry overlay |
| `GAZEKEY_GAZE_DEBUG=1` | Extra gaze/predict logs |

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

**Calibration fails / preview blocked** — keep head still, move eyes only, tap RECALIBRATE.

**Low detection rate** — improve lighting; face the camera directly.

## License

[Your License Here]
